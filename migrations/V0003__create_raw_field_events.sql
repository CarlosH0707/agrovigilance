-- Dados brutos de apontamentos de campo (webhook), só INSERT (ADR-0002, ADR-0010).
CREATE TABLE raw.field_events (
    id              uuid        PRIMARY KEY DEFAULT uuidv7(),
    idempotency_key text        NOT NULL UNIQUE,
    tenant_id       text        NOT NULL,
    field_id        text        NOT NULL,
    occurred_at     timestamptz NOT NULL,
    ingested_at     timestamptz NOT NULL DEFAULT now(),
    payload         jsonb       NOT NULL,
    status          text        NOT NULL DEFAULT 'received'  -- ciclo definido na Fase 2
);

CREATE INDEX field_events_field_occurred_idx ON raw.field_events (field_id, occurred_at DESC);
CREATE INDEX field_events_payload_idx ON raw.field_events USING gin (payload);
