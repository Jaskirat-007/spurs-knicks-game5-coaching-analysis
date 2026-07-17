WITH scoring_events AS (
    SELECT
        g.series_game_number,
        pbp.game_id,
        pbp.event_number,
        pbp.period,
        pbp.game_clock,
        pbp.team_id,
        pbp.points_scored,
        LAG(pbp.team_id) OVER (
            PARTITION BY pbp.game_id
            ORDER BY pbp.event_number
        ) AS previous_scoring_team
    FROM play_by_play AS pbp
    JOIN pregame_games AS g
        ON pbp.game_id = g.game_id
    WHERE g.series_game_number BETWEEN 1 AND 4
      AND pbp.team_id IS NOT NULL
      AND COALESCE(pbp.points_scored, 0) > 0
),
run_groups AS (
    SELECT
        *,
        SUM(
            CASE
                WHEN previous_scoring_team IS NULL
                  OR previous_scoring_team <> team_id
                THEN 1
                ELSE 0
            END
        ) OVER (
            PARTITION BY game_id
            ORDER BY event_number
        ) AS run_group
    FROM scoring_events
)
SELECT
    rg.series_game_number,
    rg.game_id,
    t.abbreviation AS team,
    MIN(rg.period) AS start_period,
    MIN(rg.event_number) AS start_event,
    MAX(rg.event_number) AS end_event,
    SUM(rg.points_scored) AS run_points,
    COUNT(*) AS scoring_plays
FROM run_groups AS rg
JOIN teams AS t
    ON rg.team_id = t.team_id
GROUP BY
    rg.series_game_number,
    rg.game_id,
    rg.team_id,
    rg.run_group
HAVING SUM(rg.points_scored) >= 6
ORDER BY
    rg.series_game_number,
    start_event;
