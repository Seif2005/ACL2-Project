"""Delete all nodes and relationships from the configured Neo4j database."""

import argparse
from pathlib import Path

from neo4j import GraphDatabase

from Create_kg import ROOT, load_config


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=ROOT / "config.txt")
    args = parser.parse_args()
    config = load_config(args.config)

    with GraphDatabase.driver(config["URI"],
                              auth=(config["USERNAME"], config["PASSWORD"])) as driver:
        with driver.session(database=config.get("DATABASE") or None) as session:
            total = 0
            while True:
                deleted = session.run(
                    "MATCH (n) WITH n LIMIT 10000 DETACH DELETE n RETURN count(*) AS deleted"
                ).single(strict=True)["deleted"]
                total += deleted
                if deleted == 0:
                    break
    print(f"Cleared {total:,} nodes and their relationships.")


if __name__ == "__main__":
    main()
