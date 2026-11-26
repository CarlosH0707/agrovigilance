-- Talhões com o fuso e a região da propriedade e a tolerância do produtor para a cultura (ADR-0026).
SELECT
    f.producer_id::text AS producer_id,
    f.field_id,
    f.name,
    f.crop,
    f.area_ha,
    f.latitude,
    f.longitude,
    fa.region,
    fa.timezone,
    pc.temperature_tolerable_max_c
FROM core.fields f
JOIN core.farms fa ON fa.id = f.farm_id
LEFT JOIN core.producer_crops pc ON pc.producer_id = f.producer_id AND pc.crop = f.crop
ORDER BY f.producer_id, f.field_id
