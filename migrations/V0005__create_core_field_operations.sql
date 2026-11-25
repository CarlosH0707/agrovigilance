-- Apontamentos de campo no formato canônico, com a lista fechada de tipos (ADR-0019).
CREATE TABLE core.field_operations (
    id            uuid        PRIMARY KEY DEFAULT uuidv7(),
    raw_event_id  uuid        NOT NULL UNIQUE REFERENCES raw.field_events (id),
    tenant_id     text        NOT NULL,
    field_id      text        NOT NULL,
    type          text        NOT NULL
                  CHECK (type IN ('pulverizacao_agendada', 'pulverizacao_concluida')),
    occurred_at   timestamptz NOT NULL,  -- quando o apontamento foi feito
    scheduled_for timestamptz,           -- quando a pulverização agendada vai acontecer
    created_at    timestamptz NOT NULL DEFAULT now(),
    CHECK (type <> 'pulverizacao_agendada' OR scheduled_for IS NOT NULL)
);
