"""Clean and combine raw NBA team game data."""

import pandas as pd
from nba_api.stats.static import teams

from config import (
    FINALS_GAME_IDS,
    HOLDOUT_GAME_DATE,
    HOLDOUT_GAME_ID,
    INTERIM_DATA_DIR,
    KNICKS_TEAM_ID,
    NBA_CUP_FINAL_DATE,
    NBA_CUP_FINAL_GAME_ID,
    PLAYOFFS_SEASON_TYPE,
    RAW_DATA_DIR,
    REGULAR_SEASON_TYPE,
    SPURS_TEAM_ID,
    TARGET_SEASON,
)


COLLECTION_JOBS = [
    {
        "team_id": SPURS_TEAM_ID,
        "team_abbreviation": "SAS",
        "season_type": REGULAR_SEASON_TYPE,
    },
    {
        "team_id": SPURS_TEAM_ID,
        "team_abbreviation": "SAS",
        "season_type": PLAYOFFS_SEASON_TYPE,
    },
    {
        "team_id": KNICKS_TEAM_ID,
        "team_abbreviation": "NYK",
        "season_type": REGULAR_SEASON_TYPE,
    },
    {
        "team_id": KNICKS_TEAM_ID,
        "team_abbreviation": "NYK",
        "season_type": PLAYOFFS_SEASON_TYPE,
    },
]


TEAM_GAME_OUTPUT_COLUMNS = [
    "game_id",
    "game_date",
    "season",
    "season_type",
    "series_game_number",
    "team_id",
    "team_abbreviation",
    "opponent_team_id",
    "opponent_abbreviation",
    "matchup",
    "wl",
    "is_home",
    "is_pregame",
    "is_holdout",
    "minutes",
    "points",
    "possessions",
    "poss_est",
    "ortg",
    "drtg",
    "net_rating",
    "pace",
    "fgm",
    "fga",
    "fg3m",
    "fg3a",
    "ftm",
    "fta",
    "oreb",
    "dreb",
    "rebounds",
    "assists",
    "steals",
    "blocks",
    "turnovers",
    "personal_fouls",
    "plus_minus",
    "efg_pct",
    "tov_pct",
    "oreb_pct",
    "dreb_pct",
    "reb_pct",
    "true_shooting_pct",
    "fta_rate",
    "three_pa_rate",
]


def format_season_type_for_file_name(
    season_type: str,
) -> str:
    """Convert a season type into the format used in filenames."""

    return (
        season_type
        .strip()
        .lower()
        .replace(" ", "_")
    )


def build_raw_file_paths(
    team_abbreviation: str,
    season_type: str,
) -> tuple:
    """Build traditional and advanced raw-file paths."""

    safe_season_type = format_season_type_for_file_name(
        season_type
    )

    traditional_path = (
        RAW_DATA_DIR
        / (
            f"{team_abbreviation.lower()}_"
            f"{safe_season_type}_game_log.csv"
        )
    )

    advanced_path = (
        RAW_DATA_DIR
        / (
            f"{team_abbreviation.lower()}_"
            f"{safe_season_type}_advanced_game_log.csv"
        )
    )

    return traditional_path, advanced_path


def load_raw_game_logs(
    team_abbreviation: str,
    season_type: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load matching traditional and advanced team game logs."""

    traditional_path, advanced_path = build_raw_file_paths(
        team_abbreviation=team_abbreviation,
        season_type=season_type,
    )

    if not traditional_path.exists():
        raise FileNotFoundError(
            f"Traditional game log not found: {traditional_path}"
        )

    if not advanced_path.exists():
        raise FileNotFoundError(
            f"Advanced game log not found: {advanced_path}"
        )

    traditional_log = pd.read_csv(
        traditional_path,
        dtype={
            "Game_ID": "string",
        },
    )

    advanced_log = pd.read_csv(
        advanced_path,
        dtype={
            "GAME_ID": "string",
        },
    )

    return traditional_log, advanced_log


def load_cup_final_team_data() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Load traditional and advanced Cup Final team data."""

    traditional_path = (
        RAW_DATA_DIR
        / "nba_cup_final_team_box_score.csv"
    )

    advanced_path = (
        RAW_DATA_DIR
        / "nba_cup_final_advanced_team_box_score.csv"
    )

    if not traditional_path.exists():
        raise FileNotFoundError(
            f"Cup traditional team data not found: "
            f"{traditional_path}"
        )

    if not advanced_path.exists():
        raise FileNotFoundError(
            f"Cup advanced team data not found: "
            f"{advanced_path}"
        )

    traditional_team_stats = pd.read_csv(
        traditional_path,
        dtype={
            "gameId": "string",
        },
    )

    advanced_team_stats = pd.read_csv(
        advanced_path,
        dtype={
            "gameId": "string",
        },
    )

    return traditional_team_stats, advanced_team_stats


def create_team_id_lookup() -> dict[str, int]:
    """Create an abbreviation-to-team-ID lookup."""

    nba_teams = teams.get_teams()

    return {
        team["abbreviation"]: team["id"]
        for team in nba_teams
    }


def extract_opponent_abbreviation(
    matchup: pd.Series,
) -> pd.Series:
    """Extract the opponent abbreviation from MATCHUP."""

    return (
        matchup
        .astype("string")
        .str.split()
        .str[-1]
        .str.strip()
        .str.upper()
    )


def calculate_rate(
    numerator: pd.Series,
    denominator: pd.Series,
) -> pd.Series:
    """Calculate a rate while avoiding division by zero."""

    valid_denominator = denominator.where(
        denominator.ne(0)
    )

    return numerator.div(valid_denominator)


def parse_team_minutes(
    minutes: pd.Series,
) -> pd.Series:
    """Convert a value such as 240:00 into 240.0 minutes."""

    minute_values = pd.to_numeric(
        minutes
        .astype("string")
        .str.split(":")
        .str[0],
        errors="coerce",
    )

    if minute_values.isna().any():
        invalid_values = minutes.loc[
            minute_values.isna()
        ].tolist()

        raise ValueError(
            f"Unable to parse team minutes: {invalid_values}"
        )

    return minute_values.astype(float)


def clean_team_game_log(
    traditional_log: pd.DataFrame,
    advanced_log: pd.DataFrame,
    team_id: int,
    team_abbreviation: str,
    season_type: str,
    team_id_lookup: dict[str, int],
) -> pd.DataFrame:
    """Merge and standardize one traditional and advanced log."""

    advanced_columns = [
        "GAME_ID",
        "TEAM_ID",
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
    ]

    advanced_subset = advanced_log[
        advanced_columns
    ].copy()

    advanced_subset = advanced_subset.rename(
        columns={
            "TEAM_ID": "ADVANCED_TEAM_ID",
        }
    )

    merged = traditional_log.merge(
        advanced_subset,
        left_on="Game_ID",
        right_on="GAME_ID",
        how="inner",
        validate="one_to_one",
    )

    if len(merged) != len(traditional_log):
        raise ValueError(
            f"{team_abbreviation} {season_type}: "
            "the traditional and advanced merge lost rows."
        )

    mismatched_team_ids = merged.loc[
        merged["Team_ID"] != merged["ADVANCED_TEAM_ID"]
    ]

    if not mismatched_team_ids.empty:
        raise ValueError(
            f"{team_abbreviation} {season_type}: "
            "team IDs do not match between the raw datasets."
        )

    if not merged["Team_ID"].eq(team_id).all():
        raise ValueError(
            f"{team_abbreviation} {season_type}: "
            "the dataset contains an unexpected team ID."
        )

    merged["GAME_DATE"] = pd.to_datetime(
        merged["GAME_DATE"],
        format="%b %d, %Y",
    )

    merged["team_abbreviation"] = team_abbreviation

    merged["opponent_abbreviation"] = (
        extract_opponent_abbreviation(
            merged["MATCHUP"]
        )
    )

    merged["opponent_team_id"] = (
        merged["opponent_abbreviation"]
        .map(team_id_lookup)
    )

    missing_opponent_ids = merged.loc[
        merged["opponent_team_id"].isna(),
        "opponent_abbreviation",
    ].unique()

    if len(missing_opponent_ids) > 0:
        raise ValueError(
            "Could not map opponent IDs for: "
            f"{sorted(missing_opponent_ids)}"
        )

    merged["is_home"] = (
        merged["MATCHUP"]
        .str.contains("vs.", regex=False)
        .astype(int)
    )

    merged["poss_est"] = (
        merged["FGA"]
        + 0.44 * merged["FTA"]
        - merged["OREB"]
        + merged["TOV"]
    )

    merged["fta_rate"] = calculate_rate(
        numerator=merged["FTA"],
        denominator=merged["FGA"],
    )

    merged["three_pa_rate"] = calculate_rate(
        numerator=merged["FG3A"],
        denominator=merged["FGA"],
    )

    finals_game_number_lookup = {
        game_id: game_number
        for game_number, game_id
        in FINALS_GAME_IDS.items()
    }

    merged["series_game_number"] = (
        merged["Game_ID"]
        .map(finals_game_number_lookup)
        .astype("Int64")
    )

    holdout_date = pd.Timestamp(
        HOLDOUT_GAME_DATE
    )

    merged["is_holdout"] = (
        merged["Game_ID"] == HOLDOUT_GAME_ID
    ).astype(int)

    merged["is_pregame"] = (
        merged["GAME_DATE"] < holdout_date
    ).astype(int)

    merged["season"] = TARGET_SEASON
    merged["season_type"] = season_type

    cleaned = pd.DataFrame(
        {
            "game_id": merged["Game_ID"],
            "game_date": merged["GAME_DATE"].dt.strftime(
                "%Y-%m-%d"
            ),
            "season": merged["season"],
            "season_type": merged["season_type"],
            "series_game_number": merged[
                "series_game_number"
            ],
            "team_id": merged["Team_ID"],
            "team_abbreviation": merged[
                "team_abbreviation"
            ],
            "opponent_team_id": merged[
                "opponent_team_id"
            ].astype(int),
            "opponent_abbreviation": merged[
                "opponent_abbreviation"
            ],
            "matchup": merged["MATCHUP"],
            "wl": merged["WL"],
            "is_home": merged["is_home"],
            "is_pregame": merged["is_pregame"],
            "is_holdout": merged["is_holdout"],
            "minutes": merged["MIN"],
            "points": merged["PTS"],
            "possessions": merged["POSS"],
            "poss_est": merged["poss_est"],
            "ortg": merged["OFF_RATING"],
            "drtg": merged["DEF_RATING"],
            "net_rating": merged["NET_RATING"],
            "pace": merged["PACE"],
            "fgm": merged["FGM"],
            "fga": merged["FGA"],
            "fg3m": merged["FG3M"],
            "fg3a": merged["FG3A"],
            "ftm": merged["FTM"],
            "fta": merged["FTA"],
            "oreb": merged["OREB"],
            "dreb": merged["DREB"],
            "rebounds": merged["REB"],
            "assists": merged["AST"],
            "steals": merged["STL"],
            "blocks": merged["BLK"],
            "turnovers": merged["TOV"],
            "personal_fouls": merged["PF"],
            "plus_minus": pd.Series(
                pd.NA,
                index=merged.index,
                dtype="Float64",
            ),
            "efg_pct": merged["EFG_PCT"],
            "tov_pct": merged["TM_TOV_PCT"],
            "oreb_pct": merged["OREB_PCT"],
            "dreb_pct": merged["DREB_PCT"],
            "reb_pct": merged["REB_PCT"],
            "true_shooting_pct": merged["TS_PCT"],
            "fta_rate": merged["fta_rate"],
            "three_pa_rate": merged["three_pa_rate"],
        }
    )

    return cleaned[TEAM_GAME_OUTPUT_COLUMNS]


def clean_cup_final_team_data(
    traditional_team_stats: pd.DataFrame,
    advanced_team_stats: pd.DataFrame,
) -> pd.DataFrame:
    """Standardize the NBA Cup Final team data."""

    advanced_columns = [
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
    ]

    advanced_subset = advanced_team_stats[
        advanced_columns
    ].copy()

    merged = traditional_team_stats.merge(
        advanced_subset,
        on=[
            "gameId",
            "teamId",
            "teamTricode",
        ],
        how="inner",
        validate="one_to_one",
    )

    if len(merged) != 2:
        raise ValueError(
            "The standardized Cup Final should contain "
            f"two team rows, but contains {len(merged)}."
        )

    expected_team_ids = {
        SPURS_TEAM_ID,
        KNICKS_TEAM_ID,
    }

    actual_team_ids = set(
        merged["teamId"].astype(int)
    )

    if actual_team_ids != expected_team_ids:
        raise ValueError(
            "The Cup Final contains unexpected team IDs."
        )

    opponent_team_lookup = {
        SPURS_TEAM_ID: KNICKS_TEAM_ID,
        KNICKS_TEAM_ID: SPURS_TEAM_ID,
    }

    opponent_abbreviation_lookup = {
        SPURS_TEAM_ID: "NYK",
        KNICKS_TEAM_ID: "SAS",
    }

    matchup_lookup = {
        SPURS_TEAM_ID: "SAS @ NYK",
        KNICKS_TEAM_ID: "NYK vs. SAS",
    }

    merged["opponent_team_id"] = (
        merged["teamId"]
        .map(opponent_team_lookup)
    )

    merged["opponent_abbreviation"] = (
        merged["teamId"]
        .map(opponent_abbreviation_lookup)
    )

    merged["matchup"] = (
        merged["teamId"]
        .map(matchup_lookup)
    )

    merged["is_home"] = (
        merged["teamId"] == KNICKS_TEAM_ID
    ).astype(int)

    winner_team_id = merged.loc[
        merged["points"].idxmax(),
        "teamId",
    ]

    merged["wl"] = (
        merged["teamId"]
        .eq(winner_team_id)
        .map({
            True: "W",
            False: "L",
        })
    )

    merged["minutes_clean"] = parse_team_minutes(
        merged["minutes"]
    )

    merged["poss_est"] = (
        merged["fieldGoalsAttempted"]
        + 0.44 * merged["freeThrowsAttempted"]
        - merged["reboundsOffensive"]
        + merged["turnovers"]
    )

    merged["fta_rate"] = calculate_rate(
        numerator=merged["freeThrowsAttempted"],
        denominator=merged["fieldGoalsAttempted"],
    )

    merged["three_pa_rate"] = calculate_rate(
        numerator=merged["threePointersAttempted"],
        denominator=merged["fieldGoalsAttempted"],
    )

    cleaned = pd.DataFrame(
        {
            "game_id": merged["gameId"],
            "game_date": NBA_CUP_FINAL_DATE,
            "season": TARGET_SEASON,
            "season_type": "NBA Cup Final",
            "series_game_number": pd.Series(
                pd.array(
                    [pd.NA] * len(merged),
                    dtype="Int64",
                )
            ),
            "team_id": merged["teamId"].astype(int),
            "team_abbreviation": merged[
                "teamTricode"
            ],
            "opponent_team_id": merged[
                "opponent_team_id"
            ].astype(int),
            "opponent_abbreviation": merged[
                "opponent_abbreviation"
            ],
            "matchup": merged["matchup"],
            "wl": merged["wl"],
            "is_home": merged["is_home"],
            "is_pregame": 1,
            "is_holdout": 0,
            "minutes": merged["minutes_clean"],
            "points": merged["points"],
            "possessions": merged["possessions"],
            "poss_est": merged["poss_est"],
            "ortg": merged["offensiveRating"],
            "drtg": merged["defensiveRating"],
            "net_rating": merged["netRating"],
            "pace": merged["pace"],
            "fgm": merged["fieldGoalsMade"],
            "fga": merged["fieldGoalsAttempted"],
            "fg3m": merged["threePointersMade"],
            "fg3a": merged["threePointersAttempted"],
            "ftm": merged["freeThrowsMade"],
            "fta": merged["freeThrowsAttempted"],
            "oreb": merged["reboundsOffensive"],
            "dreb": merged["reboundsDefensive"],
            "rebounds": merged["reboundsTotal"],
            "assists": merged["assists"],
            "steals": merged["steals"],
            "blocks": merged["blocks"],
            "turnovers": merged["turnovers"],
            "personal_fouls": merged["foulsPersonal"],
            "plus_minus": merged["plusMinusPoints"],
            "efg_pct": merged[
                "effectiveFieldGoalPercentage"
            ],
            "tov_pct": merged["turnoverRatio"] / 100,
            "oreb_pct": merged[
                "offensiveReboundPercentage"
            ],
            "dreb_pct": merged[
                "defensiveReboundPercentage"
            ],
            "reb_pct": merged["reboundPercentage"],
            "true_shooting_pct": merged[
                "trueShootingPercentage"
            ],
            "fta_rate": merged["fta_rate"],
            "three_pa_rate": merged["three_pa_rate"],
        }
    )

    return cleaned[TEAM_GAME_OUTPUT_COLUMNS]


def validate_cleaned_team_game_stats(
    dataframe: pd.DataFrame,
) -> None:
    """Validate the combined cleaned team-game dataset."""

    if dataframe.empty:
        raise ValueError(
            "The cleaned team-game dataset contains no rows."
        )

    expected_rows = 208

    if len(dataframe) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} team-game rows, "
            f"but found {len(dataframe)}."
        )

    duplicate_rows = dataframe.duplicated(
        subset=[
            "game_id",
            "team_id",
        ]
    )

    if duplicate_rows.any():
        duplicate_keys = dataframe.loc[
            duplicate_rows,
            [
                "game_id",
                "team_id",
            ],
        ].to_dict("records")

        raise ValueError(
            "Duplicate game and team combinations found: "
            f"{duplicate_keys}"
        )

    invalid_classification = dataframe.loc[
        (
            dataframe["is_pregame"]
            + dataframe["is_holdout"]
        ) != 1
    ]

    if not invalid_classification.empty:
        raise ValueError(
            "Some rows are not classified exclusively as "
            "pregame or holdout."
        )

    holdout_rows = dataframe.loc[
        dataframe["is_holdout"] == 1
    ]

    if len(holdout_rows) != 2:
        raise ValueError(
            "The holdout dataset should contain exactly "
            "two team rows."
        )

    if set(holdout_rows["game_id"]) != {
        HOLDOUT_GAME_ID
    }:
        raise ValueError(
            "The holdout contains a game other than Game 5."
        )

    if (
        holdout_rows["is_pregame"] != 0
    ).any():
        raise ValueError(
            "Game 5 appears in the pregame dataset."
        )

    cup_rows = dataframe.loc[
        dataframe["game_id"]
        == NBA_CUP_FINAL_GAME_ID
    ]

    if len(cup_rows) != 2:
        raise ValueError(
            "The Cup Final should contain two team rows."
        )

    if set(cup_rows["team_abbreviation"]) != {
        "SAS",
        "NYK",
    }:
        raise ValueError(
            "The Cup Final does not contain SAS and NYK."
        )

    if (
        cup_rows["is_pregame"] != 1
    ).any():
        raise ValueError(
            "The Cup Final was not classified as pregame data."
        )

    pregame_rows = dataframe.loc[
        dataframe["is_pregame"] == 1
    ]

    if len(pregame_rows) != 206:
        raise ValueError(
            "The pregame dataset should contain 206 team rows, "
            f"but contains {len(pregame_rows)}."
        )

    latest_pregame_date = pd.to_datetime(
        pregame_rows["game_date"]
    ).max()

    holdout_date = pd.Timestamp(
        HOLDOUT_GAME_DATE
    )

    if latest_pregame_date >= holdout_date:
        raise ValueError(
            "Pregame data contains a record on or after "
            "the Game 5 holdout date."
        )

    critical_columns = [
        "game_id",
        "game_date",
        "team_id",
        "opponent_team_id",
        "points",
        "ortg",
        "drtg",
        "net_rating",
        "pace",
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
            "The cleaned team-game dataset contains missing "
            f"critical values: {columns_with_missing_values}"
        )


def build_clean_team_game_stats() -> pd.DataFrame:
    """Build the combined cleaned team-game dataset."""

    team_id_lookup = create_team_id_lookup()

    cleaned_logs = []

    for job in COLLECTION_JOBS:
        traditional_log, advanced_log = (
            load_raw_game_logs(
                team_abbreviation=job[
                    "team_abbreviation"
                ],
                season_type=job[
                    "season_type"
                ],
            )
        )

        cleaned_log = clean_team_game_log(
            traditional_log=traditional_log,
            advanced_log=advanced_log,
            team_id=job["team_id"],
            team_abbreviation=job[
                "team_abbreviation"
            ],
            season_type=job["season_type"],
            team_id_lookup=team_id_lookup,
        )

        cleaned_logs.append(cleaned_log)

    cup_traditional, cup_advanced = (
        load_cup_final_team_data()
    )

    cleaned_cup_final = clean_cup_final_team_data(
        traditional_team_stats=cup_traditional,
        advanced_team_stats=cup_advanced,
    )

    cleaned_logs.append(cleaned_cup_final)

    combined = pd.concat(
        cleaned_logs,
        ignore_index=True,
    )

    combined = combined.sort_values(
        by=[
            "game_date",
            "game_id",
            "team_id",
        ]
    ).reset_index(drop=True)

    validate_cleaned_team_game_stats(
        combined
    )

    return combined


def save_clean_team_game_stats(
    dataframe: pd.DataFrame,
) -> None:
    """Save combined, pregame, and holdout datasets."""

    INTERIM_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    all_games_path = (
        INTERIM_DATA_DIR
        / "team_game_stats_all.csv"
    )

    pregame_path = (
        INTERIM_DATA_DIR
        / "team_game_stats_pregame.csv"
    )

    holdout_path = (
        INTERIM_DATA_DIR
        / "team_game_stats_holdout.csv"
    )

    pregame_data = dataframe.loc[
        dataframe["is_pregame"] == 1
    ].copy()

    holdout_data = dataframe.loc[
        dataframe["is_holdout"] == 1
    ].copy()

    dataframe.to_csv(
        all_games_path,
        index=False,
    )

    pregame_data.to_csv(
        pregame_path,
        index=False,
    )

    holdout_data.to_csv(
        holdout_path,
        index=False,
    )

    print(f"All team-game rows: {len(dataframe)}")

    print(
        f"Pregame team-game rows: "
        f"{len(pregame_data)}"
    )

    print(
        f"Holdout team-game rows: "
        f"{len(holdout_data)}"
    )

    print(f"Saved to: {all_games_path}")
    print(f"Saved to: {pregame_path}")
    print(f"Saved to: {holdout_path}")


def run_team_game_cleaning() -> None:
    """Run the complete team game-log cleaning stage."""

    print("Cleaning team game data.")

    cleaned_team_game_stats = (
        build_clean_team_game_stats()
    )

    save_clean_team_game_stats(
        cleaned_team_game_stats
    )

    print(
        "Team game-data cleaning completed successfully."
    )


if __name__ == "__main__":
    run_team_game_cleaning()