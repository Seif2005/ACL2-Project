"""Verify the imported graph and compare all five Cypher answers with the CSVs."""

import argparse
import csv
import math
import re
from collections import Counter, defaultdict
from pathlib import Path

from neo4j import GraphDatabase

from Create_kg import ROOT, SCHEMA, find_data_directory, load_config, load_dataset


def check(condition, message):
    if not condition:
        raise AssertionError(message)


def verify_graph(driver, database, data):
    expected_nodes = {
        (label, row["properties"][SCHEMA[label].key]): row["properties"]
        for label, rows in data.items() for row in rows
    }
    expected_edges = {
        ((label, row["properties"][spec.key]), relationship,
         (target_label, row["targets"][source]))
        for label, spec in SCHEMA.items() for row in data[label]
        for relationship, target_label, source, _ in spec.links
    }
    node_ids = {}
    records, _, _ = driver.execute_query(
        "MATCH (n) WHERE NOT n:ConnectionTest "
        "RETURN elementId(n) AS id, labels(n) AS labels, properties(n) AS props",
        database_=database,
    )
    check(len(records) == len(expected_nodes), "Total node count differs from the CSVs")
    for record in records:
        labels = record["labels"]
        check(len(labels) == 1 and labels[0] in SCHEMA, f"Unexpected labels: {labels}")
        label = labels[0]
        properties = record["props"]
        key = (label, properties.get(SCHEMA[label].key))
        check(key in expected_nodes, f"Unexpected node: {key}")
        normalized = {name: value.to_native() if hasattr(value, "to_native") else value
                      for name, value in properties.items()}
        expected = expected_nodes[key]
        check(normalized == expected, f"Incorrect properties on {key}")
        check(all(type(normalized[name]) is type(value) for name, value in expected.items()),
              f"Incorrect property types on {key}")
        node_ids[record["id"]] = key
    check(len(set(node_ids.values())) == len(expected_nodes), "Duplicate node identifiers")
    records, _, _ = driver.execute_query(
        "MATCH (a)-[r]->(b) WHERE NOT a:ConnectionTest AND NOT b:ConnectionTest "
        "RETURN elementId(a) AS source, type(r) AS type, "
        "elementId(b) AS target, properties(r) AS props", database_=database,
    )
    check(len(records) == len(expected_edges), "Total relationship count differs from the CSVs")
    actual_edges = set()
    for record in records:
        check(not record["props"], "Unexpected relationship properties")
        actual_edges.add((node_ids[record["source"]], record["type"], node_ids[record["target"]]))
    check(actual_edges == expected_edges, "Missing, incorrect, or duplicate relationships")
    print(f"Graph verified: {len(expected_nodes):,} nodes, {len(expected_edges):,} relationships;")
    print("all labels, identifiers, properties, types, and relationship endpoints match the CSVs.")


def csv_answers(directory):
    """Compute answers directly from raw CSVs without using the importer's mappings."""
    def read(name):
        with (directory / f"{name}.csv").open(encoding="utf-8-sig", newline="") as stream:
            return list(csv.DictReader(stream))

    drivers = {int(row["driverId"]): row["forename"] + " " + row["surname"]
               for row in read("drivers")}
    constructors = {int(row["constructorId"]): row["name"] for row in read("constructors")}
    races = {int(row["raceId"]): row for row in read("races")}
    statuses = {int(row["statusId"]): row["status"] for row in read("status")}
    results = read("results")
    points = defaultdict(float)
    wins = Counter()
    reliability = defaultdict(lambda: [0, 0])
    shared = defaultdict(dict)
    monaco = defaultdict(list)
    primary_entries = defaultdict(Counter)
    for result in results:
        driver_id = int(result["driverId"])
        constructor_id = int(result["constructorId"])
        race_id = int(result["raceId"])
        race = races[race_id]
        year = int(race["year"])
        status = statuses[int(result["statusId"])]
        if year == 2021:
            points[driver_id] += float(result["points"])
            wins[driver_id] += result["position"] == "1"
        if 2014 <= year <= 2021:
            reliability[constructor_id][0] += 1
            reliability[constructor_id][1] += status == "Finished" or status.startswith("+")
        if driver_id in (1, 822):
            shared[(constructor_id, race_id)][driver_id] = int(result["positionOrder"])
        if (int(race["circuitId"]) == 6 and race["date"] < "2020-01-01"
                and status not in {"Did not qualify", "Did not prequalify", "Withdrew"}):
            monaco[driver_id].append(result)
        if year in (2020, 2021):
            primary_entries[(driver_id, year)][constructor_id] += 1
    answer1 = sorted(
        [{"Driver": drivers[d], "Points": total, "Wins": wins[d]} for d, total in points.items()],
        key=lambda row: (-row["Points"], -row["Wins"], row["Driver"]),
    )
    answer2 = sorted(
        [{"Constructor": constructors[c], "Entries": entries, "Classified": classified,
          "Reliability": classified / entries}
         for c, (entries, classified) in reliability.items() if entries >= 100],
        key=lambda row: (-row["Reliability"], row["Constructor"]),
    )
    head_to_head = defaultdict(lambda: [0, 0, 0])
    for (constructor_id, _), finishes in shared.items():
        if 1 in finishes and 822 in finishes:
            row = head_to_head[constructor_id]
            row[0] += 1
            row[1] += finishes[1] < finishes[822]
            row[2] += finishes[822] < finishes[1]
    answer3 = sorted(
        [{"Constructor": constructors[c], "Shared_Races": counts[0],
          "Hamilton_Ahead": counts[1], "Bottas_Ahead": counts[2]}
         for c, counts in head_to_head.items()], key=lambda row: row["Constructor"],
    )
    answer4 = []
    for driver_id, entries in monaco.items():
        starts = len({entry["raceId"] for entry in entries})
        if starts >= 5:
            answer4.append({
                "Driver": drivers[driver_id], "Starts": starts,
                "Avg_Finish": sum(int(entry["positionOrder"]) for entry in entries) / len(entries),
                "Wins": sum(entry["position"] == "1" for entry in entries),
            })
    answer4.sort(key=lambda row: (row["Avg_Finish"], -row["Wins"], row["Driver"]))
    primary = {key: min(entries, key=lambda c: (-entries[c], c))
               for key, entries in primary_entries.items()}
    changed = sorted(drivers[d] for d in drivers
                     if (d, 2020) in primary and (d, 2021) in primary
                     and primary[(d, 2020)] != primary[(d, 2021)])
    return [answer1, answer2, answer3, answer4,
            [{"Drivers_Changed": len(changed), "Drivers": changed}]]


def verify_queries(driver, database, directory):
    text = (ROOT / "queries.txt").read_text(encoding="utf-8")
    check(re.findall(r"(?m)^//(\d+)\. Query \d+$", text) == ["1", "2", "3", "4", "5"],
          "Query headers must be //1. Query 1 through //5. Query 5")
    queries = re.split(r"(?m)^//\d+\. Query \d+\s*\n", text)[1:]
    for number, (query, expected) in enumerate(zip(queries, csv_answers(directory)), 1):
        records, _, _ = driver.execute_query(query.strip(), database_=database)
        actual = [record.data() for record in records]
        check(len(actual) == len(expected), f"Query {number}: incorrect row count")
        for row_index, (actual_row, expected_row) in enumerate(zip(actual, expected), 1):
            check(actual_row.keys() == expected_row.keys(), f"Query {number}: incorrect columns")
            for column, value in expected_row.items():
                found = actual_row[column]
                matches = (isinstance(found, (int, float)) and math.isclose(found, value, abs_tol=1e-9)
                           if isinstance(value, float) else found == value)
                check(matches, f"Query {number}, row {row_index}, {column}: {found!r} != {value!r}")
        print(f"Query {number}: all {len(actual)} rows and their ordering match the CSV calculation.")
        if number in (3, 5):
            print(actual)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path)
    parser.add_argument("--config", type=Path, default=ROOT / "config.txt")
    args = parser.parse_args()
    directory = find_data_directory(args.data_dir)
    config = load_config(args.config)
    with GraphDatabase.driver(config["URI"],
                              auth=(config["USERNAME"], config["PASSWORD"])) as driver:
        database = config.get("DATABASE") or None
        verify_graph(driver, database, load_dataset(directory))
        verify_queries(driver, database, directory)


if __name__ == "__main__":
    main()
