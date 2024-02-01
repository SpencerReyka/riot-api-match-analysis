CREATE TABLE match_data (
    id SERIAL PRIMARY KEY,
    riot_match_id TEXT UNIQUE,
    win BOOLEAN,
    dps_threat BOOLEAN,
    match_data TEXT
);