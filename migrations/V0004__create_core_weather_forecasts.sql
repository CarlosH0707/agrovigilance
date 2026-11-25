-- Previsão horária no formato canônico, uma linha por linha do raw (ADR-0019).
CREATE TABLE core.weather_forecasts (
    id                            uuid             PRIMARY KEY DEFAULT uuidv7(),
    raw_event_id                  uuid             NOT NULL UNIQUE REFERENCES raw.open_meteo_events (id),
    tenant_id                     text             NOT NULL,
    field_id                      text             NOT NULL,
    target_hour                   timestamptz      NOT NULL,
    fetched_at                    timestamptz      NOT NULL,
    temperature_c                 double precision,
    relative_humidity_pct         double precision,
    precipitation_probability_pct double precision,
    wind_speed_kmh                double precision,
    created_at                    timestamptz      NOT NULL DEFAULT now()
);
