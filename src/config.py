"""Central configuration for project paths, teams, games, and cutoff rules."""

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATA_DIR = PROJECT_ROOT / "data"
RAW_DATA_DIR = DATA_DIR / "raw"
INTERIM_DATA_DIR = DATA_DIR / "interim"
PROCESSED_DATA_DIR = DATA_DIR / "processed"
ANALYSIS_OUTPUT_DIR = PROCESSED_DATA_DIR / "analysis_outputs"

RAW_PLAYER_LOG_DIR = RAW_DATA_DIR / "player_logs"
RAW_GAME_BOX_SCORE_DIR = RAW_DATA_DIR / "game_box_scores"
RAW_SHOT_DIR = RAW_DATA_DIR / "shots"
RAW_PLAY_BY_PLAY_DIR = RAW_DATA_DIR / "play_by_play"
RAW_LINEUP_DIR = RAW_DATA_DIR / "lineups"

DATABASE_PATH = PROCESSED_DATA_DIR / "nba_finals_game5.db"

TARGET_SEASON = "2025-26"
REGULAR_SEASON_TYPE = "Regular Season"
PLAYOFFS_SEASON_TYPE = "Playoffs"

SPURS_ABBREVIATION = "SAS"
KNICKS_ABBREVIATION = "NYK"
SPURS_TEAM_ID = 1610612759
KNICKS_TEAM_ID = 1610612752

PREGAME_MAX_SERIES_GAME = 4
HOLDOUT_SERIES_GAME = 5

FINALS_GAME_IDS = {
    1: "0042500401",
    2: "0042500402",
    3: "0042500403",
    4: "0042500404",
    5: "0042500405",
}

FINALS_GAME_DATES = {
    1: "2026-06-03",
    2: "2026-06-05",
    3: "2026-06-08",
    4: "2026-06-10",
    5: "2026-06-13",
}

PREGAME_GAME_IDS = [
    FINALS_GAME_IDS[1],
    FINALS_GAME_IDS[2],
    FINALS_GAME_IDS[3],
    FINALS_GAME_IDS[4],
]

HOLDOUT_GAME_ID = FINALS_GAME_IDS[5]
HOLDOUT_GAME_DATE = FINALS_GAME_DATES[5]

REGULAR_SEASON_H2H_GAME_IDS = [
    "0022500467",
    "0022500868",
]

NBA_CUP_FINAL_GAME_ID = "0062500001"
NBA_CUP_FINAL_DATE = "2025-12-16"

PREGAME_MATCHUP_GAME_IDS = [
    NBA_CUP_FINAL_GAME_ID,
    *REGULAR_SEASON_H2H_GAME_IDS,
    *PREGAME_GAME_IDS,
]

ANALYSIS_GAME_IDS = [
    *PREGAME_MATCHUP_GAME_IDS,
    HOLDOUT_GAME_ID,
]

GAME_METADATA = {
    NBA_CUP_FINAL_GAME_ID: {
        "game_date": NBA_CUP_FINAL_DATE,
        "season_type": "NBA Cup Final",
        "endpoint_season_type": REGULAR_SEASON_TYPE,
        "sample_name": "NBA Cup Final",
        "is_pregame": 1,
        "is_holdout": 0,
    },
    REGULAR_SEASON_H2H_GAME_IDS[0]: {
        "game_date": "2025-12-31",
        "season_type": REGULAR_SEASON_TYPE,
        "endpoint_season_type": REGULAR_SEASON_TYPE,
        "sample_name": "Regular Season H2H",
        "is_pregame": 1,
        "is_holdout": 0,
    },
    REGULAR_SEASON_H2H_GAME_IDS[1]: {
        "game_date": "2026-03-01",
        "season_type": REGULAR_SEASON_TYPE,
        "endpoint_season_type": REGULAR_SEASON_TYPE,
        "sample_name": "Regular Season H2H",
        "is_pregame": 1,
        "is_holdout": 0,
    },
    FINALS_GAME_IDS[1]: {
        "game_date": FINALS_GAME_DATES[1],
        "season_type": PLAYOFFS_SEASON_TYPE,
        "endpoint_season_type": PLAYOFFS_SEASON_TYPE,
        "sample_name": "Finals Games 1-4",
        "series_game_number": 1,
        "is_pregame": 1,
        "is_holdout": 0,
    },
    FINALS_GAME_IDS[2]: {
        "game_date": FINALS_GAME_DATES[2],
        "season_type": PLAYOFFS_SEASON_TYPE,
        "endpoint_season_type": PLAYOFFS_SEASON_TYPE,
        "sample_name": "Finals Games 1-4",
        "series_game_number": 2,
        "is_pregame": 1,
        "is_holdout": 0,
    },
    FINALS_GAME_IDS[3]: {
        "game_date": FINALS_GAME_DATES[3],
        "season_type": PLAYOFFS_SEASON_TYPE,
        "endpoint_season_type": PLAYOFFS_SEASON_TYPE,
        "sample_name": "Finals Games 1-4",
        "series_game_number": 3,
        "is_pregame": 1,
        "is_holdout": 0,
    },
    FINALS_GAME_IDS[4]: {
        "game_date": FINALS_GAME_DATES[4],
        "season_type": PLAYOFFS_SEASON_TYPE,
        "endpoint_season_type": PLAYOFFS_SEASON_TYPE,
        "sample_name": "Finals Games 1-4",
        "series_game_number": 4,
        "is_pregame": 1,
        "is_holdout": 0,
    },
    HOLDOUT_GAME_ID: {
        "game_date": HOLDOUT_GAME_DATE,
        "season_type": PLAYOFFS_SEASON_TYPE,
        "endpoint_season_type": PLAYOFFS_SEASON_TYPE,
        "sample_name": "Game 5 Holdout",
        "series_game_number": 5,
        "is_pregame": 0,
        "is_holdout": 1,
    },
}

FINALS_START_DATE = FINALS_GAME_DATES[1]
PRE_FINALS_CUTOFF_DATE = "2026-06-02"
PREGAME_CUTOFF_DATE = "2026-06-12"

API_REQUEST_DELAY_SECONDS = 1.5
API_RETRY_ATTEMPTS = 4
API_TIMEOUT_SECONDS = 60
