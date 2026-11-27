-- Produto, classe e equipamento no apontamento e no snapshot (ADR-0027).
-- Produto é texto: o do catálogo vira id; o desconhecido fica como veio.
ALTER TABLE core.field_operations
    ADD COLUMN product       text,
    ADD COLUMN product_class text CHECK (product_class IN ('fungicida', 'inseticida', 'herbicida', 'biologico')),
    ADD COLUMN equipment     text CHECK (equipment IN ('trator', 'drone', 'costal'));

ALTER TABLE read.field_snapshot
    ADD COLUMN scheduled_product       text,
    ADD COLUMN scheduled_product_class text,
    ADD COLUMN scheduled_equipment     text;  -- vazio: o alerta pergunta, nunca assume
