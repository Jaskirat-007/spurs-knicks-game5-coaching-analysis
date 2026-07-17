PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS teams (
    team_id INTEGER PRIMARY KEY,
    team_name TEXT NOT NULL,
    abbreviation TEXT NOT NULL UNIQUE
        CHECK (length(abbreviation) BETWEEN 2 AND 3)
);

CREATE TABLE IF NOT EXISTS players (
    player_id INTEGER PRIMARY KEY,
    full_name TEXT NOT NULL,
    current_team_id INTEGER,
    position TEXT,

    FOREIGN KEY (current_team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS games (
    game_id TEXT PRIMARY KEY,
    game_date TEXT NOT NULL,
    season TEXT NOT NULL,
    season_type TEXT NOT NULL,
    series_game_number INTEGER
        CHECK (
            series_game_number IS NULL
            OR series_game_number >= 1
        ),
    home_team_id INTEGER NOT NULL,
    away_team_id INTEGER NOT NULL,
    home_score INTEGER
        CHECK (
            home_score IS NULL
            OR home_score >= 0
        ),
    away_score INTEGER
        CHECK (
            away_score IS NULL
            OR away_score >= 0
        ),
    is_pregame INTEGER NOT NULL DEFAULT 1
        CHECK (is_pregame IN (0, 1)),
    is_holdout INTEGER NOT NULL DEFAULT 0
        CHECK (is_holdout IN (0, 1)),
    source TEXT,
    data_retrieval_date TEXT,

    CHECK (home_team_id <> away_team_id),
    CHECK (is_pregame + is_holdout <= 1),

    FOREIGN KEY (home_team_id)
        REFERENCES teams(team_id),
    FOREIGN KEY (away_team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS team_game_stats (
    game_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    opponent_team_id INTEGER NOT NULL,
    is_home INTEGER NOT NULL
        CHECK (is_home IN (0, 1)),
    minutes REAL,
    points INTEGER,
    possessions REAL,
    poss_est REAL,
    ortg REAL,
    drtg REAL,
    net_rating REAL,
    pace REAL,
    fgm INTEGER,
    fga INTEGER,
    fg3m INTEGER,
    fg3a INTEGER,
    ftm INTEGER,
    fta INTEGER,
    oreb INTEGER,
    dreb INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    plus_minus REAL,
    efg_pct REAL,
    tov_pct REAL,
    oreb_pct REAL,
    dreb_pct REAL,
    reb_pct REAL,
    true_shooting_pct REAL,
    fta_rate REAL,
    three_pa_rate REAL,

    PRIMARY KEY (game_id, team_id),
    CHECK (team_id <> opponent_team_id),

    FOREIGN KEY (game_id)
        REFERENCES games(game_id),
    FOREIGN KEY (team_id)
        REFERENCES teams(team_id),
    FOREIGN KEY (opponent_team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS player_game_stats (
    game_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,
    team_id INTEGER NOT NULL,
    starter INTEGER
        CHECK (
            starter IS NULL
            OR starter IN (0, 1)
        ),
    minutes REAL,
    points INTEGER,
    fgm INTEGER,
    fga INTEGER,
    fg3m INTEGER,
    fg3a INTEGER,
    ftm INTEGER,
    fta INTEGER,
    oreb INTEGER,
    dreb INTEGER,
    rebounds INTEGER,
    assists INTEGER,
    steals INTEGER,
    blocks INTEGER,
    turnovers INTEGER,
    personal_fouls INTEGER,
    plus_minus REAL,
    ortg REAL,
    drtg REAL,
    net_rating REAL,
    usage_pct REAL,
    true_shooting_pct REAL,
    assist_pct REAL,
    turnover_pct REAL,

    PRIMARY KEY (game_id, player_id),

    FOREIGN KEY (game_id)
        REFERENCES games(game_id),
    FOREIGN KEY (player_id)
        REFERENCES players(player_id),
    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS shots (
    shot_id TEXT PRIMARY KEY,
    game_id TEXT NOT NULL,
    event_number INTEGER,
    team_id INTEGER NOT NULL,
    player_id INTEGER NOT NULL,
    period INTEGER NOT NULL
        CHECK (period >= 1),
    game_clock TEXT,
    seconds_remaining INTEGER
        CHECK (
            seconds_remaining IS NULL
            OR seconds_remaining >= 0
        ),
    action_type TEXT,
    shot_type TEXT,
    shot_zone_basic TEXT,
    shot_zone_area TEXT,
    shot_zone_range TEXT,
    shot_zone TEXT,
    shot_distance REAL,
    location_x REAL,
    location_y REAL,
    shot_made INTEGER NOT NULL
        CHECK (shot_made IN (0, 1)),
    assisted INTEGER
        CHECK (
            assisted IS NULL
            OR assisted IN (0, 1)
        ),
    assister_player_id INTEGER,

    FOREIGN KEY (game_id)
        REFERENCES games(game_id),
    FOREIGN KEY (team_id)
        REFERENCES teams(team_id),
    FOREIGN KEY (player_id)
        REFERENCES players(player_id),
    FOREIGN KEY (assister_player_id)
        REFERENCES players(player_id),

    UNIQUE (game_id, event_number, player_id)
);

CREATE TABLE IF NOT EXISTS play_by_play (
    game_id TEXT NOT NULL,
    event_number INTEGER NOT NULL,
    period INTEGER NOT NULL
        CHECK (period >= 1),
    game_clock TEXT,
    seconds_remaining INTEGER
        CHECK (
            seconds_remaining IS NULL
            OR seconds_remaining >= 0
        ),
    event_type TEXT,
    action_type TEXT,
    event_description TEXT,
    team_id INTEGER,
    player1_id INTEGER,
    player2_id INTEGER,
    player3_id INTEGER,
    home_score INTEGER,
    away_score INTEGER,
    score_margin INTEGER,
    points_scored INTEGER,
    is_scoring_play INTEGER
        CHECK (
            is_scoring_play IS NULL
            OR is_scoring_play IN (0, 1)
        ),
    is_turnover INTEGER
        CHECK (
            is_turnover IS NULL
            OR is_turnover IN (0, 1)
        ),
    is_foul INTEGER
        CHECK (
            is_foul IS NULL
            OR is_foul IN (0, 1)
        ),
    is_substitution INTEGER
        CHECK (
            is_substitution IS NULL
            OR is_substitution IN (0, 1)
        ),
    is_timeout INTEGER
        CHECK (
            is_timeout IS NULL
            OR is_timeout IN (0, 1)
        ),

    PRIMARY KEY (game_id, event_number),

    FOREIGN KEY (game_id)
        REFERENCES games(game_id),
    FOREIGN KEY (team_id)
        REFERENCES teams(team_id),
    FOREIGN KEY (player1_id)
        REFERENCES players(player_id),
    FOREIGN KEY (player2_id)
        REFERENCES players(player_id),
    FOREIGN KEY (player3_id)
        REFERENCES players(player_id)
);

CREATE TABLE IF NOT EXISTS lineups (
    lineup_id TEXT PRIMARY KEY,
    unit_key TEXT NOT NULL,
    game_id TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    period INTEGER NOT NULL
        CHECK (period >= 1),
    start_event_number INTEGER,
    end_event_number INTEGER,
    start_clock TEXT,
    end_clock TEXT,
    start_seconds_remaining INTEGER,
    end_seconds_remaining INTEGER,
    duration_seconds INTEGER
        CHECK (
            duration_seconds IS NULL
            OR duration_seconds >= 0
        ),
    minutes REAL,
    possessions REAL,
    points_for INTEGER,
    points_against INTEGER,
    ortg REAL,
    drtg REAL,
    net_rating REAL,
    efg_pct REAL,
    tov_pct REAL,
    oreb_pct REAL,
    is_starting_lineup INTEGER
        CHECK (
            is_starting_lineup IS NULL
            OR is_starting_lineup IN (0, 1)
        ),
    is_quarter_opening INTEGER
        CHECK (
            is_quarter_opening IS NULL
            OR is_quarter_opening IN (0, 1)
        ),

    FOREIGN KEY (game_id)
        REFERENCES games(game_id),
    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS lineup_aggregates (
    lineup_id TEXT PRIMARY KEY,
    unit_key TEXT NOT NULL,
    sample_name TEXT NOT NULL,
    team_id INTEGER NOT NULL,
    group_name TEXT,
    games_played INTEGER,
    wins INTEGER,
    losses INTEGER,
    minutes REAL,
    possessions REAL,
    points REAL,
    plus_minus REAL,
    ortg REAL,
    drtg REAL,
    net_rating REAL,
    pace REAL,
    efg_pct REAL,
    tov_pct REAL,
    oreb_pct REAL,
    dreb_pct REAL,
    reb_pct REAL,
    is_pregame INTEGER NOT NULL DEFAULT 1
        CHECK (is_pregame IN (0, 1)),
    is_holdout INTEGER NOT NULL DEFAULT 0
        CHECK (is_holdout IN (0, 1)),
    source TEXT,

    CHECK (is_pregame + is_holdout <= 1),

    FOREIGN KEY (team_id)
        REFERENCES teams(team_id)
);

CREATE TABLE IF NOT EXISTS lineup_players (
    lineup_id TEXT NOT NULL,
    player_id INTEGER NOT NULL,

    PRIMARY KEY (lineup_id, player_id),

    FOREIGN KEY (player_id)
        REFERENCES players(player_id)
);

CREATE TABLE IF NOT EXISTS data_collection_log (
    collection_id INTEGER PRIMARY KEY AUTOINCREMENT,
    dataset_name TEXT NOT NULL,
    source TEXT NOT NULL,
    endpoint TEXT,
    game_id TEXT,
    retrieved_at TEXT NOT NULL,
    raw_file_path TEXT,
    row_count INTEGER
        CHECK (
            row_count IS NULL
            OR row_count >= 0
        ),
    status TEXT NOT NULL
        CHECK (
            status IN (
                'success',
                'partial',
                'failed'
            )
        ),
    notes TEXT,

    FOREIGN KEY (game_id)
        REFERENCES games(game_id)
);

CREATE INDEX IF NOT EXISTS idx_games_date
    ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_games_series_game
    ON games(series_game_number);
CREATE INDEX IF NOT EXISTS idx_games_pregame
    ON games(is_pregame);
CREATE INDEX IF NOT EXISTS idx_games_holdout
    ON games(is_holdout);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_team
    ON team_game_stats(team_id);
CREATE INDEX IF NOT EXISTS idx_team_game_stats_game
    ON team_game_stats(game_id);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_player
    ON player_game_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_player_game_stats_team
    ON player_game_stats(team_id);
CREATE INDEX IF NOT EXISTS idx_shots_game
    ON shots(game_id);
CREATE INDEX IF NOT EXISTS idx_shots_player
    ON shots(player_id);
CREATE INDEX IF NOT EXISTS idx_shots_zone
    ON shots(shot_zone);
CREATE INDEX IF NOT EXISTS idx_play_by_play_game
    ON play_by_play(game_id);
CREATE INDEX IF NOT EXISTS idx_play_by_play_period
    ON play_by_play(game_id, period);
CREATE INDEX IF NOT EXISTS idx_lineups_game_team
    ON lineups(game_id, team_id);
CREATE INDEX IF NOT EXISTS idx_lineups_unit
    ON lineups(unit_key);
CREATE INDEX IF NOT EXISTS idx_lineup_aggregates_sample
    ON lineup_aggregates(sample_name, team_id);
CREATE INDEX IF NOT EXISTS idx_lineup_aggregates_unit
    ON lineup_aggregates(unit_key);
CREATE INDEX IF NOT EXISTS idx_lineup_players_player
    ON lineup_players(player_id);
CREATE INDEX IF NOT EXISTS idx_collection_log_dataset
    ON data_collection_log(dataset_name);

CREATE VIEW IF NOT EXISTS pregame_games AS
SELECT *
FROM games
WHERE is_pregame = 1
  AND is_holdout = 0;

CREATE VIEW IF NOT EXISTS holdout_games AS
SELECT *
FROM games
WHERE is_holdout = 1
  AND is_pregame = 0;
