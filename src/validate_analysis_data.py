"""Validate the raw files used for player, shot, PBP, and lineup analysis."""

from pathlib import Path

import pandas as pd

from config import (
    ANALYSIS_GAME_IDS,
    HOLDOUT_GAME_ID,
    KNICKS_TEAM_ID,
    PLAYOFFS_SEASON_TYPE,
    PREGAME_GAME_IDS,
    RAW_GAME_BOX_SCORE_DIR,
    RAW_LINEUP_DIR,
    RAW_PLAYER_LOG_DIR,
    RAW_PLAY_BY_PLAY_DIR,
    RAW_SHOT_DIR,
    REGULAR_SEASON_TYPE,
    SPURS_TEAM_ID,
)


TEAM_JOBS = [
    (SPURS_TEAM_ID, "SAS", REGULAR_SEASON_TYPE),
    (SPURS_TEAM_ID, "SAS", PLAYOFFS_SEASON_TYPE),
    (KNICKS_TEAM_ID, "NYK", REGULAR_SEASON_TYPE),
    (KNICKS_TEAM_ID, "NYK", PLAYOFFS_SEASON_TYPE),
]

LINEUP_SAMPLE_NAMES = [
    "Full Regular Season",
    "Playoffs Before Finals",
    "Finals Games 1-4",
    "Last 10 Before Game 5",
]


def safe_name(value: str) -> str:
    """Convert a label into a filename-safe value."""

    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


def require_file(file_path: Path) -> None:
    """Raise a clear error when a required raw file is missing."""

    if not file_path.exists():
        raise FileNotFoundError(f"Missing analysis raw file: {file_path}")


def validate_required_files() -> None:
    """Confirm that every expected analysis file exists."""

    for _, abbreviation, season_type in TEAM_JOBS:
        for measure in ["base", "advanced"]:
            require_file(
                RAW_PLAYER_LOG_DIR
                / (
                    f"{abbreviation.lower()}_{safe_name(season_type)}_"
                    f"{measure}_player_game_logs.csv"
                )
            )

    for game_id in ANALYSIS_GAME_IDS:
        require_file(
            RAW_GAME_BOX_SCORE_DIR
            / f"{game_id}_traditional_players.csv"
        )
        require_file(
            RAW_GAME_BOX_SCORE_DIR / f"{game_id}_advanced_players.csv"
        )
        require_file(RAW_SHOT_DIR / f"{game_id}_shots.csv")
        require_file(RAW_PLAY_BY_PLAY_DIR / f"{game_id}_pbp.csv")

    for sample_name in LINEUP_SAMPLE_NAMES:
        for abbreviation in ["SAS", "NYK"]:
            for measure in ["base", "advanced"]:
                require_file(
                    RAW_LINEUP_DIR
                    / (
                        f"{abbreviation.lower()}_{safe_name(sample_name)}_"
                        f"{measure}_lineups.csv"
                    )
                )

    print("All required analysis raw files exist.")


def validate_player_logs() -> None:
    """Validate player-log IDs, keys, and minimum columns."""

    base_required = {
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ID",
        "GAME_ID",
        "GAME_DATE",
        "MIN",
        "PTS",
    }
    advanced_required = {
        "PLAYER_ID",
        "TEAM_ID",
        "GAME_ID",
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "USG_PCT",
        "TS_PCT",
    }

    for _, abbreviation, season_type in TEAM_JOBS:
        for measure, required in [
            ("base", base_required),
            ("advanced", advanced_required),
        ]:
            file_path = (
                RAW_PLAYER_LOG_DIR
                / (
                    f"{abbreviation.lower()}_{safe_name(season_type)}_"
                    f"{measure}_player_game_logs.csv"
                )
            )
            dataframe = pd.read_csv(
                file_path,
                dtype={"GAME_ID": "string"},
            )

            if dataframe.empty:
                raise ValueError(f"{file_path.name} contains no rows.")

            missing = required - set(dataframe.columns)
            if missing:
                raise ValueError(
                    f"{file_path.name} is missing columns: {sorted(missing)}"
                )

            invalid_ids = dataframe.loc[
                ~dataframe["GAME_ID"].str.match(r"^\d{10}$", na=False),
                "GAME_ID",
            ].tolist()
            if invalid_ids:
                raise ValueError(
                    f"{file_path.name} contains invalid game IDs: {invalid_ids}"
                )

            duplicates = dataframe.duplicated(
                ["GAME_ID", "PLAYER_ID", "TEAM_ID"]
            )
            if duplicates.any():
                raise ValueError(
                    f"{file_path.name} contains duplicate player-game rows."
                )

            print(f"{file_path.name}: {len(dataframe)} rows")


def validate_game_files() -> None:
    """Validate game box scores, shots, and play-by-play files."""

    for game_id in ANALYSIS_GAME_IDS:
        for measure in ["traditional", "advanced"]:
            file_path = (
                RAW_GAME_BOX_SCORE_DIR
                / f"{game_id}_{measure}_players.csv"
            )
            dataframe = pd.read_csv(
                file_path,
                dtype={"gameId": "string"},
            )

            if dataframe.empty:
                raise ValueError(f"{file_path.name} contains no rows.")

            game_ids = set(dataframe["gameId"].dropna().astype(str))
            if game_ids != {game_id}:
                raise ValueError(
                    f"{file_path.name} contains unexpected IDs: {game_ids}"
                )

        shot_file = RAW_SHOT_DIR / f"{game_id}_shots.csv"
        shots = pd.read_csv(shot_file, dtype={"GAME_ID": "string"})
        if not shots.empty:
            shot_ids = set(shots["GAME_ID"].dropna().astype(str))
            if shot_ids != {game_id}:
                raise ValueError(
                    f"{shot_file.name} contains unexpected IDs: {shot_ids}"
                )

        pbp_file = RAW_PLAY_BY_PLAY_DIR / f"{game_id}_pbp.csv"
        pbp = pd.read_csv(pbp_file, dtype={"gameId": "string"})
        if pbp.empty:
            raise ValueError(f"{pbp_file.name} contains no rows.")

        pbp_ids = set(pbp["gameId"].dropna().astype(str))
        if pbp_ids != {game_id}:
            raise ValueError(
                f"{pbp_file.name} contains unexpected IDs: {pbp_ids}"
            )

        if "actionId" in pbp.columns:
            duplicate_event_rows = pbp["actionId"].duplicated().any()
            duplicate_label = "action IDs"
        else:
            event_columns = [
                "period",
                "actionNumber",
                "clock",
                "teamId",
                "personId",
                "description",
                "actionType",
                "subType",
            ]
            available_event_columns = [
                column for column in event_columns if column in pbp.columns
            ]
            duplicate_event_rows = pbp.duplicated(
                available_event_columns,
            ).any()
            duplicate_label = "event rows"

        if duplicate_event_rows:
            raise ValueError(
                f"{pbp_file.name} contains duplicate {duplicate_label}."
            )

        print(
            f"{game_id}: {len(shots)} shot rows, "
            f"{len(pbp)} play-by-play rows"
        )


def validate_lineup_files() -> None:
    """Validate that lineup files contain group identifiers."""

    for sample_name in LINEUP_SAMPLE_NAMES:
        for abbreviation in ["SAS", "NYK"]:
            for measure in ["base", "advanced"]:
                file_path = (
                    RAW_LINEUP_DIR
                    / (
                        f"{abbreviation.lower()}_{safe_name(sample_name)}_"
                        f"{measure}_lineups.csv"
                    )
                )
                dataframe = pd.read_csv(
                    file_path,
                    dtype={"GROUP_ID": "string"},
                )

                if "GROUP_ID" not in dataframe.columns:
                    raise ValueError(
                        f"{file_path.name} is missing GROUP_ID."
                    )

                print(f"{file_path.name}: {len(dataframe)} rows")


def validate_holdout_rule() -> None:
    """Confirm Game 5 is not in the pregame Finals list."""

    if HOLDOUT_GAME_ID in PREGAME_GAME_IDS:
        raise ValueError("Game 5 appears in PREGAME_GAME_IDS.")

    print("Game 5 remains isolated from the pregame Finals list.")


def validate_analysis_raw_data() -> None:
    """Run every analysis raw-data validation check."""

    validate_required_files()
    validate_player_logs()
    validate_game_files()
    validate_lineup_files()
    validate_holdout_rule()
    print("Analysis raw-data validation completed successfully.")


if __name__ == "__main__":
    validate_analysis_raw_data()
