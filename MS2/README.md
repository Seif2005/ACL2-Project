# Formula 1 knowledge graph — Milestone 2

Start the local ACL2-Project instance in Neo4j Desktop, then run these commands
from this directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe Create_kg.py
.\.venv\Scripts\python.exe verify_kg.py
```

`Create_kg.py` reads `URI`, `USERNAME`, and `PASSWORD` by key from `config.txt`.
An optional `DATABASE` key selects a database; when absent, Neo4j chooses the
user's default database. Keep the credentials private.

The importer first looks for all nine CSVs beside `Create_kg.py`, then in
`../dataset/`. Use `--data-dir PATH` to select another directory. For submission,
place the CSVs beside the script as required by the milestone, and include
`Create_kg.py`, your local `config.txt`, and `queries.txt`. The script only needs
the `neo4j` package listed in `requirements.txt`.

The importer validates the required columns, identifiers, and foreign keys
before writing. It creates uniqueness constraints and imports parent nodes
before their dependents, in transactions of 1,000 rows. Missing CSV values are
omitted; numbers and dates use the required types. Re-running the importer with
the same CSVs updates properties without duplicating nodes or relationships.
It does not clear existing graph data. A failed import can be rerun safely.

`queries.txt` contains the five numbered Cypher queries for Neo4j Query/Browser.
All points calculations use Grand Prix results only. Query 4 counts distinct
races as starts while averaging all eligible Result nodes, including shared
drives. Query 5 resolves constructor ties using the lower constructor ID.

`verify_kg.py` compares every node, property type, and relationship with the nine
CSVs, then independently calculates all five answers directly from the raw CSVs
and compares every returned row and its ordering with the Cypher results. It
expects the selected database to contain exactly the milestone graph.

The local Python runtime is in `.python/`; the virtual environment is `.venv/`.
Use the virtual environment's interpreter directly as above, or activate it with
`.\.venv\Scripts\Activate.ps1`. Neither directory is a submission deliverable.
