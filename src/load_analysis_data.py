"""Load cleaned player, shot, play-by-play, and lineup data into SQLite."""

import sqlite3
from pathlib import Path

import pandas as pd

from config import DATABASE_PATH, INTERIM_DATA_DIR


FILE_TABLE_MAP = {
    "player_game_stats_all.csv": "player_game_stats",
    "shots_all.csv": "shots",
    "play_by_play_all.csv": "play_by_play",
    "lineup_aggregates.csv": "lineup_aggregates",
    "lineup_players.csv": "lineup_players",
}


def read_interim_csv(
    file_name: str,
    dtype: dict[str, str] | None = None,
) -> pd.DataFrame:
    """Load an interim CSV and fail clearly when it is missing."""

    file_path = INTERIM_DATA_DIR / file_name

    if not file_path.exists():
        raise FileNotFoundError(f"Missing interim file: {file_path}")

    return pd.read_csv(file_path, dtype=dtype)


def prepare_for_sql(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Convert pandas missing values into SQLite-compatible nulls."""

    return dataframe.astype(object).where(pd.notna(dataframe), None)


def collect_required_player_ids(
    player_game_stats: pd.DataFrame,
    shots: pd.DataFrame,
    play_by_play: pd.DataFrame,
    lineup_players: pd.DataFrame,
) -> set[int]:
    """Collect every player ID referenced by a child table."""

    required_ids: set[int] = set()

    for dataframe, column in [
        (player_game_stats, "player_id"),
        (shots, "player_id"),
        (shots, "assister_player_id"),
        (play_by_play, "player1_id"),
        (play_by_play, "player2_id"),
        (play_by_play, "player3_id"),
        (lineup_players, "player_id"),
    ]:
        if column not in dataframe.columns:
            continue

        values = pd.to_numeric(dataframe[column], errors="coerce").dropna()
        required_ids.update(values.astype(int).tolist())

    return required_ids


def add_placeholder_players(
    players: pd.DataFrame,
    required_player_ids: set[int],
) -> pd.DataFrame:
    """Add minimal rows for referenced IDs absent from player logs."""

    existing_ids = set(players["player_id"].astype(int))
    missing_ids = sorted(required_player_ids - existing_ids)

    if not missing_ids:
        return players

    placeholders = pd.DataFrame(
        {
            "player_id": missing_ids,
            "full_name": [
                f"Unknown Player {player_id}" for player_id in missing_ids
            ],
            "current_team_id": [None] * len(missing_ids),
            "position": [None] * len(missing_ids),
        }
    )

    print(f"Added {len(placeholders)} placeholder player rows.")
    return pd.concat([players, placeholders], ignore_index=True)


def validate_game_foreign_keys(
    connection: sqlite3.Connection,
    dataframe: pd.DataFrame,
    table_name: str,
) -> None:
    """Confirm every game ID in a dataset already exists in games."""

    if "game_id" not in dataframe.columns:
        return

    database_game_ids = {
        row[0]
        for row in connection.execute("SELECT game_id FROM games;").fetchall()
    }
    data_game_ids = set(dataframe["game_id"].dropna().astype(str))
    missing_ids = sorted(data_game_ids - database_game_ids)

    if missing_ids:
        raise ValueError(
            f"{table_name} contains game IDs absent from games: {missing_ids}"
        )


def clear_analysis_tables(connection: sqlite3.Connection) -> None:
    """Clear analysis tables in child-to-parent order."""

    for table_name in [
        "lineup_players",
        "lineup_aggregates",
        "lineups",
        "shots",
        "play_by_play",
        "player_game_stats",
        "players",
    ]:
        connection.execute(f"DELETE FROM {table_name};")


def load_analysis_data() -> None:
    """Load all cleaned analysis datasets into SQLite."""

    players = read_interim_csv("players.csv")
    player_game_stats = read_interim_csv(
        "player_game_stats_all.csv",
        dtype={"game_id": "string"},
    )
    shots = read_interim_csv(
        "shots_all.csv",
        dtype={"game_id": "string", "shot_id": "string"},
    )
    play_by_play = read_interim_csv(
        "play_by_play_all.csv",
        dtype={"game_id": "string"},
    )
    lineup_aggregates = read_interim_csv("lineup_aggregates.csv")
    lineup_players = read_interim_csv("lineup_players.csv")

    if "team_id" in play_by_play.columns:
        play_by_play.loc[play_by_play["team_id"].eq(0), "team_id"] = None

    required_player_ids = collect_required_player_ids(
        player_game_stats=player_game_stats,
        shots=shots,
        play_by_play=play_by_play,
        lineup_players=lineup_players,
    )
    players = add_placeholder_players(players, required_player_ids)

    if players["player_id"].duplicated().any():
        raise ValueError("Duplicate player IDs found before database load.")

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")

        validate_game_foreign_keys(
            connection, player_game_stats, "player_game_stats"
        )
        validate_game_foreign_keys(connection, shots, "shots")
        validate_game_foreign_keys(connection, play_by_play, "play_by_play")

        clear_analysis_tables(connection)

        prepare_for_sql(players).to_sql(
            "players",
            connection,
            if_exists="append",
            index=False,
        )
        prepare_for_sql(player_game_stats).to_sql(
            "player_game_stats",
            connection,
            if_exists="append",
            index=False,
        )
        prepare_for_sql(shots).to_sql(
            "shots",
            connection,
            if_exists="append",
            index=False,
        )
        prepare_for_sql(play_by_play).to_sql(
            "play_by_play",
            connection,
            if_exists="append",
            index=False,
        )
        prepare_for_sql(lineup_aggregates).to_sql(
            "lineup_aggregates",
            connection,
            if_exists="append",
            index=False,
        )
        prepare_for_sql(lineup_players).to_sql(
            "lineup_players",
            connection,
            if_exists="append",
            index=False,
        )

        connection.commit()

        counts = {
            table_name: connection.execute(
                f"SELECT COUNT(*) FROM {table_name};"
            ).fetchone()[0]
            for table_name in [
                "players",
                "player_game_stats",
                "shots",
                "play_by_play",
                "lineup_aggregates",
                "lineup_players",
            ]
        }

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

    if foreign_key_errors:
        raise ValueError(
            f"Foreign-key validation failed: {foreign_key_errors}"
        )

    for table_name, row_count in counts.items():
        print(f"{table_name}: {row_count} rows")

    print("Analysis database loading completed successfully.")


if __name__ == "__main__":
    load_analysis_data()
