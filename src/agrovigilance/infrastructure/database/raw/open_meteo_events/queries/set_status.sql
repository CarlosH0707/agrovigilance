-- Única atualização permitida no raw: o status do processamento (ADR-0019).
UPDATE raw.open_meteo_events SET status = %(status)s WHERE id = %(id)s
