"""Validate the final pregame outputs used by the review dashboard."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from config import ANALYSIS_OUTPUT_DIR


HOLDOUT_GAME_ID = "0042500405"
EXPECTED_TEAMS = {"SAS", "NYK"}
EXPECTED_SAMPLES = {
    "Full Regular Season",
    "Playoffs Before Finals",
    "Finals Games 1-4",
    "Last 10 Before Game 5",
}

OUTPUT_FILES = {
    "team": "team_comparison_windows.csv",
    "finals": "finals_games_1_4_team_stats.csv",
    "players": "player_comparison_windows.csv",
    "matchup_players": "pregame_matchup_player_games.csv",
    "shots": "pregame_shot_profiles.csv",
    "lineups": "pregame_lineup_analysis.csv",
    "quarters": "finals_quarter_summary.csv",
    "runs": "finals_scoring_runs.csv",
    "rotations": "finals_rotation_events.csv",
}


def read_output(file_name: str) -> pd.DataFrame:
    """Read one output while preserving game IDs as strings."""

    path = ANALYSIS_OUTPUT_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(f"Missing analysis output: {path}")

    dataframe = pd.read_csv(path, dtype={"game_id": "string"})
    if "game_id" in dataframe.columns:
        dataframe["game_id"] = dataframe["game_id"].str.zfill(10)
    return dataframe


def require(condition: bool, message: str) -> None:
    """Raise a clear validation error when a condition fails."""

    if not condition:
        raise ValueError(message)


def validate_no_holdout_leak(dataframes: dict[str, pd.DataFrame]) -> None:
    """Confirm Game 5 never appears in a pregame output."""

    for name, dataframe in dataframes.items():
        if "game_id" not in dataframe.columns:
            continue
        leaked = dataframe["game_id"].eq(HOLDOUT_GAME_ID).any()
        require(not leaked, f"Game 5 leaked into the {name} output.")


def validate_team_windows(dataframe: pd.DataFrame) -> None:
    """Validate team comparison samples and ratings."""

    require(len(dataframe) == 8, "Team comparison should contain 8 rows.")
    require(
        set(dataframe["sample_name"]) == EXPECTED_SAMPLES,
        "Team comparison samples are incomplete or unexpected.",
    )
    require(
        set(dataframe["team_abbreviation"]) == EXPECTED_TEAMS,
        "Team comparison must contain SAS and NYK.",
    )
    difference = (
        pd.to_numeric(dataframe["ortg"], errors="coerce")
        - pd.to_numeric(dataframe["drtg"], errors="coerce")
        - pd.to_numeric(dataframe["net_rating"], errors="coerce")
    ).abs()
    require(
        difference.max() <= 0.2,
        "Team net rating does not equal ORTG minus DRTG.",
    )


def validate_finals_team_stats(dataframe: pd.DataFrame) -> None:
    """Validate the Games 1-4 team table."""

    require(len(dataframe) == 8, "Games 1-4 team output should have 8 rows.")
    require(
        set(dataframe["series_game_number"]) == {1, 2, 3, 4},
        "Games 1-4 team output is missing a Finals game.",
    )
    team_counts = dataframe.groupby("series_game_number")["team"].nunique()
    require(
        team_counts.eq(2).all(),
        "Each Finals game must contain one row for each team.",
    )


def validate_player_windows(dataframe: pd.DataFrame) -> None:
    """Catch percentage scaling and impossible player metrics."""

    turnover_pct = pd.to_numeric(dataframe["turnover_pct"], errors="coerce")
    require(
        turnover_pct.dropna().between(0, 100).all(),
        "Player turnover percentage is outside 0-100.",
    )
    require(
        turnover_pct.dropna().max() < 50,
        "Player turnover percentage still appears incorrectly scaled.",
    )

    for column in ["fg_pct", "three_pct", "true_shooting_pct", "usage_pct"]:
        values = pd.to_numeric(dataframe[column], errors="coerce").dropna()
        require(values.between(0, 100).all(), f"Invalid values in {column}.")


def validate_shot_profiles(dataframe: pd.DataFrame) -> None:
    """Validate harmonized zones and frequency totals."""

    require(
        "Above the Break 3" not in set(dataframe["shot_zone"])
        and "Corner 3" not in set(dataframe["shot_zone"]),
        "Shot zones are not harmonized across the NBA Cup and other games.",
    )
    totals = dataframe.groupby(["sample_name", "team"])[
        "attempt_frequency_pct"
    ].sum()
    require(
        totals.between(99.0, 101.0).all(),
        "Shot-frequency percentages do not sum to approximately 100.",
    )


def validate_lineups(dataframe: pd.DataFrame) -> None:
    """Validate lineup arithmetic."""

    difference = (
        pd.to_numeric(dataframe["ortg"], errors="coerce")
        - pd.to_numeric(dataframe["drtg"], errors="coerce")
        - pd.to_numeric(dataframe["net_rating"], errors="coerce")
    ).abs()
    require(
        difference.dropna().max() <= 0.2,
        "Lineup net rating does not equal ORTG minus DRTG.",
    )


def validate_quarters(
    quarters: pd.DataFrame,
    finals: pd.DataFrame,
) -> None:
    """Confirm quarter scoring reconciles exactly to game totals."""

    require(len(quarters) >= 32, "Quarter summary is missing team-period rows.")
    require(
        set(quarters["team"].dropna()) == EXPECTED_TEAMS,
        "Quarter summary must contain SAS and NYK only.",
    )

    quarter_totals = (
        quarters.groupby(["series_game_number", "team"], as_index=False)[
            "points"
        ]
        .sum()
        .rename(columns={"points": "quarter_points"})
    )
    game_totals = finals[
        ["series_game_number", "team", "points"]
    ].rename(columns={"points": "game_points"})
    comparison = game_totals.merge(
        quarter_totals,
        on=["series_game_number", "team"],
        how="left",
    )
    require(
        comparison["game_points"].eq(comparison["quarter_points"]).all(),
        "Quarter points do not reconcile to final game scores.",
    )

    require(
        pd.to_numeric(quarters["points"], errors="coerce").between(0, 60).all(),
        "Quarter scoring contains an impossible value.",
    )


def validate_scoring_runs(dataframe: pd.DataFrame) -> None:
    """Validate uninterrupted run arithmetic."""

    if dataframe.empty:
        return

    run_points = pd.to_numeric(dataframe["run_points"], errors="coerce")
    scoring_plays = pd.to_numeric(dataframe["scoring_plays"], errors="coerce")
    require((run_points >= 6).all(), "A listed scoring run is below 6-0.")
    require(
        (run_points >= scoring_plays).all()
        and (run_points <= 4 * scoring_plays).all(),
        "Scoring-run points are impossible for the listed play count.",
    )
    require(
        pd.to_numeric(dataframe["opponent_points"], errors="coerce").eq(0).all(),
        "The scoring-run table contains opponent points inside a run.",
    )
    require(
        (
            pd.to_numeric(dataframe["margin_after"], errors="coerce")
            - pd.to_numeric(dataframe["margin_before"], errors="coerce")
        ).eq(pd.to_numeric(dataframe["margin_swing"], errors="coerce")).all(),
        "Scoring-run margin swing is inconsistent.",
    )


def validate_rotation_events(dataframe: pd.DataFrame) -> None:
    """Confirm timeout ownership and score context are populated."""

    require(not dataframe.empty, "Rotation-event output is empty.")
    require(
        dataframe["team"].notna().all(),
        "At least one substitution or timeout is missing its team.",
    )
    for column in ["home_score", "away_score", "team_score", "opponent_score"]:
        require(
            dataframe[column].notna().all(),
            f"Rotation-event {column} contains missing values.",
        )


def validate_review_outputs() -> None:
    """Run every presentation-layer validation."""

    dataframes = {
        key: read_output(file_name)
        for key, file_name in OUTPUT_FILES.items()
    }

    validate_no_holdout_leak(dataframes)
    validate_team_windows(dataframes["team"])
    validate_finals_team_stats(dataframes["finals"])
    validate_player_windows(dataframes["players"])
    validate_shot_profiles(dataframes["shots"])
    validate_lineups(dataframes["lineups"])
    validate_quarters(dataframes["quarters"], dataframes["finals"])
    validate_scoring_runs(dataframes["runs"])
    validate_rotation_events(dataframes["rotations"])

    total_rows = sum(len(dataframe) for dataframe in dataframes.values())
    print(f"Validated analysis files: {len(dataframes)}")
    print(f"Validated analysis rows: {total_rows}")
    print("Game 5 exclusion confirmed.")
    print("Review-output validation completed successfully.")


if __name__ == "__main__":
    validate_review_outputs()
