SELECT
    g.series_game_number,
    g.game_id,
    g.game_date,
    t.abbreviation AS team,
    tgs.points,
    ROUND(tgs.ortg, 1) AS ortg,
    ROUND(tgs.drtg, 1) AS drtg,
    ROUND(tgs.net_rating, 1) AS net_rating,
    ROUND(tgs.pace, 1) AS pace,
    ROUND(100.0 * tgs.efg_pct, 1) AS efg_pct,
    ROUND(100.0 * tgs.tov_pct, 1) AS tov_pct,
    ROUND(100.0 * tgs.oreb_pct, 1) AS oreb_pct,
    ROUND(100.0 * tgs.fta_rate, 1) AS fta_rate,
    ROUND(100.0 * tgs.three_pa_rate, 1) AS three_pa_rate
FROM games AS g
JOIN team_game_stats AS tgs
    ON g.game_id = tgs.game_id
JOIN teams AS t
    ON tgs.team_id = t.team_id
WHERE g.series_game_number BETWEEN 1 AND 4
ORDER BY g.series_game_number, t.abbreviation;
