-- Grava a previsão canônica uma vez por linha do raw; reentrega da fila não duplica (ADR-0019).
INSERT INTO core.weather_forecasts (
    raw_event_id, tenant_id, field_id, target_hour, fetched_at,
    temperature_c, relative_humidity_pct, precipitation_probability_pct, wind_speed_kmh
)
VALUES (
    %(raw_event_id)s, %(tenant_id)s, %(field_id)s, %(target_hour)s, %(fetched_at)s,
    %(temperature_c)s, %(relative_humidity_pct)s, %(precipitation_probability_pct)s,
    %(wind_speed_kmh)s
)
ON CONFLICT (raw_event_id) DO NOTHING
