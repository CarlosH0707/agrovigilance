-- Grava o apontamento canônico uma vez por linha do raw; reentrega da fila não duplica (ADR-0019).
INSERT INTO core.field_operations (
    raw_event_id, tenant_id, field_id, type, occurred_at, scheduled_for,
    product, product_class, equipment
)
VALUES (
    %(raw_event_id)s, %(tenant_id)s, %(field_id)s, %(type)s, %(occurred_at)s, %(scheduled_for)s,
    %(product)s, %(product_class)s, %(equipment)s
)
ON CONFLICT (raw_event_id) DO NOTHING
