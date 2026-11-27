"""Build the Milestone 2 Formula 1 knowledge graph from CSV files."""

import argparse
import csv
import time
from dataclasses import dataclass
from datetime import date
from pathlib import Path

from neo4j import GraphDatabase


ROOT = Path(__file__).resolve().parent
INTEGER_PROPERTIES = {
    "driverId", "constructorId", "circuitId", "statusId", "raceId", "resultId",
    "qualifyId", "year", "round", "number", "grid", "position", "positionOrder",
    "laps", "milliseconds", "fastestLap", "rank", "stop", "lap", "alt",
}
FLOAT_PROPERTIES = {"points", "lat", "lng", "fastestLapSpeed"}
DATE_PROPERTIES = {"dob", "date"}


@dataclass(frozen=True)
class NodeSpec:
    file: str
    key: str
    fields: dict[str, str]
    # Each link is (relationship type, target label, CSV foreign key, target key).
    links: tuple[tuple[str, str, str, str], ...] = ()


def fields(names, **renamed):
    return {**{name: name for name in names.split()}, **renamed}


# Insertion order ensures all parent nodes exist before dependent nodes.
SCHEMA = {
    "Driver": NodeSpec("drivers.csv", "driverId", fields(
        "driverId driverRef number code forename surname dob nationality")),
    "Constructor": NodeSpec("constructors.csv", "constructorId", fields(
        "constructorId constructorRef", constructor_name="name",
        constructor_nationality="nationality")),
    "Circuit": NodeSpec("circuits.csv", "circuitId", fields(
        "circuitId circuitRef lat lng alt", circuit_name="name",
        circuit_loc="location", circuit_country="country")),
    "Season": NodeSpec("seasons.csv", "year", fields("year")),
    "Status": NodeSpec("status.csv", "statusId", fields("statusId status")),
    "Race": NodeSpec("races.csv", "raceId", fields(
        "raceId year round name date time"), (
            ("AT_CIRCUIT", "Circuit", "circuitId", "circuitId"),
            ("IN_SEASON", "Season", "year", "year"),
        )),
    "Result": NodeSpec("results.csv", "resultId", fields(
        "resultId number grid position positionText positionOrder points laps time "
        "milliseconds fastestLap rank fastestLapTime fastestLapSpeed"), (
            ("FOR_RACE", "Race", "raceId", "raceId"),
            ("BY_DRIVER", "Driver", "driverId", "driverId"),
            ("FOR_CONSTRUCTOR", "Constructor", "constructorId", "constructorId"),
            ("HAS_STATUS", "Status", "statusId", "statusId"),
        )),
    "Qualifying": NodeSpec("qualifying.csv", "qualifyId", fields(
        "qualifyId number position q1 q2 q3"), (
            ("FOR_RACE", "Race", "raceId", "raceId"),
            ("BY_DRIVER", "Driver", "driverId", "driverId"),
            ("FOR_CONSTRUCTOR", "Constructor", "constructorId", "constructorId"),
        )),
    "PitStop": NodeSpec("pit_stops.csv", "eventId", fields(
        "stop lap time duration milliseconds"), (
            ("FOR_RACE", "Race", "raceId", "raceId"),
            ("BY_DRIVER", "Driver", "driverId", "driverId"),
        )),
}


def load_config(path):
    config = {}
    for line_number, line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError(f"{path.name}:{line_number}: expected KEY=VALUE")
        config[key.strip().upper()] = value.strip().strip('"').strip("'")
    missing = [key for key in ("URI", "USERNAME", "PASSWORD") if not config.get(key)]
    if missing:
        raise ValueError(f"Missing configuration fields: {', '.join(missing)}")
    return config


def convert_value(name, value):
    if value is None or value.strip() in ("", r"\N", r"\\N"):
        return None
    if name in INTEGER_PROPERTIES:
        return int(value)
    if name in FLOAT_PROPERTIES:
        return float(value)
    if name in DATE_PROPERTIES:
        return date.fromisoformat(value)
    return value


def find_data_directory(requested=None):
    if requested is not None:
        candidates = [requested.resolve()]
    else:
        candidates = [ROOT, ROOT.parent / "dataset"]
    for candidate in candidates:
        if all((candidate / spec.file).is_file() for spec in SCHEMA.values()):
            return candidate
    raise FileNotFoundError("All nine required CSVs must be beside Create_kg.py, "
                            "in ../dataset/, or in the directory passed to --data-dir.")


def load_dataset(directory):
    """Validate every row and foreign key before making any database changes."""
    data = {}
    identifiers = {}
    for label, spec in SCHEMA.items():
        rows = []
        seen = set()
        with (directory / spec.file).open(encoding="utf-8-sig", newline="") as stream:
            reader = csv.DictReader(stream)
            required = set(spec.fields.values()) | {link[2] for link in spec.links}
            missing = required - set(reader.fieldnames or ())
            if missing:
                raise ValueError(f"{spec.file}: missing columns {sorted(missing)}")
            for line_number, raw in enumerate(reader, 2):
                try:
                    properties = {}
                    for name, source in spec.fields.items():
                        value = convert_value(name, raw[source])
                        if value is not None:
                            properties[name] = value
                    if label == "PitStop":
                        properties["eventId"] = ":".join(str(int(raw[name])) for name in
                                                          ("raceId", "driverId", "stop"))
                    identifier = properties[spec.key]
                    if identifier in seen:
                        raise ValueError(f"duplicate {spec.key}: {identifier}")
                    targets = {}
                    for _, target_label, source, _ in spec.links:
                        target_id = int(raw[source])
                        if target_id not in identifiers[target_label]:
                            raise ValueError(f"unknown {target_label}: {target_id}")
                        targets[source] = target_id
                    rows.append({"properties": properties, "targets": targets})
                    seen.add(identifier)
                except (KeyError, TypeError, ValueError) as error:
                    raise ValueError(f"{spec.file}:{line_number}: {error}") from error
        data[label] = rows
        identifiers[label] = seen
    return data


def import_query(label, spec):
    clauses = ["UNWIND $rows AS row"]
    for index, (_, target_label, source, target_key) in enumerate(spec.links):
        clauses.append(f"MATCH (p{index}:{target_label} "
                       f"{{{target_key}: row.targets.{source}}})")
    clauses.extend([
        f"MERGE (n:{label} {{{spec.key}: row.properties.{spec.key}}})",
        "SET n = row.properties",
    ])
    for index, (relationship, _, _, _) in enumerate(spec.links):
        clauses.append(f"MERGE (n)-[:{relationship}]->(p{index})")
    clauses.append("RETURN count(n) AS imported")
    return "\n".join(clauses)


def write_batch(tx, query, rows):
    imported = tx.run(query, rows=rows).single(strict=True)["imported"]
    if imported != len(rows):
        raise RuntimeError("A parent node is missing or duplicated; batch rolled back.")


def create_graph(driver, database, data, batch_size):
    with driver.session(database=database) as session:
        for label, spec in SCHEMA.items():
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_identifier IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{spec.key} IS UNIQUE"
            ).consume()
        for label, spec in SCHEMA.items():
            rows = data[label]
            query = import_query(label, spec)
            for offset in range(0, len(rows), batch_size):
                session.execute_write(write_batch, query, rows[offset:offset + batch_size])
            print(f"{label}: imported {len(rows):,} nodes")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, help="Directory containing the nine CSVs")
    parser.add_argument("--config", type=Path, default=ROOT / "config.txt")
    parser.add_argument("--batch-size", type=int, default=1000)
    args = parser.parse_args()
    if args.batch_size < 1:
        parser.error("--batch-size must be positive")
    config = load_config(args.config)
    directory = find_data_directory(args.data_dir)
    data = load_dataset(directory)
    print(f"Validated CSVs in {directory}")
    with GraphDatabase.driver(config["URI"],
                              auth=(config["USERNAME"], config["PASSWORD"])) as driver:
        driver.verify_connectivity()
        start = time.perf_counter()
        create_graph(driver, config.get("DATABASE") or None, data, args.batch_size)
        elapsed = time.perf_counter() - start
    nodes = sum(len(rows) for rows in data.values())
    relationships = sum(len(data[label]) * len(spec.links) for label, spec in SCHEMA.items())
    print(f"Import complete: {nodes:,} source nodes and {relationships:,} relationships.")
    print(f"Knowledge graph creation time: {elapsed:.2f} seconds.")


if __name__ == "__main__":
    main()
