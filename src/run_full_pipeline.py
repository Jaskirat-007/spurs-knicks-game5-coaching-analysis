"""Run the complete reproducible build from collection through exports."""

import argparse

from clean_analysis_data import save_analysis_interim_data
from clean_data import run_team_game_cleaning
from collect_analysis_data import collect_analysis_data
from collect_data import collect_initial_raw_data
from export_analysis_outputs import export_analysis_outputs
from init_db import initialize_database
from load_analysis_data import load_analysis_data
from load_data import load_team_data
from validate_data import validate_raw_data
from validate_analysis_data import validate_analysis_raw_data
from config import DATABASE_PATH


def parse_arguments() -> argparse.Namespace:
    """Read command-line options."""

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-collection",
        action="store_true",
        help="Use existing raw files instead of calling NBA endpoints.",
    )
    return parser.parse_args()


def run_full_pipeline(skip_collection: bool) -> None:
    """Run all project stages in dependency order."""

    if not skip_collection:
        collect_initial_raw_data()
        collect_analysis_data()

    validate_raw_data()
    validate_analysis_raw_data()
    run_team_game_cleaning()

    if DATABASE_PATH.exists():
        DATABASE_PATH.unlink()

    initialize_database()
    load_team_data()
    save_analysis_interim_data()
    load_analysis_data()
    export_analysis_outputs()

    print("Full project build completed successfully.")


if __name__ == "__main__":
    arguments = parse_arguments()
    run_full_pipeline(skip_collection=arguments.skip_collection)
