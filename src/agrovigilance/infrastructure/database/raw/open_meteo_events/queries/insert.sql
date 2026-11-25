-- Grava cada hora prevista uma vez por coleta; devolve o id, ou nada se a chave já existia (ADR-0002).
INSERT INTO raw.open_meteo_events (idempotency_key, tenant_id, field_id, occurred_at, payload)
VALUES (%(idempotency_key)s, %(tenant_id)s, %(field_id)s, %(occurred_at)s, %(payload)s)
ON CONFLICT (idempotency_key) DO NOTHING
RETURNING id
