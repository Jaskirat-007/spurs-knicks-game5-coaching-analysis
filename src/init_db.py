"""Initialize the project SQLite database."""

from pathlib import Path
import sqlite3


PROJECT_ROOT = Path(__file__).resolve().parents[1]

SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

DATABASE_PATH = (
    PROJECT_ROOT
    / "data"
    / "processed"
    / "nba_finals_game5.db"
)


def initialize_database() -> None:
    """Create the SQLite database using schema.sql."""

    if not SCHEMA_PATH.exists():
        raise FileNotFoundError(
            f"Schema file not found: {SCHEMA_PATH}"
        )

    DATABASE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    schema_sql = SCHEMA_PATH.read_text(
        encoding="utf-8"
    )

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute(
            "PRAGMA foreign_keys = ON;"
        )

        connection.executescript(schema_sql)

        connection.commit()

    print("Database initialized successfully.")
    print(f"Database location: {DATABASE_PATH}")


if __name__ == "__main__":
    initialize_database()