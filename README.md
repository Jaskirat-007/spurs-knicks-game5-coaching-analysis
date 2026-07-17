# Spurs–Knicks Game 5 Coaching Analysis

An out-of-sample NBA coaching analytics project using Python, SQL, SQLite, play-by-play, shot, lineup, and rotation data to build a San Antonio Spurs Game 5 scouting report against the New York Knicks.

---

## Project Question

Based only on information available through Game 4 of the 2026 NBA Finals, what offensive, defensive, lineup, and rotation adjustments should San Antonio prioritize for Game 5 while trailing the series 3–1?

---

## Why This Project Matters

The objective is not to explain what happened after the fact. Instead, this project simulates the workflow of an NBA coaching analyst preparing an elimination-game scouting report.

The analysis aims to:

- Identify repeatable opponent and team tendencies.
- Separate evidence from basketball interpretation.
- Highlight counter-evidence rather than cherry-picking results.
- Translate findings into coach-facing recommendations.
- Define measurable in-game adjustment triggers.
- Reserve Game 5 as an out-of-sample holdout evaluation.

---

## Anti-Hindsight Methodology

All scouting reports, recommendations, and visualizations were produced **using only data available through Game 4**.

Game 5 was intentionally withheld during analysis and reserved as an independent evaluation of the recommendations.

---

## Analytical Framework

The project is organized around two coaching "North Stars":

### 1. Possession Quality

- Rim pressure
- Corner three generation
- Free-throw creation
- Turnovers
- Shot location

### 2. Rotation Stability

- Starting lineup performance
- Wembanyama on/off impact
- Non-Wembanyama minutes
- Five-player lineup combinations

Supporting analyses include:

- Team performance across the regular season, playoffs, and Finals
- Four Factors
- Player efficiency
- Shot geography
- Lineup performance
- Rotation patterns
- Quarter-by-quarter game flow
- Scoring runs
- Timeout and substitution context

---

## Pregame Verdict

The analysis concluded that San Antonio **did not require a completely new identity**.

Instead, the Spurs needed to preserve the structure that had already produced:

- Dominant first quarters
- Positive starting-lineup minutes
- Positive Wembanyama minutes

Recommended Game 5 priorities:

- Match Wembanyama's minutes with Karl-Anthony Towns.
- Reduce extended Fox–Castle–Harper combinations.
- Convert paint pressure into more corner threes.
- Use Fox primarily as an advantage creator.
- Protect the rim and corners without overreacting to difficult Brunson shot-making.
- Shorten vulnerable non-Wembanyama stretches.
- Use predefined responses to scoring runs and fourth-quarter turnovers.

---

## Coach-Facing Deliverables

- Full Game 5 Coach Gameplan
- One-Page Game 5 Bench Card
- Streamlit review dashboard
- Analysis-ready CSV exports
- Reproducible Python + SQL pipeline

---

## Repository Structure

```text
spurs-knicks-game5-coaching-analysis/
│
├── README.md
├── requirements.txt
├── .gitignore
├── LICENSE
│
├── src/
│   ├── config.py
│   ├── init_db.py
│   ├── collect_data.py
│   ├── validate_data.py
│   ├── clean_data.py
│   ├── load_data.py
│   ├── collect_analysis_data.py
│   ├── validate_analysis_data.py
│   ├── clean_analysis_data.py
│   ├── load_analysis_data.py
│   ├── export_analysis_outputs.py
│   ├── validate_review_outputs.py
│   ├── run_full_pipeline.py
│   ├── run_review_build.py
│   └── review_dashboard.py
│
├── sql/
├── docs/
├── data/
│   └── analysis_outputs/
├── visuals/
└── reports/
```

---

## Data Quality Decisions

Two NBA data-feed behaviors required explicit handling.

### Play-by-play uniqueness

`actionNumber` is not always unique because linked events can share the same value.

Validation therefore:

- Uses `actionId` whenever available.
- Falls back to a composite event check only if necessary.

### SQLite foreign keys

Certain NBA events contain:

```
team_id = 0
```

These rows represent events not assigned to either team.

Before loading into SQLite:

```
team_id = NULL
```

This preserves referential integrity.

Additional validation confirms:

- Game 5 exclusion
- Unique game records
- Quarter totals
- Scoring-run calculations
- Rotation context
- Turnover percentage scaling
- Lineup net-rating calculations
- Shot-frequency totals

---

## Running the Project

See **docs/SETUP.md** for the complete build process.

Quick rerun using previously collected data:

```bash
python src/run_full_pipeline.py --skip-collection
python src/run_review_build.py
streamlit run src/review_dashboard.py
```

---

## Analysis Outputs

Descriptions for every exported dataset are available in:

```
docs/analysis_guide.md
```

---

## Limitations

- Finals sample contains only four pregame games.
- Public play-by-play data cannot perfectly identify every offensive or defensive action.
- Lineup ratings become noisy with small samples.
- Plus-minus and on/off metrics are directional evidence rather than causal proof.
- Final tactical recommendations should always be validated with film.

---

## Project Status

| Stage | Status |
|-------|--------|
| Pregame Scouting Analysis | Complete |
| Game 5 Holdout Evaluation | Pending |
| Final Case Study | Pending |

---

## Author

**Jaskirat Singh**

B.S. Computer Science  
Arizona State University

Basketball Analytics • Scouting • Coaching Decision Support
