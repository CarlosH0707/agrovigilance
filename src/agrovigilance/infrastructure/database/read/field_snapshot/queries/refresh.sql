-- Recalcula a linha do talhão inteira a partir de core (ADR-0022).
-- O resultado só depende do que está em core: ordem de chegada e reentrega não mudam nada.
WITH latest_forecast AS (
    -- Cada hora alvo é prevista de novo a cada coleta: vale a de maior fetched_at.
    SELECT DISTINCT ON (target_hour)
        target_hour, fetched_at, temperature_c, relative_humidity_pct,
        precipitation_probability_pct, wind_speed_kmh
    FROM core.weather_forecasts
    WHERE tenant_id = %(tenant_id)s
      AND field_id = %(field_id)s
      AND target_hour >= date_trunc('hour', now())
    ORDER BY target_hour, fetched_at DESC
),
last_operation AS (
    SELECT type, occurred_at
    FROM core.field_operations
    WHERE tenant_id = %(tenant_id)s AND field_id = %(field_id)s
    ORDER BY occurred_at DESC, id DESC
    LIMIT 1
),
open_schedule AS (
    -- O último agendamento vale até aparecer uma conclusão apontada depois dele.
    SELECT s.scheduled_for, s.product, s.product_class, s.equipment
    FROM core.field_operations s
    WHERE s.tenant_id = %(tenant_id)s
      AND s.field_id = %(field_id)s
      AND s.type = 'pulverizacao_agendada'
      AND NOT EXISTS (
          SELECT 1
          FROM core.field_operations d
          WHERE d.tenant_id = s.tenant_id
            AND d.field_id = s.field_id
            AND d.type = 'pulverizacao_concluida'
            AND d.occurred_at > s.occurred_at
      )
    ORDER BY s.occurred_at DESC, s.id DESC
    LIMIT 1
)
INSERT INTO read.field_snapshot (
    tenant_id, field_id, forecast, scheduled_spraying_for,
    scheduled_product, scheduled_product_class, scheduled_equipment,
    last_operation_type, last_operation_at, updated_at
)
SELECT
    %(tenant_id)s,
    %(field_id)s,
    (SELECT coalesce(jsonb_agg(to_jsonb(f) ORDER BY f.target_hour), '[]') FROM latest_forecast f),
    (SELECT scheduled_for FROM open_schedule),
    (SELECT product FROM open_schedule),
    (SELECT product_class FROM open_schedule),
    (SELECT equipment FROM open_schedule),
    (SELECT type FROM last_operation),
    (SELECT occurred_at FROM last_operation),
    now()
ON CONFLICT (tenant_id, field_id) DO UPDATE SET
    forecast = EXCLUDED.forecast,
    scheduled_spraying_for = EXCLUDED.scheduled_spraying_for,
    scheduled_product = EXCLUDED.scheduled_product,
    scheduled_product_class = EXCLUDED.scheduled_product_class,
    scheduled_equipment = EXCLUDED.scheduled_equipment,
    last_operation_type = EXCLUDED.last_operation_type,
    last_operation_at = EXCLUDED.last_operation_at,
    updated_at = EXCLUDED.updated_at
