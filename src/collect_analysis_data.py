"""Collect player, shot, play-by-play, box-score, and lineup data."""

from collections.abc import Callable
from pathlib import Path
from time import sleep

import pandas as pd
from nba_api.stats.endpoints import (
    boxscoreadvancedv3,
    boxscoretraditionalv3,
    playergamelogs,
    playbyplayv3,
    shotchartdetail,
    teamdashlineups,
)

from config import (
    ANALYSIS_GAME_IDS,
    API_REQUEST_DELAY_SECONDS,
    API_RETRY_ATTEMPTS,
    API_TIMEOUT_SECONDS,
    FINALS_START_DATE,
    GAME_METADATA,
    KNICKS_TEAM_ID,
    PLAYOFFS_SEASON_TYPE,
    PREGAME_CUTOFF_DATE,
    PRE_FINALS_CUTOFF_DATE,
    RAW_GAME_BOX_SCORE_DIR,
    RAW_LINEUP_DIR,
    RAW_PLAYER_LOG_DIR,
    RAW_PLAY_BY_PLAY_DIR,
    RAW_SHOT_DIR,
    REGULAR_SEASON_TYPE,
    SPURS_TEAM_ID,
    TARGET_SEASON,
)


TEAM_JOBS = [
    (SPURS_TEAM_ID, "SAS", REGULAR_SEASON_TYPE),
    (SPURS_TEAM_ID, "SAS", PLAYOFFS_SEASON_TYPE),
    (KNICKS_TEAM_ID, "NYK", REGULAR_SEASON_TYPE),
    (KNICKS_TEAM_ID, "NYK", PLAYOFFS_SEASON_TYPE),
]

LINEUP_SAMPLES = [
    {
        "sample_name": "Full Regular Season",
        "season_type": REGULAR_SEASON_TYPE,
        "date_from": "",
        "date_to": "",
        "last_n_games": 0,
    },
    {
        "sample_name": "Playoffs Before Finals",
        "season_type": PLAYOFFS_SEASON_TYPE,
        "date_from": "",
        "date_to": PRE_FINALS_CUTOFF_DATE,
        "last_n_games": 0,
    },
    {
        "sample_name": "Finals Games 1-4",
        "season_type": PLAYOFFS_SEASON_TYPE,
        "date_from": FINALS_START_DATE,
        "date_to": "2026-06-10",
        "last_n_games": 0,
    },
    {
        "sample_name": "Last 10 Before Game 5",
        "season_type": PLAYOFFS_SEASON_TYPE,
        "date_from": "",
        "date_to": PREGAME_CUTOFF_DATE,
        "last_n_games": 10,
    },
]


def ensure_raw_directories() -> None:
    """Create all raw-data subdirectories."""

    for directory in [
        RAW_PLAYER_LOG_DIR,
        RAW_GAME_BOX_SCORE_DIR,
        RAW_SHOT_DIR,
        RAW_PLAY_BY_PLAY_DIR,
        RAW_LINEUP_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def safe_name(value: str) -> str:
    """Convert a label into a filename-safe value."""

    return (
        value.strip()
        .lower()
        .replace("-", "_")
        .replace(" ", "_")
        .replace("/", "_")
    )


def save_dataframe(
    dataframe: pd.DataFrame,
    file_path: Path,
) -> None:
    """Save a DataFrame without adding a pandas index."""

    file_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(file_path, index=False)
    print(f"Saved {len(dataframe)} rows to {file_path}")


def run_with_retry(
    request_function: Callable[[], pd.DataFrame],
    label: str,
) -> pd.DataFrame:
    """Run an NBA API request with incremental retry delays."""

    last_error: Exception | None = None

    for attempt in range(1, API_RETRY_ATTEMPTS + 1):
        try:
            dataframe = request_function()
            return dataframe
        except Exception as error:
            last_error = error

            if attempt == API_RETRY_ATTEMPTS:
                break

            wait_seconds = API_REQUEST_DELAY_SECONDS * attempt
            print(
                f"{label} failed on attempt {attempt}: {error}. "
                f"Retrying in {wait_seconds:.1f} seconds."
            )
            sleep(wait_seconds)

    raise RuntimeError(
        f"{label} failed after {API_RETRY_ATTEMPTS} attempts."
    ) from last_error


def fetch_player_game_logs(
    team_id: int,
    season_type: str,
    measure_type: str,
) -> pd.DataFrame:
    """Fetch player game logs for one team, sample, and measure."""

    def request() -> pd.DataFrame:
        response = playergamelogs.PlayerGameLogs(
            team_id_nullable=team_id,
            season_nullable=TARGET_SEASON,
            season_type_nullable=season_type,
            measure_type_player_game_logs_nullable=measure_type,
            per_mode_simple_nullable="Totals",
            timeout=API_TIMEOUT_SECONDS,
        )
        return response.player_game_logs.get_data_frame()

    dataframe = run_with_retry(
        request_function=request,
        label=f"PlayerGameLogs {team_id} {season_type} {measure_type}",
    )

    if dataframe.empty:
        raise ValueError(
            f"No player game logs returned for {team_id}, "
            f"{season_type}, {measure_type}."
        )

    return dataframe


def collect_player_game_logs() -> None:
    """Collect base and advanced player game logs for both teams."""

    for team_id, abbreviation, season_type in TEAM_JOBS:
        for measure_type in ["Base", "Advanced"]:
            print(
                f"Collecting {abbreviation} {season_type} "
                f"player logs ({measure_type})."
            )

            dataframe = fetch_player_game_logs(
                team_id=team_id,
                season_type=season_type,
                measure_type=measure_type,
            )

            file_name = (
                f"{abbreviation.lower()}_"
                f"{safe_name(season_type)}_"
                f"{safe_name(measure_type)}_player_game_logs.csv"
            )

            save_dataframe(
                dataframe=dataframe,
                file_path=RAW_PLAYER_LOG_DIR / file_name,
            )
            sleep(API_REQUEST_DELAY_SECONDS)


def fetch_game_player_box_score(
    game_id: str,
    measure_type: str,
) -> pd.DataFrame:
    """Fetch one game's player box score."""

    def request() -> pd.DataFrame:
        if measure_type == "traditional":
            response = boxscoretraditionalv3.BoxScoreTraditionalV3(
                game_id=game_id,
                timeout=API_TIMEOUT_SECONDS,
            )
        elif measure_type == "advanced":
            response = boxscoreadvancedv3.BoxScoreAdvancedV3(
                game_id=game_id,
                timeout=API_TIMEOUT_SECONDS,
            )
        else:
            raise ValueError(f"Unknown box-score type: {measure_type}")

        return response.player_stats.get_data_frame()

    dataframe = run_with_retry(
        request_function=request,
        label=f"{measure_type} player box score {game_id}",
    )

    if dataframe.empty:
        raise ValueError(
            f"No {measure_type} player box score returned for {game_id}."
        )

    return dataframe


def collect_game_player_box_scores() -> None:
    """Collect game-level player box scores for matchup games."""

    for game_id in ANALYSIS_GAME_IDS:
        for measure_type in ["traditional", "advanced"]:
            print(
                f"Collecting {measure_type} player box score "
                f"for {game_id}."
            )

            dataframe = fetch_game_player_box_score(
                game_id=game_id,
                measure_type=measure_type,
            )

            save_dataframe(
                dataframe=dataframe,
                file_path=(
                    RAW_GAME_BOX_SCORE_DIR
                    / f"{game_id}_{measure_type}_players.csv"
                ),
            )
            sleep(API_REQUEST_DELAY_SECONDS)


def fetch_shots(game_id: str) -> pd.DataFrame:
    """Fetch all shot attempts for one game."""

    endpoint_season_type = GAME_METADATA[game_id][
        "endpoint_season_type"
    ]

    def request() -> pd.DataFrame:
        response = shotchartdetail.ShotChartDetail(
            team_id=0,
            player_id=0,
            context_measure_simple="FGA",
            game_id_nullable=game_id,
            season_nullable=TARGET_SEASON,
            season_type_all_star=endpoint_season_type,
            timeout=API_TIMEOUT_SECONDS,
        )
        return response.shot_chart_detail.get_data_frame()

    return run_with_retry(
        request_function=request,
        label=f"ShotChartDetail {game_id}",
    )


def collect_shots() -> None:
    """Collect shot charts for every matchup and holdout game."""

    for game_id in ANALYSIS_GAME_IDS:
        print(f"Collecting shots for {game_id}.")
        dataframe = fetch_shots(game_id)

        save_dataframe(
            dataframe=dataframe,
            file_path=RAW_SHOT_DIR / f"{game_id}_shots.csv",
        )
        sleep(API_REQUEST_DELAY_SECONDS)


def fetch_play_by_play(game_id: str) -> pd.DataFrame:
    """Fetch V3 play-by-play for one game."""

    def request() -> pd.DataFrame:
        response = playbyplayv3.PlayByPlayV3(
            game_id=game_id,
            start_period=1,
            end_period=10,
            timeout=API_TIMEOUT_SECONDS,
        )
        return response.play_by_play.get_data_frame()

    dataframe = run_with_retry(
        request_function=request,
        label=f"PlayByPlayV3 {game_id}",
    )

    if dataframe.empty:
        raise ValueError(f"No play-by-play returned for {game_id}.")

    return dataframe


def collect_play_by_play() -> None:
    """Collect play-by-play for every matchup and holdout game."""

    for game_id in ANALYSIS_GAME_IDS:
        print(f"Collecting play-by-play for {game_id}.")
        dataframe = fetch_play_by_play(game_id)

        save_dataframe(
            dataframe=dataframe,
            file_path=RAW_PLAY_BY_PLAY_DIR / f"{game_id}_pbp.csv",
        )
        sleep(API_REQUEST_DELAY_SECONDS)


def fetch_lineups(
    team_id: int,
    season_type: str,
    measure_type: str,
    date_from: str,
    date_to: str,
    last_n_games: int,
) -> pd.DataFrame:
    """Fetch five-player lineup aggregates for one team and sample."""

    def request() -> pd.DataFrame:
        response = teamdashlineups.TeamDashLineups(
            team_id=team_id,
            group_quantity=5,
            last_n_games=last_n_games,
            measure_type_detailed_defense=measure_type,
            month=0,
            opponent_team_id=0,
            pace_adjust="N",
            per_mode_detailed="Totals",
            period=0,
            plus_minus="N",
            rank="N",
            season=TARGET_SEASON,
            season_type_all_star=season_type,
            date_from_nullable=date_from,
            date_to_nullable=date_to,
            timeout=API_TIMEOUT_SECONDS,
        )
        return response.lineups.get_data_frame()

    return run_with_retry(
        request_function=request,
        label=(
            f"TeamDashLineups {team_id} {season_type} "
            f"{measure_type} {date_from} {date_to}"
        ),
    )


def collect_lineups() -> None:
    """Collect lineup aggregates for the four analysis windows."""

    teams = [
        (SPURS_TEAM_ID, "SAS"),
        (KNICKS_TEAM_ID, "NYK"),
    ]

    for sample in LINEUP_SAMPLES:
        for team_id, abbreviation in teams:
            for measure_type in ["Base", "Advanced"]:
                print(
                    f"Collecting {abbreviation} lineups: "
                    f"{sample['sample_name']} ({measure_type})."
                )

                dataframe = fetch_lineups(
                    team_id=team_id,
                    season_type=sample["season_type"],
                    measure_type=measure_type,
                    date_from=sample["date_from"],
                    date_to=sample["date_to"],
                    last_n_games=sample["last_n_games"],
                )

                file_name = (
                    f"{abbreviation.lower()}_"
                    f"{safe_name(sample['sample_name'])}_"
                    f"{safe_name(measure_type)}_lineups.csv"
                )

                save_dataframe(
                    dataframe=dataframe,
                    file_path=RAW_LINEUP_DIR / file_name,
                )
                sleep(API_REQUEST_DELAY_SECONDS)


def collect_analysis_data() -> None:
    """Run all remaining analysis-data collection stages."""

    ensure_raw_directories()

    collect_player_game_logs()
    collect_game_player_box_scores()
    collect_shots()
    collect_play_by_play()
    collect_lineups()

    print("Analysis-data collection completed successfully.")


if __name__ == "__main__":
    collect_analysis_data()
