# Repository Guidelines

## Project Structure & Module Organization

- `Main.ipynb` contains the Formula 1 podium-prediction workflow: auditing, cleaning, relational analysis, feature engineering, modeling, experiments, explainability, and inference. Extend the existing numbered sections; some later sections are still placeholders.
- `dataset/` contains 14 source CSV tables, including `results.csv`, `qualifying.csv`, and standings tables. Treat these files as immutable; clean DataFrame copies in memory.
- `Description.md` defines milestone requirements and deliverables. Consult it before changing the analysis scope.

## Build, Test, and Development Commands

Run commands from the repository root so `dataset/` resolves correctly. The notebook records Python 3.12.10; there is no dependency manifest or build step.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install jupyter nbconvert numpy pandas matplotlib seaborn scipy statsmodels scikit-learn torch
jupyter notebook Main.ipynb
```

These commands create an isolated environment, install the current notebook dependencies, and open the notebook for development.

For an execution check that preserves the tracked notebook:

```powershell
jupyter nbconvert --to notebook --execute Main.ipynb --output Main.executed.ipynb --ExecutePreprocessor.timeout=-1
```

Keep the generated verification notebook out of commits.

## Coding Style & Naming Conventions

Use four-space Python indentation, `snake_case` for functions and variables, and uppercase names for constants such as `DATA_DIR` and `FEATURES`. Preserve dataset column names such as `raceId` and `driverId`. Follow existing pandas, NumPy, and plotting conventions. Explain analytical decisions in nearby Markdown cells with supporting statistics or plots. No formatter or linter is configured.

## Testing & Analysis Integrity

There is no standalone test framework or coverage threshold. Restart the kernel and run all cells in order; existing assertions check missing-value handling, primary and foreign keys, join grain, and split integrity. Add assertions when introducing new transformations.

Maintain one modeling row per `(raceId, driverId)`. Use only information available after qualifying and before race start; shift historical features to exclude the current race. Preserve chronological splits and fit preprocessing on training data only. Select thresholds and hyperparameters without consulting test results; set random seeds for reproducible experiments.

## Commit & Pull Request Guidelines

History uses short, section-oriented messages such as `Section 3`; no formal convention is enforced. Prefer descriptive messages such as `Section 3: fix standings leakage`. Keep changes focused. Pull requests should identify affected sections, explain analytical choices, report execution checks and metric changes, and link relevant issues. Include plots or screenshots when visual conclusions change. Review notebook diffs for unrelated output churn before submitting.
