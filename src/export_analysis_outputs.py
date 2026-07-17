"""Export analysis-ready pregame outputs from SQLite.

The stable team, player, shot, and lineup outputs are produced from SQL files.
Quarter, scoring-run, and rotation outputs are rebuilt in Python because the
NBA play-by-play feed stores cumulative scores only on some event rows.
"""

from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pandas as pd

from config import ANALYSIS_OUTPUT_DIR, DATABASE_PATH, PROJECT_ROOT


SQL_OUTPUTS = {
    "game_summary.sql": "team_comparison_windows.csv",
    "finals_game_by_game.sql": "finals_games_1_4_team_stats.csv",
    "player_splits.sql": "player_comparison_windows.csv",
    "matchup_player_games.sql": "pregame_matchup_player_games.csv",
    "shot_profile.sql": "pregame_shot_profiles.csv",
    "lineup_analysis.sql": "pregame_lineup_analysis.csv",
}

FINALS_GAME_MIN = 1
FINALS_GAME_MAX = 4
MIN_SCORING_RUN_POINTS = 6


class PlayByPlayDataError(ValueError):
    """Raised when scoreboard data cannot support a trustworthy export."""


def read_sql_file(file_name: str) -> str:
    """Read one SQL query from the project sql directory."""

    file_path = PROJECT_ROOT / "sql" / file_name
    if not file_path.exists():
        raise FileNotFoundError(f"Missing SQL file: {file_path}")
    return file_path.read_text(encoding="utf-8")


def normalize_player_turnover_percentages(
    connection: sqlite3.Connection,
) -> int:
    """Normalize mixed player turnover-percentage units to decimal form.

    Some NBA player-log endpoints return TM_TOV_PCT as a whole percentage
    such as 7.6, while the game-level advanced feed is stored as a decimal
    such as 0.076. Values above 1.0 are therefore divided by 100. The update
    is idempotent because normalized values no longer satisfy the condition.
    """

    affected = connection.execute(
        """
        SELECT COUNT(*)
        FROM player_game_stats
        WHERE turnover_pct > 1.0;
        """
    ).fetchone()[0]

    connection.execute(
        """
        UPDATE player_game_stats
        SET turnover_pct = turnover_pct / 100.0
        WHERE turnover_pct > 1.0;
        """
    )
    connection.commit()
    return int(affected)


def load_finals_context(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load home, away, team-name, and final-score context for Games 1-4."""

    query = """
        SELECT
            g.game_id,
            g.series_game_number,
            g.home_team_id,
            g.away_team_id,
            home.abbreviation AS home_team,
            away.abbreviation AS away_team,
            home.team_name AS home_team_name,
            away.team_name AS away_team_name,
            g.home_score AS official_home_score,
            g.away_score AS official_away_score
        FROM pregame_games AS g
        JOIN teams AS home
            ON g.home_team_id = home.team_id
        JOIN teams AS away
            ON g.away_team_id = away.team_id
        WHERE g.series_game_number BETWEEN ? AND ?
        ORDER BY g.series_game_number;
    """

    context = pd.read_sql_query(
        query,
        connection,
        params=(FINALS_GAME_MIN, FINALS_GAME_MAX),
        dtype={"game_id": "string"},
    )

    if len(context) != 4:
        raise PlayByPlayDataError(
            f"Expected four Finals games before Game 5, found {len(context)}."
        )

    return context


def load_finals_play_by_play(
    connection: sqlite3.Connection,
) -> pd.DataFrame:
    """Load every play-by-play event for Finals Games 1-4."""

    query = """
        SELECT
            g.series_game_number,
            pbp.game_id,
            pbp.period,
            pbp.game_clock,
            pbp.seconds_remaining,
            pbp.event_number,
            pbp.team_id,
            pbp.event_type,
            pbp.action_type,
            pbp.event_description,
            pbp.home_score,
            pbp.away_score,
            pbp.is_turnover,
            pbp.is_foul,
            pbp.is_substitution,
            pbp.is_timeout
        FROM play_by_play AS pbp
        JOIN pregame_games AS g
            ON pbp.game_id = g.game_id
        WHERE g.series_game_number BETWEEN ? AND ?
        ORDER BY
            g.series_game_number,
            pbp.period,
            pbp.event_number;
    """

    dataframe = pd.read_sql_query(
        query,
        connection,
        params=(FINALS_GAME_MIN, FINALS_GAME_MAX),
        dtype={"game_id": "string"},
    )

    if dataframe.empty:
        raise PlayByPlayDataError("No Finals Games 1-4 play-by-play rows found.")

    duplicate_events = dataframe.duplicated(
        subset=["game_id", "event_number"],
        keep=False,
    )
    if duplicate_events.any():
        examples = dataframe.loc[
            duplicate_events,
            ["game_id", "event_number", "event_description"],
        ].head(10)
        raise PlayByPlayDataError(
            "The database event_number field is not unique within game. "
            "The cleaner should store actionId as event_number when actionId "
            "is available. Examples:\n"
            f"{examples.to_string(index=False)}"
        )

    return dataframe


def add_filled_scores(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Forward-fill cumulative home and away scores inside each game."""

    result = dataframe.copy()
    result["home_score"] = pd.to_numeric(
        result["home_score"], errors="coerce"
    )
    result["away_score"] = pd.to_numeric(
        result["away_score"], errors="coerce"
    )

    result[["home_score", "away_score"]] = (
        result.groupby("game_id", sort=False)[["home_score", "away_score"]]
        .ffill()
        .fillna(0)
    )

    result["home_score"] = result["home_score"].astype(int)
    result["away_score"] = result["away_score"].astype(int)

    for score_column in ["home_score", "away_score"]:
        score_change = result.groupby("game_id", sort=False)[score_column].diff()
        if (score_change.dropna() < 0).any():
            bad = result.loc[
                score_change < 0,
                [
                    "game_id",
                    "period",
                    "game_clock",
                    "event_number",
                    "event_description",
                    "home_score",
                    "away_score",
                ],
            ].head(10)
            raise PlayByPlayDataError(
                f"Score decreased in {score_column}. Review these events:\n"
                f"{bad.to_string(index=False)}"
            )

    return result


def team_aliases(abbreviation: str, full_name: str) -> list[str]:
    """Build text tokens that can identify a team in an event description."""

    full_name = str(full_name).strip().upper()
    abbreviation = str(abbreviation).strip().upper()
    words = full_name.split()

    aliases = [full_name, abbreviation]
    if words:
        aliases.append(words[-1])
    if len(words) > 1:
        aliases.append(" ".join(words[:-1]))

    return sorted(set(alias for alias in aliases if alias), key=len, reverse=True)


def description_mentions_alias(description: str, alias: str) -> bool:
    """Return whether a normalized description contains a team alias."""

    if " " in alias:
        return alias in description
    return re.search(rf"\b{re.escape(alias)}\b", description) is not None


def infer_event_team(
    row: pd.Series,
    game_context: pd.Series,
) -> tuple[int | None, str | None]:
    """Resolve event team from team_id or the event description."""

    valid_teams = {
        int(game_context["home_team_id"]): str(game_context["home_team"]),
        int(game_context["away_team_id"]): str(game_context["away_team"]),
    }

    team_id = pd.to_numeric(row.get("team_id"), errors="coerce")
    if pd.notna(team_id) and int(team_id) in valid_teams:
        resolved_id = int(team_id)
        return resolved_id, valid_teams[resolved_id]

    description = str(row.get("event_description") or "").upper()
    candidates = [
        (
            int(game_context["home_team_id"]),
            str(game_context["home_team"]),
            str(game_context["home_team_name"]),
        ),
        (
            int(game_context["away_team_id"]),
            str(game_context["away_team"]),
            str(game_context["away_team_name"]),
        ),
    ]

    matches: list[tuple[int, str]] = []
    for candidate_id, abbreviation, full_name in candidates:
        aliases = team_aliases(abbreviation, full_name)
        if any(
            description_mentions_alias(description, alias)
            for alias in aliases
        ):
            matches.append((candidate_id, abbreviation))

    if len(matches) == 1:
        return matches[0]

    return None, None


def add_event_team_labels(
    play_by_play: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    """Add resolved team ID and abbreviation to every event."""

    result_parts: list[pd.DataFrame] = []
    context_by_game = context.set_index("game_id")

    for game_id, game_events in play_by_play.groupby("game_id", sort=False):
        if game_id not in context_by_game.index:
            raise PlayByPlayDataError(f"Missing game context for {game_id}.")

        game_context = context_by_game.loc[game_id]
        resolved = game_events.apply(
            lambda row: infer_event_team(row, game_context),
            axis=1,
            result_type="expand",
        )
        resolved.columns = ["resolved_team_id", "team"]

        game_result = game_events.copy()
        game_result["resolved_team_id"] = resolved["resolved_team_id"]
        game_result["team"] = resolved["team"]
        result_parts.append(game_result)

    return pd.concat(result_parts, ignore_index=True)


def validate_final_scores(
    play_by_play: pd.DataFrame,
    context: pd.DataFrame,
) -> None:
    """Confirm the final cumulative scoreboard matches the games table."""

    last_scores = (
        play_by_play.sort_values(["game_id", "period", "event_number"])
        .groupby("game_id", as_index=False)
        .tail(1)[["game_id", "home_score", "away_score"]]
    )

    comparison = context.merge(last_scores, on="game_id", how="left")
    for side in ["home", "away"]:
        official = pd.to_numeric(
            comparison[f"official_{side}_score"], errors="coerce"
        )
        feed = pd.to_numeric(comparison[f"{side}_score"], errors="coerce")
        mismatch = official.notna() & feed.notna() & official.ne(feed)
        if mismatch.any():
            bad = comparison.loc[
                mismatch,
                [
                    "series_game_number",
                    "game_id",
                    f"official_{side}_score",
                    f"{side}_score",
                ],
            ]
            raise PlayByPlayDataError(
                "Final play-by-play score does not match the games table:\n"
                f"{bad.to_string(index=False)}"
            )


def build_quarter_summary(
    play_by_play: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    """Build quarter scoring and event counts using scoreboard differences."""

    rows: list[dict[str, object]] = []
    context_by_game = context.set_index("game_id")

    for game_id, game_events in play_by_play.groupby("game_id", sort=False):
        game_events = game_events.sort_values(["period", "event_number"])
        game_context = context_by_game.loc[game_id]
        previous_home_score = 0
        previous_away_score = 0

        for period, period_events in game_events.groupby("period", sort=True):
            final_event = period_events.iloc[-1]
            final_home_score = int(final_event["home_score"])
            final_away_score = int(final_event["away_score"])

            period_points = {
                str(game_context["home_team"]): (
                    final_home_score - previous_home_score
                ),
                str(game_context["away_team"]): (
                    final_away_score - previous_away_score
                ),
            }

            for team in [
                str(game_context["home_team"]),
                str(game_context["away_team"]),
            ]:
                team_events = period_events.loc[period_events["team"] == team]
                rows.append(
                    {
                        "series_game_number": int(
                            game_context["series_game_number"]
                        ),
                        "game_id": game_id,
                        "period": int(period),
                        "team": team,
                        "points": int(period_points[team]),
                        "turnovers": int(
                            pd.to_numeric(
                                team_events["is_turnover"], errors="coerce"
                            )
                            .fillna(0)
                            .sum()
                        ),
                        "fouls": int(
                            pd.to_numeric(
                                team_events["is_foul"], errors="coerce"
                            )
                            .fillna(0)
                            .sum()
                        ),
                        "timeouts": int(
                            pd.to_numeric(
                                team_events["is_timeout"], errors="coerce"
                            )
                            .fillna(0)
                            .sum()
                        ),
                        "substitutions": int(
                            pd.to_numeric(
                                team_events["is_substitution"], errors="coerce"
                            )
                            .fillna(0)
                            .sum()
                        ),
                    }
                )

            previous_home_score = final_home_score
            previous_away_score = final_away_score

    result = pd.DataFrame(rows)
    return result.sort_values(
        ["series_game_number", "period", "team"]
    ).reset_index(drop=True)


def build_scoring_events(
    play_by_play: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    """Convert cumulative score changes into one row per scoring event."""

    rows: list[dict[str, object]] = []
    context_by_game = context.set_index("game_id")

    for game_id, game_events in play_by_play.groupby("game_id", sort=False):
        game_events = game_events.sort_values(["period", "event_number"]).copy()
        game_context = context_by_game.loc[game_id]

        previous_home = game_events["home_score"].shift(1, fill_value=0)
        previous_away = game_events["away_score"].shift(1, fill_value=0)
        game_events["home_points_added"] = game_events["home_score"] - previous_home
        game_events["away_points_added"] = game_events["away_score"] - previous_away

        invalid = game_events.loc[
            (game_events["home_points_added"] < 0)
            | (game_events["away_points_added"] < 0)
            | (game_events["home_points_added"] > 4)
            | (game_events["away_points_added"] > 4)
            | (
                (game_events["home_points_added"] > 0)
                & (game_events["away_points_added"] > 0)
            )
        ]
        if not invalid.empty:
            raise PlayByPlayDataError(
                "Invalid score change found while rebuilding scoring runs:\n"
                f"{invalid.head(10).to_string(index=False)}"
            )

        for row in game_events.itertuples(index=False):
            home_added = int(row.home_points_added)
            away_added = int(row.away_points_added)
            if home_added == 0 and away_added == 0:
                continue

            if home_added > 0:
                team = str(game_context["home_team"])
                opponent = str(game_context["away_team"])
                points = home_added
                team_before = int(row.home_score) - points
                opponent_before = int(row.away_score)
                team_after = int(row.home_score)
                opponent_after = int(row.away_score)
            else:
                team = str(game_context["away_team"])
                opponent = str(game_context["home_team"])
                points = away_added
                team_before = int(row.away_score) - points
                opponent_before = int(row.home_score)
                team_after = int(row.away_score)
                opponent_after = int(row.home_score)

            rows.append(
                {
                    "series_game_number": int(
                        game_context["series_game_number"]
                    ),
                    "game_id": game_id,
                    "period": int(row.period),
                    "game_clock": row.game_clock,
                    "event_number": int(row.event_number),
                    "team": team,
                    "opponent": opponent,
                    "points_added": points,
                    "team_score_before": team_before,
                    "opponent_score_before": opponent_before,
                    "team_score_after": team_after,
                    "opponent_score_after": opponent_after,
                    "margin_before": team_before - opponent_before,
                    "margin_after": team_after - opponent_after,
                }
            )

    return pd.DataFrame(rows)


def build_scoring_runs(
    scoring_events: pd.DataFrame,
) -> pd.DataFrame:
    """Group uninterrupted scoring events by the same team."""

    run_rows: list[dict[str, object]] = []

    for game_id, game_events in scoring_events.groupby("game_id", sort=False):
        game_events = game_events.sort_values(["period", "event_number"]).copy()
        game_events["new_run"] = game_events["team"].ne(
            game_events["team"].shift(1)
        )
        game_events["run_group"] = game_events["new_run"].cumsum()

        for _, run in game_events.groupby("run_group", sort=False):
            run_points = int(run["points_added"].sum())
            if run_points < MIN_SCORING_RUN_POINTS:
                continue

            first = run.iloc[0]
            last = run.iloc[-1]
            run_rows.append(
                {
                    "series_game_number": int(first["series_game_number"]),
                    "game_id": game_id,
                    "team": first["team"],
                    "opponent": first["opponent"],
                    "start_period": int(first["period"]),
                    "start_clock": first["game_clock"],
                    "end_period": int(last["period"]),
                    "end_clock": last["game_clock"],
                    "start_event": int(first["event_number"]),
                    "end_event": int(last["event_number"]),
                    "run_points": run_points,
                    "opponent_points": 0,
                    "scoring_plays": int(len(run)),
                    "team_score_before": int(first["team_score_before"]),
                    "opponent_score_before": int(
                        first["opponent_score_before"]
                    ),
                    "team_score_after": int(last["team_score_after"]),
                    "opponent_score_after": int(last["opponent_score_after"]),
                    "margin_before": int(first["margin_before"]),
                    "margin_after": int(last["margin_after"]),
                    "margin_swing": int(
                        last["margin_after"] - first["margin_before"]
                    ),
                    "run_label": f"{run_points}-0",
                }
            )

    result = pd.DataFrame(run_rows)
    if result.empty:
        return pd.DataFrame(
            columns=[
                "series_game_number",
                "game_id",
                "team",
                "opponent",
                "start_period",
                "start_clock",
                "end_period",
                "end_clock",
                "start_event",
                "end_event",
                "run_points",
                "opponent_points",
                "scoring_plays",
                "team_score_before",
                "opponent_score_before",
                "team_score_after",
                "opponent_score_after",
                "margin_before",
                "margin_after",
                "margin_swing",
                "run_label",
            ]
        )

    return result.sort_values(
        ["series_game_number", "start_period", "start_event"]
    ).reset_index(drop=True)


def build_rotation_events(
    play_by_play: pd.DataFrame,
    context: pd.DataFrame,
) -> pd.DataFrame:
    """Create a score-aware substitution and timeout event table."""

    context_by_game = context.set_index("game_id")
    rows: list[dict[str, object]] = []

    selected = play_by_play.loc[
        pd.to_numeric(play_by_play["is_substitution"], errors="coerce")
        .fillna(0)
        .eq(1)
        | pd.to_numeric(play_by_play["is_timeout"], errors="coerce")
        .fillna(0)
        .eq(1)
    ]

    for row in selected.itertuples(index=False):
        game_context = context_by_game.loc[row.game_id]
        team = row.team

        if team == game_context["home_team"]:
            team_score = int(row.home_score)
            opponent_score = int(row.away_score)
        elif team == game_context["away_team"]:
            team_score = int(row.away_score)
            opponent_score = int(row.home_score)
        else:
            team_score = None
            opponent_score = None

        rows.append(
            {
                "series_game_number": int(row.series_game_number),
                "game_id": row.game_id,
                "period": int(row.period),
                "game_clock": row.game_clock,
                "seconds_remaining": row.seconds_remaining,
                "event_number": int(row.event_number),
                "team": team,
                "event_type": row.event_type,
                "action_type": row.action_type,
                "event_description": row.event_description,
                "home_team": game_context["home_team"],
                "away_team": game_context["away_team"],
                "home_score": int(row.home_score),
                "away_score": int(row.away_score),
                "team_score": team_score,
                "opponent_score": opponent_score,
                "team_margin": (
                    None
                    if team_score is None
                    else int(team_score - opponent_score)
                ),
            }
        )

    return pd.DataFrame(rows).sort_values(
        ["series_game_number", "period", "event_number"]
    ).reset_index(drop=True)


def export_dataframe(dataframe: pd.DataFrame, file_name: str) -> None:
    """Write one output and print its row count."""

    output_path = ANALYSIS_OUTPUT_DIR / file_name
    dataframe.to_csv(output_path, index=False)
    print(f"{file_name}: {len(dataframe)} rows saved to {output_path}")


def export_analysis_outputs() -> None:
    """Rebuild and export every pregame analysis output."""

    ANALYSIS_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sqlite3.connect(DATABASE_PATH) as connection:
        connection.execute("PRAGMA foreign_keys = ON;")

        normalized_rows = normalize_player_turnover_percentages(connection)
        print(
            "Player turnover-percentage rows normalized: "
            f"{normalized_rows}"
        )

        for sql_file_name, output_file_name in SQL_OUTPUTS.items():
            query = read_sql_file(sql_file_name)
            dataframe = pd.read_sql_query(query, connection)
            if "game_id" in dataframe.columns:
                dataframe["game_id"] = dataframe["game_id"].astype("string")
            export_dataframe(dataframe, output_file_name)

        context = load_finals_context(connection)
        play_by_play = load_finals_play_by_play(connection)

    play_by_play = add_filled_scores(play_by_play)
    play_by_play = add_event_team_labels(play_by_play, context)
    validate_final_scores(play_by_play, context)

    quarter_summary = build_quarter_summary(play_by_play, context)
    scoring_events = build_scoring_events(play_by_play, context)
    scoring_runs = build_scoring_runs(scoring_events)
    rotation_events = build_rotation_events(play_by_play, context)

    export_dataframe(quarter_summary, "finals_quarter_summary.csv")
    export_dataframe(scoring_runs, "finals_scoring_runs.csv")
    export_dataframe(rotation_events, "finals_rotation_events.csv")

    print("Analysis outputs exported successfully.")


if __name__ == "__main__":
    export_analysis_outputs()
