"""Load cleaned team-game data into the SQLite database."""

from datetime import date
import sqlite3

import pandas as pd
from nba_api.stats.static import teams

from config import (
    DATABASE_PATH,
    HOLDOUT_GAME_ID,
    INTERIM_DATA_DIR,
)


TEAM_GAME_STATS_PATH = (
    INTERIM_DATA_DIR
    / "team_game_stats_all.csv"
)


TEAM_GAME_STATS_COLUMNS = [
    "game_id",
    "team_id",
    "opponent_team_id",
    "is_home",
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


def load_cleaned_team_game_data() -> pd.DataFrame:
    """Load the cleaned team-game CSV."""

    if not TEAM_GAME_STATS_PATH.exists():
        raise FileNotFoundError(
            f"Cleaned team-game file not found: "
            f"{TEAM_GAME_STATS_PATH}"
        )

    dataframe = pd.read_csv(
        TEAM_GAME_STATS_PATH,
        dtype={
            "game_id": "string",
        },
    )

    if dataframe.empty:
        raise ValueError(
            "The cleaned team-game dataset contains no rows."
        )

    return dataframe


def build_teams_table() -> pd.DataFrame:
    """Build the teams table from nba_api's team directory."""

    nba_teams = teams.get_teams()

    teams_table = pd.DataFrame(
        [
            {
                "team_id": team["id"],
                "team_name": team["full_name"],
                "abbreviation": team["abbreviation"],
            }
            for team in nba_teams
        ]
    )

    if teams_table["team_id"].duplicated().any():
        raise ValueError(
            "Duplicate team IDs were found."
        )

    if teams_table["abbreviation"].duplicated().any():
        raise ValueError(
            "Duplicate team abbreviations were found."
        )

    return teams_table


def first_non_null(
    values: pd.Series,
):
    """Return the first non-null value in a pandas Series."""

    non_null_values = values.dropna()

    if non_null_values.empty:
        return None

    return non_null_values.iloc[0]


def build_games_table(
    team_game_stats: pd.DataFrame,
) -> pd.DataFrame:
    """Create one games-table row for each unique game."""

    game_rows = team_game_stats[
        [
            "game_id",
            "game_date",
            "season",
            "season_type",
            "series_game_number",
            "team_id",
            "opponent_team_id",
            "is_home",
            "points",
            "is_pregame",
            "is_holdout",
        ]
    ].copy()

    game_rows["home_team_id"] = game_rows[
        "team_id"
    ].where(
        game_rows["is_home"] == 1,
        game_rows["opponent_team_id"],
    )

    game_rows["away_team_id"] = game_rows[
        "opponent_team_id"
    ].where(
        game_rows["is_home"] == 1,
        game_rows["team_id"],
    )

    game_rows["home_score"] = game_rows[
        "points"
    ].where(
        game_rows["is_home"] == 1
    )

    game_rows["away_score"] = game_rows[
        "points"
    ].where(
        game_rows["is_home"] == 0
    )

    games_table = (
        game_rows
        .groupby(
            "game_id",
            as_index=False,
        )
        .agg(
            {
                "game_date": "first",
                "season": "first",
                "season_type": "first",
                "series_game_number": first_non_null,
                "home_team_id": "first",
                "away_team_id": "first",
                "home_score": first_non_null,
                "away_score": first_non_null,
                "is_pregame": "max",
                "is_holdout": "max",
            }
        )
    )

    games_table["source"] = "nba_api"

    games_table["data_retrieval_date"] = (
        date.today().isoformat()
    )

    games_table = games_table[
        [
            "game_id",
            "game_date",
            "season",
            "season_type",
            "series_game_number",
            "home_team_id",
            "away_team_id",
            "home_score",
            "away_score",
            "is_pregame",
            "is_holdout",
            "source",
            "data_retrieval_date",
        ]
    ]

    if games_table["game_id"].duplicated().any():
        raise ValueError(
            "Duplicate game IDs were created."
        )

    invalid_matchups = games_table.loc[
        games_table["home_team_id"]
        == games_table["away_team_id"]
    ]

    if not invalid_matchups.empty:
        raise ValueError(
            "A game has the same home and away team."
        )

    return games_table


def build_team_game_stats_table(
    cleaned_data: pd.DataFrame,
) -> pd.DataFrame:
    """Select and order fields for the team_game_stats table."""

    missing_columns = (
        set(TEAM_GAME_STATS_COLUMNS)
        - set(cleaned_data.columns)
    )

    if missing_columns:
        raise ValueError(
            "The cleaned dataset is missing database columns: "
            f"{sorted(missing_columns)}"
        )

    team_game_stats_table = cleaned_data[
        TEAM_GAME_STATS_COLUMNS
    ].copy()

    duplicate_rows = team_game_stats_table.duplicated(
        subset=[
            "game_id",
            "team_id",
        ]
    )

    if duplicate_rows.any():
        raise ValueError(
            "Duplicate game and team combinations were found."
        )

    return team_game_stats_table


def prepare_for_sql(
    dataframe: pd.DataFrame,
) -> pd.DataFrame:
    """Convert pandas missing values into SQLite-compatible nulls."""

    return (
        dataframe
        .astype(object)
        .where(
            pd.notna(dataframe),
            None,
        )
    )


def clear_existing_team_data(
    connection: sqlite3.Connection,
) -> None:
    """Clear existing team-level records before reloading."""

    connection.execute(
        "DELETE FROM team_game_stats;"
    )

    connection.execute(
        "DELETE FROM games;"
    )

    connection.execute(
        "DELETE FROM teams;"
    )


def load_tables_into_database(
    teams_table: pd.DataFrame,
    games_table: pd.DataFrame,
    team_game_stats_table: pd.DataFrame,
) -> None:
    """Insert teams, games, and team statistics into SQLite."""

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        clear_existing_team_data(
            connection
        )

        prepare_for_sql(
            teams_table
        ).to_sql(
            "teams",
            connection,
            if_exists="append",
            index=False,
        )

        prepare_for_sql(
            games_table
        ).to_sql(
            "games",
            connection,
            if_exists="append",
            index=False,
        )

        prepare_for_sql(
            team_game_stats_table
        ).to_sql(
            "team_game_stats",
            connection,
            if_exists="append",
            index=False,
        )

        connection.commit()


def validate_loaded_database(
    expected_team_count: int,
    expected_game_count: int,
    expected_team_game_count: int,
) -> None:
    """Confirm the expected records were inserted."""

    with sqlite3.connect(
        DATABASE_PATH
    ) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        team_count = connection.execute(
            "SELECT COUNT(*) FROM teams;"
        ).fetchone()[0]

        game_count = connection.execute(
            "SELECT COUNT(*) FROM games;"
        ).fetchone()[0]

        team_game_count = connection.execute(
            "SELECT COUNT(*) FROM team_game_stats;"
        ).fetchone()[0]

        holdout_game_ids = connection.execute(
            """
            SELECT game_id
            FROM holdout_games
            ORDER BY game_id;
            """
        ).fetchall()

        foreign_key_errors = connection.execute(
            "PRAGMA foreign_key_check;"
        ).fetchall()

    if team_count != expected_team_count:
        raise ValueError(
            f"Expected {expected_team_count} teams, "
            f"but found {team_count}."
        )

    if game_count != expected_game_count:
        raise ValueError(
            f"Expected {expected_game_count} games, "
            f"but found {game_count}."
        )

    if team_game_count != expected_team_game_count:
        raise ValueError(
            f"Expected {expected_team_game_count} "
            f"team-game rows, but found {team_game_count}."
        )

    if holdout_game_ids != [
        (HOLDOUT_GAME_ID,)
    ]:
        raise ValueError(
            "The holdout view does not contain exactly Game 5."
        )

    if foreign_key_errors:
        raise ValueError(
            "Foreign-key validation failed: "
            f"{foreign_key_errors}"
        )

    print(f"Teams loaded: {team_count}")
    print(f"Games loaded: {game_count}")
    print(
        f"Team-game rows loaded: {team_game_count}"
    )
    print(
        f"Holdout game: {holdout_game_ids[0][0]}"
    )
    print("Foreign-key validation passed.")


def load_team_data() -> None:
    """Run the team-level database loading stage."""

    print("Preparing team-level database tables.")

    cleaned_data = (
        load_cleaned_team_game_data()
    )

    teams_table = build_teams_table()

    games_table = build_games_table(
        team_game_stats=cleaned_data
    )

    team_game_stats_table = (
        build_team_game_stats_table(
            cleaned_data=cleaned_data
        )
    )

    print(f"Teams prepared: {len(teams_table)}")
    print(f"Games prepared: {len(games_table)}")
    print(
        "Team-game rows prepared: "
        f"{len(team_game_stats_table)}"
    )

    load_tables_into_database(
        teams_table=teams_table,
        games_table=games_table,
        team_game_stats_table=team_game_stats_table,
    )

    validate_loaded_database(
        expected_team_count=len(teams_table),
        expected_game_count=len(games_table),
        expected_team_game_count=(
            len(team_game_stats_table)
        ),
    )

    print(
        "Team-level database loading completed successfully."
    )


if __name__ == "__main__":
    load_team_data()