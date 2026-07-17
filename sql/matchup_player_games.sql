SELECT
    g.game_date,
    CASE
        WHEN g.season_type = 'NBA Cup Final' THEN 'NBA Cup Final'
        WHEN g.series_game_number BETWEEN 1 AND 4 THEN 'Finals Games 1-4'
        ELSE 'Regular Season H2H'
    END AS matchup_sample,
    g.series_game_number,
    t.abbreviation AS team,
    p.full_name AS player,
    pgs.starter,
    ROUND(pgs.minutes, 1) AS minutes,
    pgs.points,
    pgs.rebounds,
    pgs.assists,
    pgs.turnovers,
    pgs.fga,
    pgs.fg3a,
    pgs.fta,
    ROUND(100.0 * pgs.true_shooting_pct, 1) AS true_shooting_pct,
    ROUND(100.0 * pgs.usage_pct, 1) AS usage_pct,
    ROUND(pgs.plus_minus, 1) AS plus_minus
FROM pregame_games AS g
JOIN player_game_stats AS pgs
    ON g.game_id = pgs.game_id
JOIN players AS p
    ON pgs.player_id = p.player_id
JOIN teams AS t
    ON pgs.team_id = t.team_id
WHERE g.season_type = 'NBA Cup Final'
   OR g.series_game_number BETWEEN 1 AND 4
   OR (
        g.season_type = 'Regular Season'
        AND g.game_id IN ('0022500467', '0022500868')
   )
ORDER BY g.game_date, t.abbreviation, pgs.minutes DESC;
