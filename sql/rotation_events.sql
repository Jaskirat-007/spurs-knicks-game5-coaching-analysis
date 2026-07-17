SELECT
    g.series_game_number,
    pbp.game_id,
    pbp.period,
    pbp.game_clock,
    pbp.event_number,
    t.abbreviation AS team,
    pbp.event_type,
    pbp.action_type,
    pbp.event_description,
    pbp.home_score,
    pbp.away_score,
    pbp.score_margin
FROM play_by_play AS pbp
JOIN pregame_games AS g
    ON pbp.game_id = g.game_id
LEFT JOIN teams AS t
    ON pbp.team_id = t.team_id
WHERE g.series_game_number BETWEEN 1 AND 4
  AND (
        pbp.is_substitution = 1
        OR pbp.is_timeout = 1
      )
ORDER BY
    g.series_game_number,
    pbp.event_number;
