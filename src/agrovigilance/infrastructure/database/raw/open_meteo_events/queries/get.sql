-- Lê a linha que a mensagem da fila aponta (ADR-0019).
SELECT id, tenant_id, field_id, occurred_at, ingested_at, payload
FROM raw.open_meteo_events
WHERE id = %(id)s
