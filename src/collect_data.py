"""Collect and preserve raw NBA data for the Finals scouting project."""

from pathlib import Path
from time import sleep

import pandas as pd
from nba_api.stats.endpoints import (
    boxscoreadvancedv3,
    boxscoretraditionalv3,
    teamgamelog,
    teamgamelogs,
)

from config import (
    KNICKS_TEAM_ID,
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


def fetch_team_game_log(
    team_id: int,
    season_type: str,
) -> pd.DataFrame:
    """Retrieve one team's traditional game log."""

    response = teamgamelog.TeamGameLog(
        team_id=team_id,
        season=TARGET_SEASON,
        season_type_all_star=season_type,
    )

    game_log = response.get_data_frames()[0]

    if game_log.empty:
        raise ValueError(
            f"No traditional games returned for team {team_id}, "
            f"season {TARGET_SEASON}, type {season_type}."
        )

    required_columns = {
        "Team_ID",
        "Game_ID",
        "GAME_DATE",
        "MATCHUP",
        "WL",
        "PTS",
    }

    missing_columns = required_columns - set(game_log.columns)

    if missing_columns:
        raise ValueError(
            "Traditional game log is missing columns: "
            f"{sorted(missing_columns)}"
        )

    return game_log


def fetch_advanced_team_game_log(
    team_id: int,
    season_type: str,
) -> pd.DataFrame:
    """Retrieve advanced game-level statistics for one team."""

    response = teamgamelogs.TeamGameLogs(
        team_id_nullable=team_id,
        season_nullable=TARGET_SEASON,
        season_type_nullable=season_type,
        measure_type_player_game_logs_nullable="Advanced",
    )

    advanced_game_log = response.get_data_frames()[0]

    if advanced_game_log.empty:
        raise ValueError(
            f"No advanced games returned for team {team_id}, "
            f"season {TARGET_SEASON}, type {season_type}."
        )

    required_columns = {
        "TEAM_ID",
        "GAME_ID",
        "GAME_DATE",
        "MATCHUP",
        "OFF_RATING",
        "DEF_RATING",
        "NET_RATING",
        "OREB_PCT",
        "TM_TOV_PCT",
        "EFG_PCT",
        "PACE",
        "POSS",
    }

    missing_columns = (
        required_columns
        - set(advanced_game_log.columns)
    )

    if missing_columns:
        raise ValueError(
            "Advanced game log is missing columns: "
            f"{sorted(missing_columns)}"
        )

    return advanced_game_log


def fetch_nba_cup_final_traditional_box_score() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Retrieve traditional Cup Final team and player box scores."""

    response = boxscoretraditionalv3.BoxScoreTraditionalV3(
        game_id=NBA_CUP_FINAL_GAME_ID,
    )

    team_stats = response.team_stats.get_data_frame()
    player_stats = response.player_stats.get_data_frame()

    if team_stats.empty:
        raise ValueError(
            "The NBA Cup Final traditional team data returned no rows."
        )

    if player_stats.empty:
        raise ValueError(
            "The NBA Cup Final traditional player data returned no rows."
        )

    return team_stats, player_stats


def fetch_nba_cup_final_advanced_box_score() -> tuple[
    pd.DataFrame,
    pd.DataFrame,
]:
    """Retrieve advanced Cup Final team and player box scores."""

    response = boxscoreadvancedv3.BoxScoreAdvancedV3(
        game_id=NBA_CUP_FINAL_GAME_ID,
    )

    team_stats = response.team_stats.get_data_frame()
    player_stats = response.player_stats.get_data_frame()

    if team_stats.empty:
        raise ValueError(
            "The NBA Cup Final advanced team data returned no rows."
        )

    if player_stats.empty:
        raise ValueError(
            "The NBA Cup Final advanced player data returned no rows."
        )

    required_team_columns = {
        "gameId",
        "teamId",
        "teamTricode",
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
    }

    missing_columns = (
        required_team_columns
        - set(team_stats.columns)
    )

    if missing_columns:
        raise ValueError(
            "NBA Cup Final advanced team data is missing columns: "
            f"{sorted(missing_columns)}"
        )

    return team_stats, player_stats


def save_raw_dataframe(
    dataframe: pd.DataFrame,
    file_name: str,
) -> Path:
    """Save an API response in the raw-data folder."""

    RAW_DATA_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_path = RAW_DATA_DIR / file_name

    dataframe.to_csv(
        file_path,
        index=False,
    )

    return file_path


def format_season_type_for_file_name(
    season_type: str,
) -> str:
    """Convert a season type into a filename-safe value."""

    return (
        season_type
        .strip()
        .lower()
        .replace(" ", "_")
    )


def build_game_log_file_name(
    team_abbreviation: str,
    season_type: str,
) -> str:
    """Create a filename for a traditional team game log."""

    safe_season_type = format_season_type_for_file_name(
        season_type
    )

    return (
        f"{team_abbreviation.lower()}_"
        f"{safe_season_type}_game_log.csv"
    )


def build_advanced_game_log_file_name(
    team_abbreviation: str,
    season_type: str,
) -> str:
    """Create a filename for an advanced team game log."""

    safe_season_type = format_season_type_for_file_name(
        season_type
    )

    return (
        f"{team_abbreviation.lower()}_"
        f"{safe_season_type}_advanced_game_log.csv"
    )


def collect_all_team_game_logs() -> None:
    """Collect traditional game logs for both teams."""

    total_jobs = len(COLLECTION_JOBS)

    for job_number, job in enumerate(
        COLLECTION_JOBS,
        start=1,
    ):
        team_abbreviation = job["team_abbreviation"]
        season_type = job["season_type"]

        print(
            f"Collecting {team_abbreviation} "
            f"{season_type} game log..."
        )

        game_log = fetch_team_game_log(
            team_id=job["team_id"],
            season_type=season_type,
        )

        file_name = build_game_log_file_name(
            team_abbreviation=team_abbreviation,
            season_type=season_type,
        )

        saved_path = save_raw_dataframe(
            dataframe=game_log,
            file_name=file_name,
        )

        print(f"Rows retrieved: {len(game_log)}")
        print(f"Saved to: {saved_path}")
        print()

        if job_number < total_jobs:
            sleep(1)


def collect_and_save_advanced_game_log(
    team_id: int,
    team_abbreviation: str,
    season_type: str,
) -> Path:
    """Collect and save one advanced team game log."""

    print(
        f"Collecting {team_abbreviation} "
        f"{season_type} advanced game log..."
    )

    advanced_game_log = fetch_advanced_team_game_log(
        team_id=team_id,
        season_type=season_type,
    )

    file_name = build_advanced_game_log_file_name(
        team_abbreviation=team_abbreviation,
        season_type=season_type,
    )

    saved_path = save_raw_dataframe(
        dataframe=advanced_game_log,
        file_name=file_name,
    )

    print(f"Rows retrieved: {len(advanced_game_log)}")
    print(f"Saved to: {saved_path}")
    print()

    return saved_path


def collect_all_advanced_team_game_logs() -> None:
    """Collect advanced game logs for both teams."""

    total_jobs = len(COLLECTION_JOBS)

    for job_number, job in enumerate(
        COLLECTION_JOBS,
        start=1,
    ):
        collect_and_save_advanced_game_log(
            team_id=job["team_id"],
            team_abbreviation=job["team_abbreviation"],
            season_type=job["season_type"],
        )

        if job_number < total_jobs:
            sleep(1)


def collect_nba_cup_final() -> None:
    """Collect traditional and advanced NBA Cup Final data."""

    print("Collecting NBA Cup Final traditional box score...")

    traditional_team_stats, traditional_player_stats = (
        fetch_nba_cup_final_traditional_box_score()
    )

    traditional_team_path = save_raw_dataframe(
        dataframe=traditional_team_stats,
        file_name="nba_cup_final_team_box_score.csv",
    )

    traditional_player_path = save_raw_dataframe(
        dataframe=traditional_player_stats,
        file_name="nba_cup_final_player_box_score.csv",
    )

    print(
        f"Traditional team rows retrieved: "
        f"{len(traditional_team_stats)}"
    )

    print(
        f"Traditional player rows retrieved: "
        f"{len(traditional_player_stats)}"
    )

    print(f"Saved to: {traditional_team_path}")
    print(f"Saved to: {traditional_player_path}")
    print()

    sleep(1)

    print("Collecting NBA Cup Final advanced box score...")

    advanced_team_stats, advanced_player_stats = (
        fetch_nba_cup_final_advanced_box_score()
    )

    advanced_team_path = save_raw_dataframe(
        dataframe=advanced_team_stats,
        file_name="nba_cup_final_advanced_team_box_score.csv",
    )

    advanced_player_path = save_raw_dataframe(
        dataframe=advanced_player_stats,
        file_name="nba_cup_final_advanced_player_box_score.csv",
    )

    print(
        f"Advanced team rows retrieved: "
        f"{len(advanced_team_stats)}"
    )

    print(
        f"Advanced player rows retrieved: "
        f"{len(advanced_player_stats)}"
    )

    print(f"Saved to: {advanced_team_path}")
    print(f"Saved to: {advanced_player_path}")
    print()


def collect_initial_raw_data() -> None:
    """Run the current raw-data collection pipeline."""

    print("Starting traditional game-log collection.")
    print()

    collect_all_team_game_logs()

    sleep(1)

    print("Starting advanced game-log collection.")
    print()

    collect_all_advanced_team_game_logs()

    sleep(1)

    collect_nba_cup_final()

    print("Initial raw-data collection completed successfully.")


if __name__ == "__main__":
    collect_initial_raw_data()