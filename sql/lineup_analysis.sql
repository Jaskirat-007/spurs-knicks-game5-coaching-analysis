SELECT
    la.sample_name,
    t.abbreviation AS team,
    la.group_name AS lineup,
    la.games_played,
    ROUND(la.minutes, 1) AS minutes,
    ROUND(la.possessions, 1) AS possessions,
    ROUND(la.ortg, 1) AS ortg,
    ROUND(la.drtg, 1) AS drtg,
    ROUND(la.net_rating, 1) AS net_rating,
    ROUND(100.0 * la.efg_pct, 1) AS efg_pct,
    ROUND(100.0 * la.tov_pct, 1) AS tov_pct,
    ROUND(100.0 * la.oreb_pct, 1) AS oreb_pct,
    ROUND(la.plus_minus, 1) AS plus_minus
FROM lineup_aggregates AS la
JOIN teams AS t
    ON la.team_id = t.team_id
WHERE la.is_pregame = 1
  AND la.minutes >= CASE
        WHEN la.sample_name = 'Finals Games 1-4' THEN 5
        ELSE 20
      END
ORDER BY
    CASE la.sample_name
        WHEN 'Full Regular Season' THEN 1
        WHEN 'Playoffs Before Finals' THEN 2
        WHEN 'Finals Games 1-4' THEN 3
        WHEN 'Last 10 Before Game 5' THEN 4
    END,
    t.abbreviation,
    la.minutes DESC;
