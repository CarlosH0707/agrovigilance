-- O talhão está cadastrado para esse produtor (ADR-0026).
SELECT EXISTS (
    SELECT 1 FROM core.fields WHERE producer_id = %(producer_id)s AND field_id = %(field_id)s
)
