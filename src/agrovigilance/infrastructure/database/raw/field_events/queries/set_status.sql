-- Única atualização permitida no raw: o status do processamento (ADR-0019).
UPDATE raw.field_events SET status = %(status)s WHERE id = %(id)s
