WITH pregame_team_games AS (
    SELECT
        g.game_id,
        g.game_date,
        g.season_type,
        g.series_game_number,
        tgs.team_id,
        t.abbreviation AS team_abbreviation,
        tgs.possessions,
        tgs.ortg,
        tgs.drtg,
        tgs.net_rating,
        tgs.pace,
        tgs.fgm,
        tgs.fga,
        tgs.fg3m,
        tgs.fg3a,
        tgs.fta,
        tgs.turnovers,
        tgs.oreb_pct
    FROM pregame_games AS g
    JOIN team_game_stats AS tgs
        ON g.game_id = tgs.game_id
    JOIN teams AS t
        ON tgs.team_id = t.team_id
    WHERE t.abbreviation IN ('SAS', 'NYK')
),
ranked_pregame_games AS (
    SELECT
        *,
        ROW_NUMBER() OVER (
            PARTITION BY team_id
            ORDER BY game_date DESC, game_id DESC
        ) AS recent_game_number
    FROM pregame_team_games
),
comparison_samples AS (
    SELECT 'Full Regular Season' AS sample_name, *
    FROM ranked_pregame_games
    WHERE season_type = 'Regular Season'

    UNION ALL

    SELECT 'Playoffs Before Finals' AS sample_name, *
    FROM ranked_pregame_games
    WHERE season_type = 'Playoffs'
      AND series_game_number IS NULL

    UNION ALL

    SELECT 'Finals Games 1-4' AS sample_name, *
    FROM ranked_pregame_games
    WHERE series_game_number BETWEEN 1 AND 4

    UNION ALL

    SELECT 'Last 10 Before Game 5' AS sample_name, *
    FROM ranked_pregame_games
    WHERE recent_game_number <= 10
)
SELECT
    sample_name,
    team_abbreviation,
    COUNT(*) AS games,
    ROUND(SUM(ortg * possessions) / SUM(possessions), 1) AS ortg,
    ROUND(SUM(drtg * possessions) / SUM(possessions), 1) AS drtg,
    ROUND(SUM(net_rating * possessions) / SUM(possessions), 1) AS net_rating,
    ROUND(AVG(pace), 1) AS pace,
    ROUND(100.0 * SUM(fgm + 0.5 * fg3m) / SUM(fga), 1) AS efg_pct,
    ROUND(100.0 * SUM(turnovers) / SUM(possessions), 1) AS tov_pct,
    ROUND(100.0 * AVG(oreb_pct), 1) AS oreb_pct,
    ROUND(100.0 * SUM(fta) / SUM(fga), 1) AS fta_rate,
    ROUND(100.0 * SUM(fg3a) / SUM(fga), 1) AS three_pa_rate
FROM comparison_samples
GROUP BY sample_name, team_abbreviation
ORDER BY
    CASE sample_name
        WHEN 'Full Regular Season' THEN 1
        WHEN 'Playoffs Before Finals' THEN 2
        WHEN 'Finals Games 1-4' THEN 3
        WHEN 'Last 10 Before Game 5' THEN 4
    END,
    team_abbreviation;
