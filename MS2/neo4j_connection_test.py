"""Create and query a small example in the configured Neo4j database."""

from pathlib import Path

from neo4j import GraphDatabase


def load_config():
    config = {}
    for line in Path(__file__).with_name("config.txt").read_text(encoding="utf-8-sig").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator:
            raise ValueError("Each configuration line must use KEY=VALUE.")
        config[key.strip().upper()] = value.strip().strip('"').strip("'")
    missing = {"URI", "USERNAME", "PASSWORD"} - config.keys()
    if missing:
        raise ValueError(f"Missing configuration fields: {', '.join(sorted(missing))}")
    return config


def main():
    config = load_config()
    with GraphDatabase.driver(
        config["URI"], auth=(config["USERNAME"], config["PASSWORD"])
    ) as driver:
        driver.verify_connectivity()
        records, summary, _ = driver.execute_query(
            "MERGE (n:ConnectionTest {name: $name}) RETURN n.name AS name",
            name="ACL2 Neo4j connection works",
        )
        print(f"Connected to database: {summary.database}")
        print(f"Example query returned: {records[0]['name']}")


if __name__ == "__main__":
    main()
