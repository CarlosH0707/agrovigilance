-- Read model por talhão, recalculado a partir de core a cada evento processado (ADR-0022).
CREATE TABLE read.field_snapshot (
    tenant_id              text        NOT NULL,
    field_id               text        NOT NULL,
    forecast               jsonb       NOT NULL DEFAULT '[]',  -- próximas horas, coleta mais recente de cada hora
    scheduled_spraying_for timestamptz,                         -- pulverização agendada ainda não concluída
    last_operation_type    text,
    last_operation_at      timestamptz,
    updated_at             timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, field_id)
);
