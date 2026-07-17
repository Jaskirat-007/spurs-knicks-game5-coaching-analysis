# Spursâ€“Knicks Game 5 Coaching Analysis

An out-of-sample NBA coaching analytics project using Python, SQL, SQLite, play-by-play, shot, lineup, and rotation data to build a San Antonio Spurs Game 5 scouting report against the New York Knicks.

## Project Question

Based only on information available through Game 4 of the 2026 NBA Finals, what offensive, defensive, lineup, and rotation adjustments should San Antonio prioritize for Game 5 while trailing the series 3â€“1?

## Why This Project Matters

The goal is not to describe what already happened. It is to simulate the work of a coaching analyst preparing an elimination-game plan:

- isolate repeatable opponent and team tendencies;
- distinguish evidence from basketball interpretation;
- identify counter-evidence;
- translate findings into coach-facing priorities;
- define measurable in-game adjustment triggers;
- reserve Game 5 as an out-of-sample holdout.

## Anti-Hindsight Methodology

All pregame analysis and recommendations were created using data available through Finals Game 4.

Game 5 is excluded from the scouting analysis and reserved for a later holdout evaluation. The pregame report is frozen before the holdout is opened.

## Analytical Framework

The project is organized around two North Stars:

1. **Possession quality** â€” rim pressure, corner threes, free throws, turnovers, and final shot location.
2. **Rotation stability** â€” performance of the starting group, Wembanyama minutes, non-Wembanyama stretches, and recurring five-player combinations.

Supporting analysis covers:

- team identity across regular season, pre-Finals playoffs, last 10 games, and Finals Games 1â€“4;
- Four Factors and game-by-game team performance;
- player workload and efficiency;
- shot geography;
- lineup and rotation performance;
- quarter-level game flow;
- unanswered scoring runs;
- timeout and substitution context.

## Pregame Verdict

San Antonio did not need a completely new identity. It needed to preserve the structure that already produced dominant first quarters, positive starting-lineup minutes, and positive Wembanyama minutes.

The coach gameplan prioritizes:

- matching Wembanyama's minutes to Karl-Anthony Towns;
- limiting extended Foxâ€“Castleâ€“Harper overlap;
- converting paint pressure into more corner threes;
- using Fox as an advantage creator;
- protecting the rim and corners without overreacting to difficult Brunson makes;
- shortening vulnerable non-Wembanyama stretches;
- using predetermined responses to scoring runs and fourth-quarter turnovers.

## Coach-Facing Deliverables

- [Full Game 5 Coach Gameplan](reports/Spurs_Game5_Coach_Gameplan.pdf)
- [One-Page Game 5 Bench Card](reports/Spurs_Game5_Bench_Card.pdf)
- Interactive Streamlit review dashboard
- Analysis-ready CSV outputs
- Reproducible Python and SQL pipeline

## Project Structure

```text
spurs-knicks-game5-coaching-analysis/
â”œâ”€â”€ README.md
â”œâ”€â”€ requirements.txt
â”œâ”€â”€ .gitignore
â”œâ”€â”€ LICENSE
â”œâ”€â”€ src/
â”‚   â”œâ”€â”€ config.py
â”‚   â”œâ”€â”€ init_db.py
â”‚   â”œâ”€â”€ collect_data.py
â”‚   â”œâ”€â”€ validate_data.py
â”‚   â”œâ”€â”€ clean_data.py
â”‚   â”œâ”€â”€ load_data.py
â”‚   â”œâ”€â”€ collect_analysis_data.py
â”‚   â”œâ”€â”€ validate_analysis_data.py
â”‚   â”œâ”€â”€ clean_analysis_data.py
â”‚   â”œâ”€â”€ load_analysis_data.py
â”‚   â”œâ”€â”€ export_analysis_outputs.py
â”‚   â”œâ”€â”€ validate_review_outputs.py
â”‚   â”œâ”€â”€ run_full_pipeline.py
â”‚   â”œâ”€â”€ run_review_build.py
â”‚   â””â”€â”€ review_dashboard.py
â”œâ”€â”€ sql/
â”œâ”€â”€ docs/
â”‚   â”œâ”€â”€ SETUP.md
â”‚   â”œâ”€â”€ analysis_guide.md
â”‚   â”œâ”€â”€ data_dictionary.csv
â”‚   â””â”€â”€ methodology.md
â”œâ”€â”€ data/
â”‚   â””â”€â”€ analysis_outputs/
â”œâ”€â”€ visuals/
â””â”€â”€ reports/
```

## Data Quality Decisions

Two NBA feed behaviors required explicit handling:

- `actionNumber` is not unique for every play-by-play row. Linked events can share an action number, so validation uses `actionId` when available and falls back to a composite event-row check.
- `team_id = 0` represents an event not assigned to a real team. These values are converted to `NULL` before SQLite insertion to preserve referential integrity.

The review outputs were also validated for:

- Game 5 exclusion;
- unique team-game and event records;
- valid quarter totals;
- valid scoring-run score changes;
- complete rotation score context;
- consistent player turnover-percentage scaling;
- lineup net-rating arithmetic;
- shot-frequency totals.

## Run the Project

See [docs/SETUP.md](docs/SETUP.md) for the complete build instructions.

Quick rerun using existing raw data:

```powershell
python src/run_full_pipeline.py --skip-collection
python src/run_review_build.py
streamlit run src/review_dashboard.py
```

## Analysis Outputs

See [docs/analysis_guide.md](docs/analysis_guide.md) for descriptions of the exported CSV files.

## Limitations

- The Finals sample contains only four pregame games.
- Public data cannot identify every defensive coverage or offensive action with film-level certainty.
- Lineup ratings are contextual and can be noisy in small samples.
- Plus-minus and on/off results are used as directional evidence, not individual causal proof.
- Exact scheme recommendations require film validation.

## Project Status

**Pregame phase:** Complete and frozen  
**Game 5 holdout evaluation:** Pending  
**Final long-form case study:** Pending holdout evaluation

## Author

**Jaskirat Singh**  
B.S. Computer Science, Arizona State University  
Basketball analytics, scouting, and decision support

