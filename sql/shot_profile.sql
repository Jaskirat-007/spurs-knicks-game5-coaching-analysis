WITH classified_shots AS (
    SELECT
        s.*,
        g.season_type,
        g.series_game_number,
        t.abbreviation AS team,
        CASE
            WHEN s.shot_zone IN (
                'Above the Break 3',
                'Corner 3',
                'Three-Point'
            ) THEN 'Three-Point'
            WHEN s.shot_zone = 'Rim' THEN 'Rim'
            WHEN s.shot_zone = 'Short Midrange' THEN 'Short Midrange'
            WHEN s.shot_zone = 'Long Midrange' THEN 'Long Midrange'
            ELSE COALESCE(s.shot_zone, 'Other')
        END AS harmonized_shot_zone,
        CASE
            WHEN g.season_type = 'NBA Cup Final' THEN 'NBA Cup Final'
            WHEN g.series_game_number BETWEEN 1 AND 4 THEN 'Finals Games 1-4'
            WHEN g.game_id IN ('0022500467', '0022500868')
                THEN 'Regular Season H2H'
            ELSE NULL
        END AS specific_sample
    FROM shots AS s
    JOIN pregame_games AS g
        ON s.game_id = g.game_id
    JOIN teams AS t
        ON s.team_id = t.team_id
),
samples AS (
    SELECT specific_sample AS sample_name, *
    FROM classified_shots
    WHERE specific_sample IS NOT NULL

    UNION ALL

    SELECT 'All Pregame Matchups' AS sample_name, *
    FROM classified_shots
    WHERE specific_sample IS NOT NULL
)
SELECT
    sample_name,
    team,
    harmonized_shot_zone AS shot_zone,
    COUNT(*) AS attempts,
    SUM(shot_made) AS makes,
    ROUND(100.0 * SUM(shot_made) / COUNT(*), 1) AS fg_pct,
    ROUND(
        100.0 * COUNT(*)
        / SUM(COUNT(*)) OVER (PARTITION BY sample_name, team),
        1
    ) AS attempt_frequency_pct,
    ROUND(AVG(shot_distance), 1) AS average_distance
FROM samples
GROUP BY
    sample_name,
    team,
    harmonized_shot_zone
ORDER BY
    CASE sample_name
        WHEN 'Regular Season H2H' THEN 1
        WHEN 'NBA Cup Final' THEN 2
        WHEN 'Finals Games 1-4' THEN 3
        WHEN 'All Pregame Matchups' THEN 4
    END,
    team,
    CASE harmonized_shot_zone
        WHEN 'Rim' THEN 1
        WHEN 'Short Midrange' THEN 2
        WHEN 'Long Midrange' THEN 3
        WHEN 'Three-Point' THEN 4
        ELSE 5
    END;
