"""Clean player, shot, play-by-play, and lineup datasets."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import pandas as pd

from config import (
    ANALYSIS_GAME_IDS,
    GAME_METADATA,
    HOLDOUT_GAME_ID,
    INTERIM_DATA_DIR,
    KNICKS_TEAM_ID,
    PLAYOFFS_SEASON_TYPE,
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

PLAYER_GAME_COLUMNS = [
    "game_id",
    "player_id",
    "team_id",
    "starter",
    "minutes",
    "points",
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
    "ortg",
    "drtg",
    "net_rating",
    "usage_pct",
    "true_shooting_pct",
    "assist_pct",
    "turnover_pct",
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


def read_csv_with_game_id(
    file_path: Path,
    game_id_column: str,
) -> pd.DataFrame:
    """Read a CSV while preserving a leading-zero game ID."""

    if not file_path.exists():
        raise FileNotFoundError(f"Missing raw file: {file_path}")

    return pd.read_csv(
        file_path,
        dtype={game_id_column: "string"},
    )


def optional_series(
    dataframe: pd.DataFrame,
    column_name: str,
    default: object = pd.NA,
) -> pd.Series:
    """Return a column or a same-length default Series."""

    if column_name in dataframe.columns:
        return dataframe[column_name]

    return pd.Series(default, index=dataframe.index)


def parse_minutes_value(value: object) -> float | None:
    """Convert numeric, MM:SS, or ISO PT minutes into decimal minutes."""

    if value is None or pd.isna(value):
        return None

    if isinstance(value, (int, float)):
        return float(value)

    text = str(value).strip()

    if not text:
        return None

    try:
        return float(text)
    except ValueError:
        pass

    clock_match = re.fullmatch(r"(\d+):(\d+(?:\.\d+)?)", text)
    if clock_match:
        minutes = float(clock_match.group(1))
        seconds = float(clock_match.group(2))
        return minutes + seconds / 60.0

    iso_match = re.fullmatch(
        r"PT(?:(\d+(?:\.\d+)?)H)?(?:(\d+(?:\.\d+)?)M)?"
        r"(?:(\d+(?:\.\d+)?)S)?",
        text,
    )
    if iso_match:
        hours = float(iso_match.group(1) or 0)
        minutes = float(iso_match.group(2) or 0)
        seconds = float(iso_match.group(3) or 0)
        return hours * 60 + minutes + seconds / 60.0

    raise ValueError(f"Unsupported minutes value: {value}")


def parse_clock_seconds(value: object) -> int | None:
    """Convert a game clock into seconds remaining in the period."""

    if value is None or pd.isna(value):
        return None

    text = str(value).strip()

    clock_match = re.fullmatch(r"(\d+):(\d+(?:\.\d+)?)", text)
    if clock_match:
        minutes = int(clock_match.group(1))
        seconds = float(clock_match.group(2))
        return int(round(minutes * 60 + seconds))

    iso_match = re.fullmatch(
        r"PT(?:(\d+(?:\.\d+)?)M)?(?:(\d+(?:\.\d+)?)S)?",
        text,
    )
    if iso_match:
        minutes = float(iso_match.group(1) or 0)
        seconds = float(iso_match.group(2) or 0)
        return int(round(minutes * 60 + seconds))

    return None


def starter_lookup_from_box_scores() -> pd.DataFrame:
    """Build starter and position labels for the matchup games."""

    rows: list[pd.DataFrame] = []

    for game_id in ANALYSIS_GAME_IDS:
        file_path = (
            RAW_GAME_BOX_SCORE_DIR
            / f"{game_id}_traditional_players.csv"
        )
        dataframe = read_csv_with_game_id(
            file_path=file_path,
            game_id_column="gameId",
        )

        minutes = dataframe["minutes"].map(parse_minutes_value)
        positions = optional_series(dataframe, "position").fillna("")

        lookup = pd.DataFrame(
            {
                "game_id": dataframe["gameId"],
                "player_id": dataframe["personId"].astype(int),
                "position": positions.astype("string"),
                "starter": (
                    positions.astype("string").str.strip().ne("")
                    & pd.Series(minutes).fillna(0).gt(0)
                ).astype(int),
            }
        )
        rows.append(lookup)

    combined = pd.concat(rows, ignore_index=True)
    return combined.drop_duplicates(["game_id", "player_id"])


def clean_player_log_sample(
    team_id: int,
    abbreviation: str,
    season_type: str,
    starter_lookup: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Merge one base and advanced player-log sample."""

    base_path = (
        RAW_PLAYER_LOG_DIR
        / (
            f"{abbreviation.lower()}_{safe_name(season_type)}_"
            "base_player_game_logs.csv"
        )
    )
    advanced_path = (
        RAW_PLAYER_LOG_DIR
        / (
            f"{abbreviation.lower()}_{safe_name(season_type)}_"
            "advanced_player_game_logs.csv"
        )
    )

    base = read_csv_with_game_id(base_path, "GAME_ID")
    advanced = read_csv_with_game_id(advanced_path, "GAME_ID")

    base_required = {
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ID",
        "GAME_ID",
        "GAME_DATE",
        "MIN",
        "PTS",
        "FGM",
        "FGA",
        "FG3M",
        "FG3A",
        "FTM",
        "FTA",
        "OREB",
        "DREB",
        "REB",
        "AST",
        "TOV",
        "STL",
        "BLK",
        "PF",
        "PLUS_MINUS",
    }
    missing_base = base_required - set(base.columns)
    if missing_base:
        raise ValueError(
            f"Missing base player columns in {base_path.name}: "
            f"{sorted(missing_base)}"
        )

    advanced_required = {
        "PLAYER_ID",
        "TEAM_ID",
        "GAME_ID",
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "USG_PCT",
        "TS_PCT",
        "AST_PCT",
        "TM_TOV_PCT",
    }
    missing_advanced = advanced_required - set(advanced.columns)
    if missing_advanced:
        raise ValueError(
            f"Missing advanced player columns in {advanced_path.name}: "
            f"{sorted(missing_advanced)}"
        )

    advanced_subset = advanced[
        [
            "PLAYER_ID",
            "TEAM_ID",
            "GAME_ID",
            "OFF_RATING",
            "DEF_RATING",
            "NET_RATING",
            "USG_PCT",
            "TS_PCT",
            "AST_PCT",
            "TM_TOV_PCT",
        ]
    ].copy()

    merged = base.merge(
        advanced_subset,
        on=["PLAYER_ID", "TEAM_ID", "GAME_ID"],
        how="left",
        validate="one_to_one",
    )

    merged = merged.merge(
        starter_lookup,
        left_on=["GAME_ID", "PLAYER_ID"],
        right_on=["game_id", "player_id"],
        how="left",
        validate="many_to_one",
    )

    game_stats = pd.DataFrame(
        {
            "game_id": merged["GAME_ID"],
            "player_id": merged["PLAYER_ID"].astype(int),
            "team_id": merged["TEAM_ID"].astype(int),
            "starter": merged["starter"].astype("Int64"),
            "minutes": pd.to_numeric(merged["MIN"], errors="coerce"),
            "points": merged["PTS"],
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
            "plus_minus": merged["PLUS_MINUS"],
            "ortg": merged["OFF_RATING"],
            "drtg": merged["DEF_RATING"],
            "net_rating": merged["NET_RATING"],
            "usage_pct": merged["USG_PCT"],
            "true_shooting_pct": merged["TS_PCT"],
            "assist_pct": merged["AST_PCT"],
            "turnover_pct": merged["TM_TOV_PCT"],
        }
    )[PLAYER_GAME_COLUMNS]

    players = pd.DataFrame(
        {
            "player_id": merged["PLAYER_ID"].astype(int),
            "full_name": merged["PLAYER_NAME"].astype("string"),
            "current_team_id": team_id,
            "position": merged["position"].astype("string"),
            "game_date": pd.to_datetime(merged["GAME_DATE"]),
        }
    )

    return game_stats, players


def clean_cup_player_box_score() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Clean the Cup Final game-level player box scores."""

    game_id = "0062500001"
    traditional = read_csv_with_game_id(
        RAW_GAME_BOX_SCORE_DIR / f"{game_id}_traditional_players.csv",
        "gameId",
    )
    advanced = read_csv_with_game_id(
        RAW_GAME_BOX_SCORE_DIR / f"{game_id}_advanced_players.csv",
        "gameId",
    )

    advanced_subset = advanced[
        [
            "gameId",
            "teamId",
            "personId",
            "offensiveRating",
            "defensiveRating",
            "netRating",
            "usagePercentage",
            "trueShootingPercentage",
            "assistPercentage",
            "turnoverRatio",
        ]
    ].copy()

    merged = traditional.merge(
        advanced_subset,
        on=["gameId", "teamId", "personId"],
        how="left",
        validate="one_to_one",
    )

    minutes = merged["minutes"].map(parse_minutes_value)
    position = optional_series(merged, "position").fillna("")

    game_stats = pd.DataFrame(
        {
            "game_id": merged["gameId"],
            "player_id": merged["personId"].astype(int),
            "team_id": merged["teamId"].astype(int),
            "starter": (
                position.astype("string").str.strip().ne("")
                & pd.Series(minutes).fillna(0).gt(0)
            ).astype(int),
            "minutes": minutes,
            "points": merged["points"],
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
            "ortg": merged["offensiveRating"],
            "drtg": merged["defensiveRating"],
            "net_rating": merged["netRating"],
            "usage_pct": merged["usagePercentage"],
            "true_shooting_pct": merged["trueShootingPercentage"],
            "assist_pct": merged["assistPercentage"],
            "turnover_pct": merged["turnoverRatio"] / 100.0,
        }
    )[PLAYER_GAME_COLUMNS]

    players = pd.DataFrame(
        {
            "player_id": merged["personId"].astype(int),
            "full_name": (
                merged["firstName"].fillna("").astype(str).str.strip()
                + " "
                + merged["familyName"].fillna("").astype(str).str.strip()
            ).str.strip(),
            "current_team_id": merged["teamId"].astype(int),
            "position": position.astype("string"),
            "game_date": pd.Timestamp(GAME_METADATA[game_id]["game_date"]),
        }
    )

    return game_stats, players


def build_player_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build players and player-game statistics."""

    starter_lookup = starter_lookup_from_box_scores()
    game_frames: list[pd.DataFrame] = []
    player_frames: list[pd.DataFrame] = []

    for team_id, abbreviation, season_type in TEAM_JOBS:
        game_stats, players = clean_player_log_sample(
            team_id=team_id,
            abbreviation=abbreviation,
            season_type=season_type,
            starter_lookup=starter_lookup,
        )
        game_frames.append(game_stats)
        player_frames.append(players)

    cup_game_stats, cup_players = clean_cup_player_box_score()
    game_frames.append(cup_game_stats)
    player_frames.append(cup_players)

    player_game_stats = pd.concat(game_frames, ignore_index=True)
    player_game_stats = player_game_stats.drop_duplicates(
        ["game_id", "player_id"],
        keep="last",
    )

    player_history = pd.concat(player_frames, ignore_index=True)
    player_history["position"] = (
        player_history["position"].fillna("").astype("string")
    )
    player_history = player_history.sort_values(
        ["player_id", "game_date"]
    )

    players = (
        player_history.groupby("player_id", as_index=False)
        .agg(
            full_name=("full_name", "last"),
            current_team_id=("current_team_id", "last"),
            position=(
                "position",
                lambda values: next(
                    (
                        value
                        for value in reversed(values.tolist())
                        if str(value).strip()
                    ),
                    None,
                ),
            ),
        )
    )

    if player_game_stats.duplicated(["game_id", "player_id"]).any():
        raise ValueError("Duplicate player-game keys remain after cleaning.")

    return players, player_game_stats


def classify_shot_zone(
    basic: object,
    area: object,
    distance: object,
) -> str:
    """Map NBA shot-zone fields into coaching-friendly categories."""

    basic_text = "" if pd.isna(basic) else str(basic)
    area_text = "" if pd.isna(area) else str(area)
    distance_value = pd.to_numeric(pd.Series([distance]), errors="coerce").iloc[0]

    if basic_text == "Restricted Area":
        return "Rim"
    if basic_text == "In The Paint (Non-RA)":
        return "Short Midrange"
    if basic_text == "Mid-Range":
        return "Long Midrange"
    if "Corner 3" in basic_text or "Corner" in area_text:
        return "Corner 3"
    if basic_text == "Above the Break 3":
        return "Above the Break 3"
    if basic_text == "Backcourt":
        return "Backcourt"
    if pd.notna(distance_value) and distance_value <= 4:
        return "Rim"
    if pd.notna(distance_value) and distance_value < 14:
        return "Short Midrange"
    if pd.notna(distance_value) and distance_value < 23:
        return "Long Midrange"
    if pd.notna(distance_value):
        return "Three-Point"
    return "Other"


def shots_from_pbp(game_id: str) -> pd.DataFrame:
    """Build a fallback shot table from V3 play-by-play."""

    pbp = read_csv_with_game_id(
        RAW_PLAY_BY_PLAY_DIR / f"{game_id}_pbp.csv",
        "gameId",
    )
    shots = pbp.loc[
        pd.to_numeric(pbp["isFieldGoal"], errors="coerce").fillna(0).eq(1)
    ].copy()

    return pd.DataFrame(
        {
            "GAME_ID": shots["gameId"],
            "GAME_EVENT_ID": shots["actionNumber"],
            "PLAYER_ID": shots["personId"],
            "TEAM_ID": shots["teamId"],
            "PERIOD": shots["period"],
            "MINUTES_REMAINING": shots["clock"].map(
                lambda value: (
                    parse_clock_seconds(value) // 60
                    if parse_clock_seconds(value) is not None
                    else None
                )
            ),
            "SECONDS_REMAINING": shots["clock"].map(
                lambda value: (
                    parse_clock_seconds(value) % 60
                    if parse_clock_seconds(value) is not None
                    else None
                )
            ),
            "ACTION_TYPE": shots["subType"],
            "SHOT_TYPE": shots["actionType"],
            "SHOT_ZONE_BASIC": "PBP Fallback",
            "SHOT_ZONE_AREA": shots["location"],
            "SHOT_ZONE_RANGE": pd.NA,
            "SHOT_DISTANCE": shots["shotDistance"],
            "LOC_X": shots["xLegacy"],
            "LOC_Y": shots["yLegacy"],
            "SHOT_MADE_FLAG": shots["shotResult"].astype("string")
            .str.lower()
            .eq("made")
            .astype(int),
        }
    )


def build_shots_dataset() -> pd.DataFrame:
    """Build the standardized shot-attempt dataset."""

    frames: list[pd.DataFrame] = []

    for game_id in ANALYSIS_GAME_IDS:
        file_path = RAW_SHOT_DIR / f"{game_id}_shots.csv"
        raw = read_csv_with_game_id(file_path, "GAME_ID")

        if raw.empty:
            raw = shots_from_pbp(game_id)

        required = {
            "GAME_ID",
            "GAME_EVENT_ID",
            "PLAYER_ID",
            "TEAM_ID",
            "PERIOD",
            "MINUTES_REMAINING",
            "SECONDS_REMAINING",
            "ACTION_TYPE",
            "SHOT_TYPE",
            "SHOT_ZONE_BASIC",
            "SHOT_ZONE_AREA",
            "SHOT_ZONE_RANGE",
            "SHOT_DISTANCE",
            "LOC_X",
            "LOC_Y",
            "SHOT_MADE_FLAG",
        }
        missing = required - set(raw.columns)
        if missing:
            raise ValueError(
                f"Shot data for {game_id} is missing: {sorted(missing)}"
            )

        cleaned = pd.DataFrame(
            {
                "shot_id": (
                    raw["GAME_ID"].astype(str)
                    + ":"
                    + raw["GAME_EVENT_ID"].astype(str)
                    + ":"
                    + raw["PLAYER_ID"].astype(str)
                ),
                "game_id": raw["GAME_ID"],
                "event_number": raw["GAME_EVENT_ID"],
                "team_id": raw["TEAM_ID"].astype(int),
                "player_id": raw["PLAYER_ID"].astype(int),
                "period": raw["PERIOD"].astype(int),
                "game_clock": (
                    raw["MINUTES_REMAINING"].astype("Int64").astype(str)
                    + ":"
                    + raw["SECONDS_REMAINING"]
                    .astype("Int64")
                    .astype(str)
                    .str.zfill(2)
                ),
                "seconds_remaining": (
                    pd.to_numeric(raw["MINUTES_REMAINING"], errors="coerce")
                    * 60
                    + pd.to_numeric(
                        raw["SECONDS_REMAINING"], errors="coerce"
                    )
                ),
                "action_type": raw["ACTION_TYPE"],
                "shot_type": raw["SHOT_TYPE"],
                "shot_zone_basic": raw["SHOT_ZONE_BASIC"],
                "shot_zone_area": raw["SHOT_ZONE_AREA"],
                "shot_zone_range": raw["SHOT_ZONE_RANGE"],
                "shot_zone": [
                    classify_shot_zone(basic, area, distance)
                    for basic, area, distance in zip(
                        raw["SHOT_ZONE_BASIC"],
                        raw["SHOT_ZONE_AREA"],
                        raw["SHOT_DISTANCE"],
                    )
                ],
                "shot_distance": raw["SHOT_DISTANCE"],
                "location_x": raw["LOC_X"],
                "location_y": raw["LOC_Y"],
                "shot_made": raw["SHOT_MADE_FLAG"].astype(int),
                "assisted": pd.Series(pd.NA, index=raw.index, dtype="Int64"),
                "assister_player_id": pd.Series(
                    pd.NA, index=raw.index, dtype="Int64"
                ),
            }
        )
        frames.append(cleaned)

    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates("shot_id")


def build_play_by_play_dataset() -> pd.DataFrame:
    """Build standardized V3 play-by-play data."""

    frames: list[pd.DataFrame] = []

    for game_id in ANALYSIS_GAME_IDS:
        raw = read_csv_with_game_id(
            RAW_PLAY_BY_PLAY_DIR / f"{game_id}_pbp.csv",
            "gameId",
        )

        action_text = raw["actionType"].fillna("").astype(str).str.lower()
        subtype_text = raw["subType"].fillna("").astype(str).str.lower()
        description_text = raw["description"].fillna("").astype(str).str.lower()

        player_ids = pd.to_numeric(raw["personId"], errors="coerce")
        player_ids = player_ids.where(player_ids.gt(0))

        home_score = pd.to_numeric(raw["scoreHome"], errors="coerce")
        away_score = pd.to_numeric(raw["scoreAway"], errors="coerce")
        points_scored = pd.to_numeric(raw["pointsTotal"], errors="coerce")

        cleaned = pd.DataFrame(
            {
                "game_id": raw["gameId"],
                "event_number": raw["actionNumber"].astype(int),
                "period": raw["period"].astype(int),
                "game_clock": raw["clock"],
                "seconds_remaining": raw["clock"].map(parse_clock_seconds),
                "event_type": raw["actionType"],
                "action_type": raw["subType"],
                "event_description": raw["description"],
                "team_id": pd.to_numeric(raw["teamId"], errors="coerce"),
                "player1_id": player_ids.astype("Int64"),
                "player2_id": pd.Series(
                    pd.NA, index=raw.index, dtype="Int64"
                ),
                "player3_id": pd.Series(
                    pd.NA, index=raw.index, dtype="Int64"
                ),
                "home_score": home_score.astype("Int64"),
                "away_score": away_score.astype("Int64"),
                "score_margin": (home_score - away_score).astype("Int64"),
                "points_scored": points_scored.astype("Int64"),
                "is_scoring_play": points_scored.fillna(0).gt(0).astype(int),
                "is_turnover": (
                    action_text.str.contains("turnover")
                    | subtype_text.str.contains("turnover")
                    | description_text.str.contains("turnover")
                ).astype(int),
                "is_foul": (
                    action_text.str.contains("foul")
                    | subtype_text.str.contains("foul")
                ).astype(int),
                "is_substitution": (
                    action_text.str.contains("substitution")
                    | subtype_text.str.contains("substitution")
                    | description_text.str.contains("substitution")
                ).astype(int),
                "is_timeout": (
                    action_text.str.contains("timeout")
                    | subtype_text.str.contains("timeout")
                    | description_text.str.contains("timeout")
                ).astype(int),
            }
        )
        frames.append(cleaned)

    combined = pd.concat(frames, ignore_index=True)
    return combined.drop_duplicates(["game_id", "event_number"])


def extract_lineup_player_ids(group_id: object) -> list[int]:
    """Extract five player IDs from an NBA lineup group ID."""

    if group_id is None or pd.isna(group_id):
        return []

    values = [int(value) for value in re.findall(r"\d+", str(group_id))]
    values = [value for value in values if value > 0]

    if len(values) < 5:
        return []

    return values[-5:]


def get_numeric_column(
    dataframe: pd.DataFrame,
    column_name: str,
) -> pd.Series:
    """Return a numeric column or null values when unavailable."""

    if column_name not in dataframe.columns:
        return pd.Series(pd.NA, index=dataframe.index, dtype="Float64")

    return pd.to_numeric(dataframe[column_name], errors="coerce")


def build_lineup_datasets() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Build lineup aggregate and lineup-player bridge tables."""

    lineup_frames: list[pd.DataFrame] = []
    player_rows: list[dict[str, object]] = []

    for sample_name in LINEUP_SAMPLE_NAMES:
        for team_id, abbreviation in [
            (SPURS_TEAM_ID, "SAS"),
            (KNICKS_TEAM_ID, "NYK"),
        ]:
            base_path = (
                RAW_LINEUP_DIR
                / (
                    f"{abbreviation.lower()}_{safe_name(sample_name)}_"
                    "base_lineups.csv"
                )
            )
            advanced_path = (
                RAW_LINEUP_DIR
                / (
                    f"{abbreviation.lower()}_{safe_name(sample_name)}_"
                    "advanced_lineups.csv"
                )
            )

            if not base_path.exists() or not advanced_path.exists():
                raise FileNotFoundError(
                    f"Missing lineup files for {abbreviation}, {sample_name}."
                )

            base = pd.read_csv(base_path, dtype={"GROUP_ID": "string"})
            advanced = pd.read_csv(
                advanced_path, dtype={"GROUP_ID": "string"}
            )

            if base.empty:
                continue

            advanced_columns = [
                column
                for column in [
                    "GROUP_ID",
                    "OFF_RATING",
                    "DEF_RATING",
                    "NET_RATING",
                    "PACE",
                    "POSS",
                    "EFG_PCT",
                    "TM_TOV_PCT",
                    "OREB_PCT",
                    "DREB_PCT",
                    "REB_PCT",
                ]
                if column in advanced.columns
            ]

            merged = base.merge(
                advanced[advanced_columns],
                on="GROUP_ID",
                how="left",
                validate="one_to_one",
            )

            cleaned_rows: list[dict[str, object]] = []

            for _, row in merged.iterrows():
                player_ids = extract_lineup_player_ids(row["GROUP_ID"])
                if len(player_ids) != 5:
                    continue

                unit_key = "-".join(str(value) for value in sorted(player_ids))
                digest = hashlib.sha1(
                    f"{sample_name}|{team_id}|{unit_key}".encode("utf-8")
                ).hexdigest()[:16]
                lineup_id = f"agg_{digest}"

                cleaned_rows.append(
                    {
                        "lineup_id": lineup_id,
                        "unit_key": unit_key,
                        "sample_name": sample_name,
                        "team_id": team_id,
                        "group_name": row.get("GROUP_NAME"),
                        "games_played": row.get("GP"),
                        "wins": row.get("W"),
                        "losses": row.get("L"),
                        "minutes": row.get("MIN"),
                        "possessions": row.get("POSS"),
                        "points": row.get("PTS"),
                        "plus_minus": row.get("PLUS_MINUS"),
                        "ortg": row.get("OFF_RATING"),
                        "drtg": row.get("DEF_RATING"),
                        "net_rating": row.get("NET_RATING"),
                        "pace": row.get("PACE"),
                        "efg_pct": row.get("EFG_PCT"),
                        "tov_pct": row.get("TM_TOV_PCT"),
                        "oreb_pct": row.get("OREB_PCT"),
                        "dreb_pct": row.get("DREB_PCT"),
                        "reb_pct": row.get("REB_PCT"),
                        "is_pregame": 1,
                        "is_holdout": 0,
                        "source": "nba_api TeamDashLineups",
                    }
                )

                for player_id in player_ids:
                    player_rows.append(
                        {
                            "lineup_id": lineup_id,
                            "player_id": player_id,
                        }
                    )

            if cleaned_rows:
                lineup_frames.append(pd.DataFrame(cleaned_rows))

    if not lineup_frames:
        raise ValueError("No valid five-player lineup rows were created.")

    lineups = pd.concat(lineup_frames, ignore_index=True)
    lineup_players = pd.DataFrame(player_rows).drop_duplicates()

    return lineups, lineup_players


def add_pregame_flags(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Add pregame and holdout flags based on game ID."""

    result = dataframe.copy()
    result["is_holdout"] = result["game_id"].eq(HOLDOUT_GAME_ID).astype(int)
    result["is_pregame"] = result["game_id"].map(
        lambda game_id: GAME_METADATA.get(str(game_id), {}).get(
            "is_pregame", 1
        )
    )
    return result


def save_analysis_interim_data() -> None:
    """Build and save every cleaned analysis dataset."""

    INTERIM_DATA_DIR.mkdir(parents=True, exist_ok=True)

    players, player_game_stats = build_player_datasets()
    shots = build_shots_dataset()
    play_by_play = build_play_by_play_dataset()
    lineups, lineup_players = build_lineup_datasets()

    player_game_stats_with_flags = add_pregame_flags(player_game_stats)
    shots_with_flags = add_pregame_flags(shots)
    pbp_with_flags = add_pregame_flags(play_by_play)

    players.to_csv(INTERIM_DATA_DIR / "players.csv", index=False)
    player_game_stats.to_csv(
        INTERIM_DATA_DIR / "player_game_stats_all.csv", index=False
    )
    player_game_stats_with_flags.loc[
        player_game_stats_with_flags["is_pregame"].eq(1),
        PLAYER_GAME_COLUMNS,
    ].to_csv(
        INTERIM_DATA_DIR / "player_game_stats_pregame.csv", index=False
    )
    player_game_stats_with_flags.loc[
        player_game_stats_with_flags["is_holdout"].eq(1),
        PLAYER_GAME_COLUMNS,
    ].to_csv(
        INTERIM_DATA_DIR / "player_game_stats_holdout.csv", index=False
    )

    shots.to_csv(INTERIM_DATA_DIR / "shots_all.csv", index=False)
    shots_with_flags.loc[
        shots_with_flags["is_pregame"].eq(1), shots.columns
    ].to_csv(INTERIM_DATA_DIR / "shots_pregame.csv", index=False)
    shots_with_flags.loc[
        shots_with_flags["is_holdout"].eq(1), shots.columns
    ].to_csv(INTERIM_DATA_DIR / "shots_holdout.csv", index=False)

    play_by_play.to_csv(
        INTERIM_DATA_DIR / "play_by_play_all.csv", index=False
    )
    pbp_with_flags.loc[
        pbp_with_flags["is_pregame"].eq(1), play_by_play.columns
    ].to_csv(INTERIM_DATA_DIR / "play_by_play_pregame.csv", index=False)
    pbp_with_flags.loc[
        pbp_with_flags["is_holdout"].eq(1), play_by_play.columns
    ].to_csv(INTERIM_DATA_DIR / "play_by_play_holdout.csv", index=False)

    lineups.to_csv(
        INTERIM_DATA_DIR / "lineup_aggregates.csv", index=False
    )
    lineup_players.to_csv(
        INTERIM_DATA_DIR / "lineup_players.csv", index=False
    )

    print(f"Players: {len(players)}")
    print(f"Player-game rows: {len(player_game_stats)}")
    print(f"Shots: {len(shots)}")
    print(f"Play-by-play events: {len(play_by_play)}")
    print(f"Lineup aggregates: {len(lineups)}")
    print(f"Lineup-player rows: {len(lineup_players)}")
    print("Analysis-data cleaning completed successfully.")


if __name__ == "__main__":
    save_analysis_interim_data()
