WITH team_games AS (
    SELECT
        g.game_id,
        g.game_date,
        g.season_type,
        g.series_game_number,
        tgs.team_id,
        ROW_NUMBER() OVER (
            PARTITION BY tgs.team_id
            ORDER BY g.game_date DESC, g.game_id DESC
        ) AS recent_game_number
    FROM pregame_games AS g
    JOIN team_game_stats AS tgs
        ON g.game_id = tgs.game_id
    WHERE tgs.team_id IN (1610612759, 1610612752)
),
samples AS (
    SELECT 'Full Regular Season' AS sample_name, *
    FROM team_games
    WHERE season_type = 'Regular Season'

    UNION ALL

    SELECT 'Playoffs Before Finals' AS sample_name, *
    FROM team_games
    WHERE season_type = 'Playoffs'
      AND series_game_number IS NULL

    UNION ALL

    SELECT 'Finals Games 1-4' AS sample_name, *
    FROM team_games
    WHERE series_game_number BETWEEN 1 AND 4

    UNION ALL

    SELECT 'Last 10 Before Game 5' AS sample_name, *
    FROM team_games
    WHERE recent_game_number <= 10
),
player_sample_games AS (
    SELECT
        s.sample_name,
        s.team_id,
        pgs.player_id,
        pgs.minutes,
        pgs.points,
        pgs.fgm,
        pgs.fga,
        pgs.fg3m,
        pgs.fg3a,
        pgs.ftm,
        pgs.fta,
        pgs.rebounds,
        pgs.assists,
        pgs.turnovers,
        pgs.plus_minus,
        pgs.usage_pct,
        pgs.assist_pct,
        pgs.turnover_pct
    FROM samples AS s
    JOIN player_game_stats AS pgs
        ON s.game_id = pgs.game_id
       AND s.team_id = pgs.team_id
    WHERE COALESCE(pgs.minutes, 0) > 0
)
SELECT
    psg.sample_name,
    t.abbreviation AS team,
    p.full_name AS player,
    COUNT(*) AS games,
    ROUND(SUM(psg.minutes), 1) AS total_minutes,
    ROUND(AVG(psg.minutes), 1) AS minutes_per_game,
    ROUND(AVG(psg.points), 1) AS points_per_game,
    ROUND(AVG(psg.rebounds), 1) AS rebounds_per_game,
    ROUND(AVG(psg.assists), 1) AS assists_per_game,
    ROUND(AVG(psg.turnovers), 1) AS turnovers_per_game,
    ROUND(100.0 * SUM(psg.fgm) / NULLIF(SUM(psg.fga), 0), 1) AS fg_pct,
    ROUND(100.0 * SUM(psg.fg3m) / NULLIF(SUM(psg.fg3a), 0), 1) AS three_pct,
    ROUND(
        100.0 * SUM(psg.points)
        / NULLIF(2.0 * (SUM(psg.fga) + 0.44 * SUM(psg.fta)), 0),
        1
    ) AS true_shooting_pct,
    ROUND(
        100.0 * SUM(psg.usage_pct * psg.minutes)
        / NULLIF(SUM(psg.minutes), 0),
        1
    ) AS usage_pct,
    ROUND(
        100.0 * SUM(psg.assist_pct * psg.minutes)
        / NULLIF(SUM(psg.minutes), 0),
        1
    ) AS assist_pct,
    ROUND(
        100.0 * SUM(psg.turnover_pct * psg.minutes)
        / NULLIF(SUM(psg.minutes), 0),
        1
    ) AS turnover_pct,
    ROUND(AVG(psg.plus_minus), 1) AS average_plus_minus
FROM player_sample_games AS psg
JOIN players AS p
    ON psg.player_id = p.player_id
JOIN teams AS t
    ON psg.team_id = t.team_id
GROUP BY
    psg.sample_name,
    t.abbreviation,
    p.full_name
HAVING SUM(psg.minutes) >= 25
ORDER BY
    CASE psg.sample_name
        WHEN 'Full Regular Season' THEN 1
        WHEN 'Playoffs Before Finals' THEN 2
        WHEN 'Finals Games 1-4' THEN 3
        WHEN 'Last 10 Before Game 5' THEN 4
    END,
    t.abbreviation,
    total_minutes DESC;
