-- Cadastro: produtores, contatos, propriedades, talhões e o que cada produtor tolera por cultura
-- (ADR-0026). Sem API: as linhas entram à mão.

CREATE TABLE core.producers (
    id         uuid        PRIMARY KEY DEFAULT uuidv7(),  -- é o tenant_id das outras tabelas
    name       text        NOT NULL,                      -- só para mostrar: pode repetir
    created_at timestamptz NOT NULL DEFAULT now()
);

-- Quem fala com o sistema. O celular é único (login e WhatsApp), mas não é id: muda e é reciclado.
CREATE TABLE core.producer_contacts (
    id          uuid        PRIMARY KEY DEFAULT uuidv7(),
    producer_id uuid        NOT NULL REFERENCES core.producers (id),
    name        text        NOT NULL,
    phone       text        NOT NULL UNIQUE CHECK (phone ~ '^\+[1-9][0-9]{7,14}$'),  -- E.164
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ON core.producer_contacts (producer_id);

-- O que o produtor decidiu tolerar em cada cultura (ex.: calor no café do ES).
CREATE TABLE core.producer_crops (
    producer_id                 uuid             NOT NULL REFERENCES core.producers (id),
    crop                        text             NOT NULL,
    temperature_tolerable_max_c double precision CHECK (temperature_tolerable_max_c BETWEEN 0 AND 50),
    PRIMARY KEY (producer_id, crop)
);

-- Propriedade: agrupa talhões e dá o fuso e a região.
CREATE TABLE core.farms (
    id            uuid             PRIMARY KEY DEFAULT uuidv7(),
    producer_id   uuid             NOT NULL REFERENCES core.producers (id),
    name          text             NOT NULL,
    region        text             NOT NULL CHECK (region ~ '^[A-Z]{2}$'),  -- UF
    -- Nome IANA; fuso desconhecido faz o próprio AT TIME ZONE falhar no insert.
    timezone      text             NOT NULL
                  CHECK ((timestamptz '2000-01-01 00:00+00' AT TIME ZONE timezone) IS NOT NULL),
    total_area_ha double precision CHECK (total_area_ha > 0),
    created_at    timestamptz      NOT NULL DEFAULT now(),
    UNIQUE (id, producer_id)  -- alvo da FK composta dos talhões
);
CREATE INDEX ON core.farms (producer_id);

-- Talhão: unidade de manejo com uma cultura. A previsão é coletada por talhão.
CREATE TABLE core.fields (
    producer_id uuid             NOT NULL REFERENCES core.producers (id),
    field_id    text             NOT NULL CHECK (field_id ~ '^[a-z0-9][a-z0-9_-]*$'),  -- vai nas chaves
    farm_id     uuid             NOT NULL,
    name        text             NOT NULL,
    crop        text             NOT NULL,
    area_ha     double precision CHECK (area_ha > 0),
    latitude    double precision NOT NULL CHECK (latitude BETWEEN -90 AND 90),
    longitude   double precision NOT NULL CHECK (longitude BETWEEN -180 AND 180),
    created_at  timestamptz      NOT NULL DEFAULT now(),
    PRIMARY KEY (producer_id, field_id),
    -- O talhão só pode estar numa propriedade do mesmo produtor.
    FOREIGN KEY (farm_id, producer_id) REFERENCES core.farms (id, producer_id)
);
