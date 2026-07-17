SELECT
    g.series_game_number,
    pbp.game_id,
    pbp.period,
    t.abbreviation AS team,
    SUM(COALESCE(pbp.points_scored, 0)) AS points,
    SUM(pbp.is_turnover) AS turnovers,
    SUM(pbp.is_foul) AS fouls,
    SUM(pbp.is_timeout) AS timeouts,
    SUM(pbp.is_substitution) AS substitutions
FROM play_by_play AS pbp
JOIN pregame_games AS g
    ON pbp.game_id = g.game_id
LEFT JOIN teams AS t
    ON pbp.team_id = t.team_id
WHERE g.series_game_number BETWEEN 1 AND 4
  AND pbp.team_id IS NOT NULL
GROUP BY
    g.series_game_number,
    pbp.game_id,
    pbp.period,
    t.abbreviation
ORDER BY
    g.series_game_number,
    pbp.period,
    t.abbreviation;
