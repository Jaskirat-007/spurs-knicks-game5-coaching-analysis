"""Interactive pregame review dashboard for Spurs-Knicks Games 1-4.

This application intentionally reads only pregame analysis outputs. Game 5 is
not loaded anywhere in the dashboard, which protects the holdout design.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config import ANALYSIS_OUTPUT_DIR


SAMPLE_ORDER = [
    "Full Regular Season",
    "Playoffs Before Finals",
    "Finals Games 1-4",
    "Last 10 Before Game 5",
]
MATCHUP_SAMPLE_ORDER = [
    "Regular Season H2H",
    "NBA Cup Final",
    "Finals Games 1-4",
    "All Pregame Matchups",
]
TEAM_ORDER = ["SAS", "NYK"]

FILE_MAP = {
    "team_windows": "team_comparison_windows.csv",
    "finals_team": "finals_games_1_4_team_stats.csv",
    "player_windows": "player_comparison_windows.csv",
    "matchup_players": "pregame_matchup_player_games.csv",
    "shots": "pregame_shot_profiles.csv",
    "lineups": "pregame_lineup_analysis.csv",
    "quarters": "finals_quarter_summary.csv",
    "runs": "finals_scoring_runs.csv",
    "rotations": "finals_rotation_events.csv",
}


st.set_page_config(
    page_title="Spurs-Knicks Pregame Review",
    layout="wide",
)


@st.cache_data

def load_csv(file_name: str) -> pd.DataFrame:
    """Load one analysis output and preserve game IDs."""

    path = ANALYSIS_OUTPUT_DIR / file_name
    if not path.exists():
        raise FileNotFoundError(
            f"Missing {path}. Run python run_review_build.py first."
        )

    dataframe = pd.read_csv(path, dtype={"game_id": "string"})
    if "game_id" in dataframe.columns:
        dataframe["game_id"] = dataframe["game_id"].str.zfill(10)
    return dataframe


@st.cache_data

def load_all_outputs() -> dict[str, pd.DataFrame]:
    """Load all pregame files used by the dashboard."""

    return {key: load_csv(name) for key, name in FILE_MAP.items()}


def sample_quality(possessions: float) -> str:
    """Assign a transparent lineup sample-size warning."""

    if possessions >= 100:
        return "Strong sample"
    if possessions >= 50:
        return "Moderate sample"
    if possessions >= 25:
        return "Small sample"
    return "Very small sample"


def format_game_label(game_number: int) -> str:
    """Return a readable Finals game label."""

    return f"Game {int(game_number)}"


def team_metric_chart(
    dataframe: pd.DataFrame,
    metric: str,
    title: str,
):
    """Build a grouped bar chart for one team metric."""

    chart_data = dataframe.copy()
    chart_data["sample_name"] = pd.Categorical(
        chart_data["sample_name"],
        categories=SAMPLE_ORDER,
        ordered=True,
    )
    chart_data = chart_data.sort_values("sample_name")
    return px.bar(
        chart_data,
        x="sample_name",
        y=metric,
        color="team_abbreviation",
        barmode="group",
        labels={
            "sample_name": "Sample",
            metric: metric.replace("_", " ").title(),
            "team_abbreviation": "Team",
        },
        title=title,
    )


def build_notes_markdown(notes: dict[str, str]) -> str:
    """Build a downloadable pregame recommendation document."""

    return f"""# Spurs vs. Knicks Game 5 Pregame Review

Prepared: {date.today().isoformat()}

Data cutoff: Finals Games 1-4. Game 5 remained hidden during preparation.

## Core diagnosis

{notes['diagnosis']}

## Offensive priorities

1. {notes['offense_1']}
2. {notes['offense_2']}
3. {notes['offense_3']}

## Defensive priorities

1. {notes['defense_1']}
2. {notes['defense_2']}
3. {notes['defense_3']}

## Rotation adjustment

{notes['rotation']}

## Live-game triggers

{notes['triggers']}

## Counter-evidence and uncertainty

{notes['counter_evidence']}

## Evidence still needed from film

{notes['film']}
"""


def render_team_identity(data: dict[str, pd.DataFrame]) -> None:
    """Render regular-season, playoff, and Finals team profiles."""

    st.subheader("Team identity across comparison windows")
    st.caption(
        "Use this page to understand how each team normally played and how "
        "Games 1-4 differed."
    )

    team_windows = data["team_windows"].copy()
    metric = st.selectbox(
        "Metric",
        options=[
            "net_rating",
            "ortg",
            "drtg",
            "pace",
            "efg_pct",
            "tov_pct",
            "oreb_pct",
            "fta_rate",
            "three_pa_rate",
        ],
        format_func=lambda value: value.replace("_", " ").upper(),
        key="team_metric",
    )

    st.plotly_chart(
        team_metric_chart(
            team_windows,
            metric,
            f"{metric.replace('_', ' ').title()} by sample",
        ),
        use_container_width=True,
    )

    ordered = team_windows.copy()
    ordered["sample_name"] = pd.Categorical(
        ordered["sample_name"], SAMPLE_ORDER, ordered=True
    )
    ordered = ordered.sort_values(["sample_name", "team_abbreviation"])
    st.dataframe(ordered, hide_index=True, use_container_width=True)


def render_finals_games(data: dict[str, pd.DataFrame]) -> None:
    """Render game-by-game team results for Games 1-4."""

    st.subheader("Finals Games 1-4")
    finals = data["finals_team"].copy()
    finals["game"] = finals["series_game_number"].map(format_game_label)

    metric = st.selectbox(
        "Game-by-game metric",
        options=[
            "net_rating",
            "ortg",
            "drtg",
            "efg_pct",
            "tov_pct",
            "oreb_pct",
            "fta_rate",
            "three_pa_rate",
        ],
        format_func=lambda value: value.replace("_", " ").upper(),
        key="finals_metric",
    )

    figure = px.line(
        finals,
        x="series_game_number",
        y=metric,
        color="team",
        markers=True,
        labels={
            "series_game_number": "Finals game",
            metric: metric.replace("_", " ").title(),
            "team": "Team",
        },
        title=f"{metric.replace('_', ' ').title()} by Finals game",
    )
    figure.update_xaxes(dtick=1)
    st.plotly_chart(figure, use_container_width=True)
    st.dataframe(
        finals.drop(columns=["game"]),
        hide_index=True,
        use_container_width=True,
    )


def render_players(data: dict[str, pd.DataFrame]) -> None:
    """Render player window comparisons and matchup game logs."""

    st.subheader("Player performance")
    player_windows = data["player_windows"].copy()

    controls = st.columns(3)
    with controls[0]:
        sample = st.selectbox(
            "Sample",
            SAMPLE_ORDER,
            index=2,
            key="player_sample",
        )
    with controls[1]:
        team = st.selectbox("Team", TEAM_ORDER, key="player_team")
    with controls[2]:
        minimum_minutes = st.number_input(
            "Minimum total minutes",
            min_value=0.0,
            value=25.0,
            step=5.0,
        )

    filtered = player_windows.loc[
        player_windows["sample_name"].eq(sample)
        & player_windows["team"].eq(team)
        & pd.to_numeric(
            player_windows["total_minutes"], errors="coerce"
        ).ge(minimum_minutes)
    ].copy()

    if filtered.empty:
        st.info("No players match the selected filters.")
    else:
        figure = px.scatter(
            filtered,
            x="usage_pct",
            y="true_shooting_pct",
            size="total_minutes",
            hover_name="player",
            text="player",
            labels={
                "usage_pct": "Usage percentage",
                "true_shooting_pct": "True shooting percentage",
                "total_minutes": "Minutes",
            },
            title=f"{team}: usage and scoring efficiency",
        )
        figure.update_traces(textposition="top center")
        st.plotly_chart(figure, use_container_width=True)
        st.dataframe(
            filtered.sort_values("total_minutes", ascending=False),
            hide_index=True,
            use_container_width=True,
        )

    with st.expander("Pregame matchup player game logs"):
        matchup = data["matchup_players"].copy()
        selected_samples = st.multiselect(
            "Matchup samples",
            options=sorted(matchup["matchup_sample"].dropna().unique()),
            default=sorted(matchup["matchup_sample"].dropna().unique()),
        )
        matchup_filtered = matchup.loc[
            matchup["team"].eq(team)
            & matchup["matchup_sample"].isin(selected_samples)
        ]
        st.dataframe(
            matchup_filtered,
            hide_index=True,
            use_container_width=True,
        )


def render_shots(data: dict[str, pd.DataFrame]) -> None:
    """Render harmonized shot-zone frequency and efficiency."""

    st.subheader("Shot profile")
    shots = data["shots"].copy()

    sample = st.selectbox(
        "Shot sample",
        MATCHUP_SAMPLE_ORDER,
        index=2,
        key="shot_sample",
    )
    filtered = shots.loc[shots["sample_name"].eq(sample)].copy()

    frequency = px.bar(
        filtered,
        x="shot_zone",
        y="attempt_frequency_pct",
        color="team",
        barmode="group",
        labels={
            "shot_zone": "Shot zone",
            "attempt_frequency_pct": "Attempt frequency percentage",
            "team": "Team",
        },
        title=f"Shot distribution: {sample}",
    )
    st.plotly_chart(frequency, use_container_width=True)

    efficiency = px.bar(
        filtered,
        x="shot_zone",
        y="fg_pct",
        color="team",
        barmode="group",
        labels={
            "shot_zone": "Shot zone",
            "fg_pct": "Field-goal percentage",
            "team": "Team",
        },
        title=f"Shot efficiency: {sample}",
    )
    st.plotly_chart(efficiency, use_container_width=True)
    st.dataframe(filtered, hide_index=True, use_container_width=True)


def render_lineups(data: dict[str, pd.DataFrame]) -> None:
    """Render lineup results with sample-size warnings."""

    st.subheader("Lineups")
    lineups = data["lineups"].copy()
    lineups["sample_quality"] = pd.to_numeric(
        lineups["possessions"], errors="coerce"
    ).fillna(0).map(sample_quality)

    controls = st.columns(3)
    with controls[0]:
        team = st.selectbox("Lineup team", TEAM_ORDER, key="lineup_team")
    with controls[1]:
        available_samples = sorted(
            lineups.loc[lineups["team"].eq(team), "sample_name"]
            .dropna()
            .unique()
        )
        default_index = (
            available_samples.index("Finals Games 1-4")
            if "Finals Games 1-4" in available_samples
            else 0
        )
        sample = st.selectbox(
            "Lineup sample",
            available_samples,
            index=default_index,
            key="lineup_sample",
        )
    with controls[2]:
        minimum_possessions = st.slider(
            "Minimum possessions",
            min_value=0,
            max_value=200,
            value=25,
            step=5,
        )

    filtered = lineups.loc[
        lineups["team"].eq(team)
        & lineups["sample_name"].eq(sample)
        & pd.to_numeric(lineups["possessions"], errors="coerce").ge(
            minimum_possessions
        )
    ].copy()

    if filtered.empty:
        st.info("No lineups match the selected possession threshold.")
        return

    filtered = filtered.sort_values("net_rating", ascending=False)
    chart_data = filtered.head(15).sort_values("net_rating")
    figure = px.bar(
        chart_data,
        x="net_rating",
        y="lineup",
        orientation="h",
        hover_data=["minutes", "possessions", "ortg", "drtg", "sample_quality"],
        labels={"net_rating": "Net rating", "lineup": "Lineup"},
        title=f"{team} lineup net rating: {sample}",
    )
    st.plotly_chart(figure, use_container_width=True)
    st.caption(
        "Sample warnings are descriptive only: 100+ possessions is strong, "
        "50-99 moderate, 25-49 small, and below 25 very small."
    )
    st.dataframe(filtered, hide_index=True, use_container_width=True)


def render_game_flow(data: dict[str, pd.DataFrame]) -> None:
    """Render quarter results and verified scoring runs."""

    st.subheader("Game flow")
    game_number = st.selectbox(
        "Finals game",
        options=[1, 2, 3, 4],
        format_func=format_game_label,
        key="flow_game",
    )

    quarters = data["quarters"].loc[
        data["quarters"]["series_game_number"].eq(game_number)
    ].copy()
    runs = data["runs"].loc[
        data["runs"]["series_game_number"].eq(game_number)
    ].copy()

    quarter_chart = px.bar(
        quarters,
        x="period",
        y="points",
        color="team",
        barmode="group",
        labels={"period": "Period", "points": "Points", "team": "Team"},
        title=f"Quarter scoring: Game {game_number}",
    )
    quarter_chart.update_xaxes(dtick=1)
    st.plotly_chart(quarter_chart, use_container_width=True)

    left, right = st.columns(2)
    with left:
        st.markdown("#### Quarter summary")
        st.dataframe(quarters, hide_index=True, use_container_width=True)
    with right:
        st.markdown("#### Unanswered scoring runs of at least 6-0")
        if runs.empty:
            st.info("No qualifying uninterrupted runs were found.")
        else:
            st.dataframe(runs, hide_index=True, use_container_width=True)


def render_rotations(data: dict[str, pd.DataFrame]) -> None:
    """Render score-aware substitution and timeout events."""

    st.subheader("Rotation and timeout timeline")
    rotations = data["rotations"].copy()

    controls = st.columns(2)
    with controls[0]:
        game_number = st.selectbox(
            "Rotation game",
            options=[1, 2, 3, 4],
            format_func=format_game_label,
            key="rotation_game",
        )
    with controls[1]:
        selected_teams = st.multiselect(
            "Rotation teams",
            options=TEAM_ORDER,
            default=TEAM_ORDER,
        )

    filtered = rotations.loc[
        rotations["series_game_number"].eq(game_number)
        & rotations["team"].isin(selected_teams)
    ].copy()

    display_columns = [
        "period",
        "game_clock",
        "team",
        "event_type",
        "event_description",
        "team_score",
        "opponent_score",
        "team_margin",
    ]
    st.dataframe(
        filtered[display_columns],
        hide_index=True,
        use_container_width=True,
        height=650,
    )


def render_notes() -> None:
    """Render the user-owned basketball interpretation workspace."""

    st.subheader("Observation and recommendation workspace")
    st.caption(
        "Write only after reviewing the evidence tabs. Game 5 remains hidden."
    )

    diagnosis = st.text_area(
        "Core diagnosis: why was New York ahead after four games?",
        height=140,
        key="notes_diagnosis",
    )

    st.markdown("#### Offensive priorities")
    offense_1 = st.text_area("Offensive priority 1", key="notes_offense_1")
    offense_2 = st.text_area("Offensive priority 2", key="notes_offense_2")
    offense_3 = st.text_area("Offensive priority 3", key="notes_offense_3")

    st.markdown("#### Defensive priorities")
    defense_1 = st.text_area("Defensive priority 1", key="notes_defense_1")
    defense_2 = st.text_area("Defensive priority 2", key="notes_defense_2")
    defense_3 = st.text_area("Defensive priority 3", key="notes_defense_3")

    rotation = st.text_area(
        "Rotation adjustment",
        height=100,
        key="notes_rotation",
    )
    triggers = st.text_area(
        "Live-game triggers and thresholds",
        height=120,
        key="notes_triggers",
    )
    counter_evidence = st.text_area(
        "Counter-evidence, uncertainty, and alternative explanations",
        height=120,
        key="notes_counter",
    )
    film = st.text_area(
        "Questions that still require film review",
        height=120,
        key="notes_film",
    )

    notes = {
        "diagnosis": diagnosis,
        "offense_1": offense_1,
        "offense_2": offense_2,
        "offense_3": offense_3,
        "defense_1": defense_1,
        "defense_2": defense_2,
        "defense_3": defense_3,
        "rotation": rotation,
        "triggers": triggers,
        "counter_evidence": counter_evidence,
        "film": film,
    }
    markdown = build_notes_markdown(notes)

    st.download_button(
        "Download frozen pregame notes",
        data=markdown,
        file_name="spurs_knicks_game5_pregame_notes.md",
        mime="text/markdown",
    )


try:
    outputs = load_all_outputs()
except (FileNotFoundError, ValueError) as error:
    st.error(str(error))
    st.stop()

st.title("Spurs vs. Knicks Game 5 Pregame Review")
st.warning(
    "Pregame mode: only data available through Finals Game 4 is loaded. "
    "Game 5 is intentionally excluded."
)

st.sidebar.header("Review sequence")
st.sidebar.markdown(
    """
1. Team identity
2. Games 1-4
3. Players
4. Shot profile
5. Lineups
6. Game flow
7. Rotations
8. Notes and recommendations
"""
)
st.sidebar.caption(
    "The dashboard presents evidence. Basketball interpretation remains yours."
)

(
    team_tab,
    finals_tab,
    player_tab,
    shot_tab,
    lineup_tab,
    flow_tab,
    rotation_tab,
    notes_tab,
) = st.tabs(
    [
        "Team Identity",
        "Games 1-4",
        "Players",
        "Shot Profile",
        "Lineups",
        "Game Flow",
        "Rotations",
        "Notes",
    ]
)

with team_tab:
    render_team_identity(outputs)
with finals_tab:
    render_finals_games(outputs)
with player_tab:
    render_players(outputs)
with shot_tab:
    render_shots(outputs)
with lineup_tab:
    render_lineups(outputs)
with flow_tab:
    render_game_flow(outputs)
with rotation_tab:
    render_rotations(outputs)
with notes_tab:
    render_notes()
