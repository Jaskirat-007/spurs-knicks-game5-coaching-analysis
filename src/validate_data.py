"""Validate raw NBA data before cleaning or analysis."""

import pandas as pd

from config import (
    FINALS_GAME_IDS,
    HOLDOUT_GAME_ID,
    KNICKS_TEAM_ID,
    NBA_CUP_FINAL_GAME_ID,
    PREGAME_GAME_IDS,
    RAW_DATA_DIR,
    REGULAR_SEASON_H2H_GAME_IDS,
    SPURS_TEAM_ID,
)


REQUIRED_RAW_FILES = [
    "sas_regular_season_game_log.csv",
    "sas_playoffs_game_log.csv",
    "nyk_regular_season_game_log.csv",
    "nyk_playoffs_game_log.csv",
    "sas_regular_season_advanced_game_log.csv",
    "sas_playoffs_advanced_game_log.csv",
    "nyk_regular_season_advanced_game_log.csv",
    "nyk_playoffs_advanced_game_log.csv",
    "nba_cup_final_team_box_score.csv",
    "nba_cup_final_player_box_score.csv",
    "nba_cup_final_advanced_team_box_score.csv",
    "nba_cup_final_advanced_player_box_score.csv",
]


GAME_LOG_REQUIRED_COLUMNS = {
    "Team_ID",
    "Game_ID",
    "GAME_DATE",
    "MATCHUP",
    "WL",
    "PTS",
}


ADVANCED_GAME_LOG_REQUIRED_COLUMNS = {
    "TEAM_ID",
    "TEAM_ABBREVIATION",
    "GAME_ID",
    "GAME_DATE",
    "MATCHUP",
    "WL",
    "OFF_RATING",
    "DEF_RATING",
    "NET_RATING",
    "OREB_PCT",
    "DREB_PCT",
    "REB_PCT",
    "TM_TOV_PCT",
    "EFG_PCT",
    "TS_PCT",
    "PACE",
    "POSS",
}


CUP_TRADITIONAL_TEAM_REQUIRED_COLUMNS = {
    "gameId",
    "teamId",
    "teamTricode",
    "fieldGoalsMade",
    "fieldGoalsAttempted",
    "threePointersMade",
    "threePointersAttempted",
    "freeThrowsMade",
    "freeThrowsAttempted",
    "reboundsOffensive",
    "reboundsDefensive",
    "reboundsTotal",
    "assists",
    "turnovers",
    "points",
}


CUP_ADVANCED_TEAM_REQUIRED_COLUMNS = {
    "gameId",
    "teamId",
    "teamTricode",
    "offensiveRating",
    "defensiveRating",
    "netRating",
    "offensiveReboundPercentage",
    "defensiveReboundPercentage",
    "reboundPercentage",
    "turnoverRatio",
    "effectiveFieldGoalPercentage",
    "trueShootingPercentage",
    "pace",
    "possessions",
}


def validate_raw_files_exist() -> None:
    """Confirm that every required raw-data file exists."""

    missing_files = []

    for file_name in REQUIRED_RAW_FILES:
        file_path = RAW_DATA_DIR / file_name

        if not file_path.exists():
            missing_files.append(file_name)

    if missing_files:
        raise FileNotFoundError(
            f"Missing raw-data files: {missing_files}"
        )

    print("All required raw-data files exist.")


def load_csv(
    file_name: str,
    game_id_column: str | None = None,
) -> pd.DataFrame:
    """Load one raw CSV while preserving game IDs as text."""

    file_path = RAW_DATA_DIR / file_name

    dtype = None

    if game_id_column is not None:
        dtype = {
            game_id_column: "string",
        }

    return pd.read_csv(
        file_path,
        dtype=dtype,
    )


def validate_game_id_format(
    dataframe: pd.DataFrame,
    game_id_column: str,
    file_name: str,
) -> None:
    """Confirm NBA game IDs contain exactly ten digits."""

    invalid_game_ids = dataframe.loc[
        ~dataframe[game_id_column].str.match(
            r"^\d{10}$",
            na=False,
        ),
        game_id_column,
    ].tolist()

    if invalid_game_ids:
        raise ValueError(
            f"{file_name} contains invalid game IDs: "
            f"{invalid_game_ids}"
        )


def validate_no_duplicate_game_ids(
    dataframe: pd.DataFrame,
    game_id_column: str,
    file_name: str,
) -> None:
    """Confirm a team game log has one row per game."""

    duplicate_game_ids = dataframe.loc[
        dataframe[game_id_column].duplicated(),
        game_id_column,
    ].tolist()

    if duplicate_game_ids:
        raise ValueError(
            f"{file_name} contains duplicate game IDs: "
            f"{duplicate_game_ids}"
        )


def validate_game_log_structure(
    dataframe: pd.DataFrame,
    file_name: str,
) -> None:
    """Validate one traditional team game log."""

    if dataframe.empty:
        raise ValueError(
            f"{file_name} contains no rows."
        )

    missing_columns = (
        GAME_LOG_REQUIRED_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{file_name} is missing columns: "
            f"{sorted(missing_columns)}"
        )

    critical_columns = [
        "Team_ID",
        "Game_ID",
        "GAME_DATE",
        "MATCHUP",
        "PTS",
    ]

    missing_values = (
        dataframe[critical_columns]
        .isna()
        .sum()
    )

    columns_with_missing_values = (
        missing_values[missing_values > 0]
        .to_dict()
    )

    if columns_with_missing_values:
        raise ValueError(
            f"{file_name} has missing critical values: "
            f"{columns_with_missing_values}"
        )

    validate_no_duplicate_game_ids(
        dataframe=dataframe,
        game_id_column="Game_ID",
        file_name=file_name,
    )

    validate_game_id_format(
        dataframe=dataframe,
        game_id_column="Game_ID",
        file_name=file_name,
    )

    print(
        f"{file_name}: "
        f"{len(dataframe)} rows, "
        f"{len(dataframe.columns)} columns."
    )


def validate_advanced_game_log_structure(
    dataframe: pd.DataFrame,
    file_name: str,
) -> None:
    """Validate one advanced team game log."""

    if dataframe.empty:
        raise ValueError(
            f"{file_name} contains no rows."
        )

    missing_columns = (
        ADVANCED_GAME_LOG_REQUIRED_COLUMNS
        - set(dataframe.columns)
    )

    if missing_columns:
        raise ValueError(
            f"{file_name} is missing advanced columns: "
            f"{sorted(missing_columns)}"
        )

    critical_columns = [
        "TEAM_ID",
        "TEAM_ABBREVIATION",
        "GAME_ID",
        "GAME_DATE",
        "MATCHUP",
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "PACE",
        "POSS",
    ]

    missing_values = (
        dataframe[critical_columns]
        .isna()
        .sum()
    )

    columns_with_missing_values = (
        missing_values[missing_values > 0]
        .to_dict()
    )

    if columns_with_missing_values:
        raise ValueError(
            f"{file_name} has missing advanced values: "
            f"{columns_with_missing_values}"
        )

    validate_no_duplicate_game_ids(
        dataframe=dataframe,
        game_id_column="GAME_ID",
        file_name=file_name,
    )

    validate_game_id_format(
        dataframe=dataframe,
        game_id_column="GAME_ID",
        file_name=file_name,
    )

    invalid_possessions = dataframe.loc[
        dataframe["POSS"] <= 0,
        "GAME_ID",
    ].tolist()

    if invalid_possessions:
        raise ValueError(
            f"{file_name} contains non-positive possessions "
            f"for games: {invalid_possessions}"
        )

    invalid_pace = dataframe.loc[
        dataframe["PACE"] <= 0,
        "GAME_ID",
    ].tolist()

    if invalid_pace:
        raise ValueError(
            f"{file_name} contains non-positive pace values "
            f"for games: {invalid_pace}"
        )

    print(
        f"{file_name}: "
        f"{len(dataframe)} rows, "
        f"{len(dataframe.columns)} columns."
    )


def validate_regular_season_counts(
    sas_regular_season: pd.DataFrame,
    nyk_regular_season: pd.DataFrame,
) -> None:
    """Confirm both regular-season logs contain 82 games."""

    expected_games = 82

    if len(sas_regular_season) != expected_games:
        raise ValueError(
            "San Antonio regular-season log should contain "
            f"{expected_games} games, but contains "
            f"{len(sas_regular_season)}."
        )

    if len(nyk_regular_season) != expected_games:
        raise ValueError(
            "New York regular-season log should contain "
            f"{expected_games} games, but contains "
            f"{len(nyk_regular_season)}."
        )

    print("Both regular-season logs contain 82 games.")


def validate_traditional_and_advanced_match(
    traditional_log: pd.DataFrame,
    advanced_log: pd.DataFrame,
    description: str,
) -> None:
    """Confirm traditional and advanced logs contain the same games."""

    traditional_ids = set(
        traditional_log["Game_ID"]
        .dropna()
        .astype(str)
    )

    advanced_ids = set(
        advanced_log["GAME_ID"]
        .dropna()
        .astype(str)
    )

    missing_from_advanced = (
        traditional_ids - advanced_ids
    )

    missing_from_traditional = (
        advanced_ids - traditional_ids
    )

    if missing_from_advanced:
        raise ValueError(
            f"{description} games missing from the advanced log: "
            f"{sorted(missing_from_advanced)}"
        )

    if missing_from_traditional:
        raise ValueError(
            f"{description} games missing from the traditional log: "
            f"{sorted(missing_from_traditional)}"
        )

    if len(traditional_log) != len(advanced_log):
        raise ValueError(
            f"{description} traditional and advanced row counts "
            "do not match."
        )

    print(
        f"{description} traditional and advanced game IDs match."
    )


def validate_game_ids_in_both_logs(
    expected_game_ids: list[str],
    first_log: pd.DataFrame,
    second_log: pd.DataFrame,
    description: str,
) -> None:
    """Confirm expected games appear in both team logs."""

    expected_ids = set(expected_game_ids)

    first_ids = set(
        first_log["Game_ID"]
        .dropna()
        .astype(str)
    )

    second_ids = set(
        second_log["Game_ID"]
        .dropna()
        .astype(str)
    )

    missing_from_first = expected_ids - first_ids
    missing_from_second = expected_ids - second_ids

    if missing_from_first:
        raise ValueError(
            f"{description} missing from the Spurs log: "
            f"{sorted(missing_from_first)}"
        )

    if missing_from_second:
        raise ValueError(
            f"{description} missing from the Knicks log: "
            f"{sorted(missing_from_second)}"
        )

    print(
        f"{description} appear in both team logs."
    )


def validate_holdout_configuration() -> None:
    """Confirm Game 5 is separate from pregame game IDs."""

    expected_pregame_ids = {
        FINALS_GAME_IDS[1],
        FINALS_GAME_IDS[2],
        FINALS_GAME_IDS[3],
        FINALS_GAME_IDS[4],
    }

    configured_pregame_ids = set(
        PREGAME_GAME_IDS
    )

    if configured_pregame_ids != expected_pregame_ids:
        raise ValueError(
            "PREGAME_GAME_IDS does not contain exactly "
            "Finals Games 1–4."
        )

    if HOLDOUT_GAME_ID != FINALS_GAME_IDS[5]:
        raise ValueError(
            "HOLDOUT_GAME_ID does not match Finals Game 5."
        )

    if HOLDOUT_GAME_ID in configured_pregame_ids:
        raise ValueError(
            "Game 5 holdout data appears in PREGAME_GAME_IDS."
        )

    print(
        "Finals Games 1–4 are pregame data and "
        "Game 5 is isolated as the holdout."
    )


def validate_cup_game_ids(
    dataframe: pd.DataFrame,
    file_name: str,
) -> None:
    """Confirm a Cup Final file contains only the Cup game ID."""

    if "gameId" not in dataframe.columns:
        raise ValueError(
            f"{file_name} is missing gameId."
        )

    validate_game_id_format(
        dataframe=dataframe,
        game_id_column="gameId",
        file_name=file_name,
    )

    game_ids = set(
        dataframe["gameId"]
        .dropna()
        .astype(str)
    )

    if game_ids != {NBA_CUP_FINAL_GAME_ID}:
        raise ValueError(
            f"{file_name} contains unexpected game IDs: "
            f"{sorted(game_ids)}"
        )


def validate_cup_final_data(
    traditional_team_stats: pd.DataFrame,
    traditional_player_stats: pd.DataFrame,
    advanced_team_stats: pd.DataFrame,
    advanced_player_stats: pd.DataFrame,
) -> None:
    """Validate traditional and advanced NBA Cup Final data."""

    cup_dataframes = {
        "nba_cup_final_team_box_score.csv": (
            traditional_team_stats
        ),
        "nba_cup_final_player_box_score.csv": (
            traditional_player_stats
        ),
        "nba_cup_final_advanced_team_box_score.csv": (
            advanced_team_stats
        ),
        "nba_cup_final_advanced_player_box_score.csv": (
            advanced_player_stats
        ),
    }

    for file_name, dataframe in cup_dataframes.items():
        if dataframe.empty:
            raise ValueError(
                f"{file_name} contains no rows."
            )

        validate_cup_game_ids(
            dataframe=dataframe,
            file_name=file_name,
        )

    missing_traditional_columns = (
        CUP_TRADITIONAL_TEAM_REQUIRED_COLUMNS
        - set(traditional_team_stats.columns)
    )

    if missing_traditional_columns:
        raise ValueError(
            "NBA Cup Final traditional team data is missing "
            f"columns: {sorted(missing_traditional_columns)}"
        )

    missing_advanced_columns = (
        CUP_ADVANCED_TEAM_REQUIRED_COLUMNS
        - set(advanced_team_stats.columns)
    )

    if missing_advanced_columns:
        raise ValueError(
            "NBA Cup Final advanced team data is missing "
            f"columns: {sorted(missing_advanced_columns)}"
        )

    if len(traditional_team_stats) != 2:
        raise ValueError(
            "NBA Cup Final traditional team data should "
            f"contain 2 rows, but contains "
            f"{len(traditional_team_stats)}."
        )

    if len(advanced_team_stats) != 2:
        raise ValueError(
            "NBA Cup Final advanced team data should "
            f"contain 2 rows, but contains "
            f"{len(advanced_team_stats)}."
        )

    expected_team_codes = {
        "SAS",
        "NYK",
    }

    traditional_team_codes = set(
        traditional_team_stats["teamTricode"]
        .dropna()
        .astype(str)
    )

    advanced_team_codes = set(
        advanced_team_stats["teamTricode"]
        .dropna()
        .astype(str)
    )

    if traditional_team_codes != expected_team_codes:
        raise ValueError(
            "Cup Final traditional team data does not contain "
            "exactly SAS and NYK."
        )

    if advanced_team_codes != expected_team_codes:
        raise ValueError(
            "Cup Final advanced team data does not contain "
            "exactly SAS and NYK."
        )

    expected_team_ids = {
        SPURS_TEAM_ID,
        KNICKS_TEAM_ID,
    }

    traditional_team_ids = set(
        traditional_team_stats["teamId"]
        .dropna()
        .astype(int)
    )

    advanced_team_ids = set(
        advanced_team_stats["teamId"]
        .dropna()
        .astype(int)
    )

    if traditional_team_ids != expected_team_ids:
        raise ValueError(
            "Cup Final traditional data contains unexpected "
            "team IDs."
        )

    if advanced_team_ids != expected_team_ids:
        raise ValueError(
            "Cup Final advanced data contains unexpected "
            "team IDs."
        )

    trusted_advanced_columns = [
        "offensiveRating",
        "defensiveRating",
        "netRating",
        "offensiveReboundPercentage",
        "defensiveReboundPercentage",
        "effectiveFieldGoalPercentage",
        "trueShootingPercentage",
        "turnoverRatio",
        "pace",
        "possessions",
    ]

    missing_values = (
        advanced_team_stats[trusted_advanced_columns]
        .isna()
        .sum()
    )

    columns_with_missing_values = (
        missing_values[missing_values > 0]
        .to_dict()
    )

    if columns_with_missing_values:
        raise ValueError(
            "Cup Final advanced team data contains missing "
            f"values: {columns_with_missing_values}"
        )

    if (
        advanced_team_stats["pace"] <= 0
    ).any():
        raise ValueError(
            "Cup Final advanced data contains invalid pace."
        )

    if (
        advanced_team_stats["possessions"] <= 0
    ).any():
        raise ValueError(
            "Cup Final advanced data contains invalid possessions."
        )

    calculated_net_rating = (
        advanced_team_stats["offensiveRating"]
        - advanced_team_stats["defensiveRating"]
    )

    net_rating_difference = (
        calculated_net_rating
        - advanced_team_stats["netRating"]
    ).abs()

    if (
        net_rating_difference > 0.2
    ).any():
        raise ValueError(
            "Cup Final net rating does not match "
            "offensive rating minus defensive rating."
        )

    print(
        "NBA Cup Final traditional and advanced data "
        "validated successfully."
    )

    print(
        f"NBA Cup Final player rows: "
        f"{len(traditional_player_stats)} traditional, "
        f"{len(advanced_player_stats)} advanced."
    )


def validate_raw_data() -> None:
    """Run all raw-data validation checks."""

    validate_raw_files_exist()

    sas_regular_season = load_csv(
        "sas_regular_season_game_log.csv",
        game_id_column="Game_ID",
    )

    sas_playoffs = load_csv(
        "sas_playoffs_game_log.csv",
        game_id_column="Game_ID",
    )

    nyk_regular_season = load_csv(
        "nyk_regular_season_game_log.csv",
        game_id_column="Game_ID",
    )

    nyk_playoffs = load_csv(
        "nyk_playoffs_game_log.csv",
        game_id_column="Game_ID",
    )

    sas_regular_season_advanced = load_csv(
        "sas_regular_season_advanced_game_log.csv",
        game_id_column="GAME_ID",
    )

    sas_playoffs_advanced = load_csv(
        "sas_playoffs_advanced_game_log.csv",
        game_id_column="GAME_ID",
    )

    nyk_regular_season_advanced = load_csv(
        "nyk_regular_season_advanced_game_log.csv",
        game_id_column="GAME_ID",
    )

    nyk_playoffs_advanced = load_csv(
        "nyk_playoffs_advanced_game_log.csv",
        game_id_column="GAME_ID",
    )

    cup_traditional_team = load_csv(
        "nba_cup_final_team_box_score.csv",
        game_id_column="gameId",
    )

    cup_traditional_player = load_csv(
        "nba_cup_final_player_box_score.csv",
        game_id_column="gameId",
    )

    cup_advanced_team = load_csv(
        "nba_cup_final_advanced_team_box_score.csv",
        game_id_column="gameId",
    )

    cup_advanced_player = load_csv(
        "nba_cup_final_advanced_player_box_score.csv",
        game_id_column="gameId",
    )

    traditional_game_logs = {
        "sas_regular_season_game_log.csv": sas_regular_season,
        "sas_playoffs_game_log.csv": sas_playoffs,
        "nyk_regular_season_game_log.csv": nyk_regular_season,
        "nyk_playoffs_game_log.csv": nyk_playoffs,
    }

    advanced_game_logs = {
        "sas_regular_season_advanced_game_log.csv": (
            sas_regular_season_advanced
        ),
        "sas_playoffs_advanced_game_log.csv": (
            sas_playoffs_advanced
        ),
        "nyk_regular_season_advanced_game_log.csv": (
            nyk_regular_season_advanced
        ),
        "nyk_playoffs_advanced_game_log.csv": (
            nyk_playoffs_advanced
        ),
    }

    for file_name, dataframe in traditional_game_logs.items():
        validate_game_log_structure(
            dataframe=dataframe,
            file_name=file_name,
        )

    for file_name, dataframe in advanced_game_logs.items():
        validate_advanced_game_log_structure(
            dataframe=dataframe,
            file_name=file_name,
        )

    validate_regular_season_counts(
        sas_regular_season=sas_regular_season,
        nyk_regular_season=nyk_regular_season,
    )

    validate_traditional_and_advanced_match(
        traditional_log=sas_regular_season,
        advanced_log=sas_regular_season_advanced,
        description="San Antonio regular season",
    )

    validate_traditional_and_advanced_match(
        traditional_log=sas_playoffs,
        advanced_log=sas_playoffs_advanced,
        description="San Antonio playoffs",
    )

    validate_traditional_and_advanced_match(
        traditional_log=nyk_regular_season,
        advanced_log=nyk_regular_season_advanced,
        description="New York regular season",
    )

    validate_traditional_and_advanced_match(
        traditional_log=nyk_playoffs,
        advanced_log=nyk_playoffs_advanced,
        description="New York playoffs",
    )

    validate_game_ids_in_both_logs(
        expected_game_ids=list(
            FINALS_GAME_IDS.values()
        ),
        first_log=sas_playoffs,
        second_log=nyk_playoffs,
        description="All five NBA Finals games",
    )

    validate_game_ids_in_both_logs(
        expected_game_ids=REGULAR_SEASON_H2H_GAME_IDS,
        first_log=sas_regular_season,
        second_log=nyk_regular_season,
        description="The two regular-season head-to-head games",
    )

    validate_holdout_configuration()

    validate_cup_final_data(
        traditional_team_stats=cup_traditional_team,
        traditional_player_stats=cup_traditional_player,
        advanced_team_stats=cup_advanced_team,
        advanced_player_stats=cup_advanced_player,
    )

    print()
    print("Raw-data validation completed successfully.")


if __name__ == "__main__":
    validate_raw_data()