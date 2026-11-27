# 0019. Canonical payload: uma tabela por tipo de evento em `core`

- **Status:** aceita (apontamento ampliado com produto e equipamento pelo [ADR-0027](0027-produto-e-equipamento-no-agendamento.md))
- **Data:** 2026-11-25

## Contexto
O raw guarda cada fonte como chegou (ADR-0010). As regras da Fase 3 e o `read.field_snapshot` precisam de um formato interno estável, que não dependa do JSON da Open-Meteo nem do texto livre do webhook. Na Fase 1 o `type` do apontamento é texto livre, e o `status` do raw ficou como `received`, com o ciclo a definir na Fase 2.

## Decisão
- **Uma tabela por tipo em `core`**, com colunas tipadas: `core.weather_forecasts` e `core.field_operations`. Cada linha aponta para a linha do raw de onde veio (`raw_event_id`, UNIQUE + FK). A UNIQUE é o que deixa o worker idempotente: reprocessar a mesma mensagem não duplica nada.
- **Previsão (`core.weather_forecasts`):** `target_hour`, `fetched_at`, `temperature_c`, `relative_humidity_pct`, `precipitation_probability_pct` e `wind_speed_kmh`. Os valores podem ser nulos (a API às vezes não tem a hora). O `fetched_at` é o `raw.ingested_at`, gravado no mesmo instante da coleta, porque o raw não guarda a hora da coleta em coluna própria. A conversão confere `utc_offset_seconds = 0` e as unidades em `hourly_units`. Uma unidade diferente da esperada indica bug na ingestão, então a conversão falha em vez de converter.
- **Apontamento (`core.field_operations`):** lista fechada de tipos, por enquanto `pulverizacao_agendada` e `pulverizacao_concluida` (o caso de uso 1). Tipo novo entra por ADR. `pulverizacao_agendada` exige `scheduled_for` com fuso (quando a pulverização vai acontecer), porque a regra de janela cruza esse horário com a previsão. O `occurred_at` continua sendo quando o apontamento foi feito.
- **Evento inválido** (tipo fora da lista ou agendamento sem `scheduled_for`) não é erro transitório, e tentar de novo não resolve. O worker marca o raw como `rejected` e apaga a mensagem, em vez de deixá-la ir para a DLQ.
- **Ciclo do `status` no raw:** `received` → `processed` (gravado no core) ou `rejected` (inválido). É a única atualização permitida no raw. O payload continua imutável.
- A conversão raw → canônico é código puro em `domain/`, com teste unitário. O banco repete as regras com `CHECK`.

## Consequências
- As regras e o snapshot leem colunas tipadas, sem JSONB.
- O webhook continua aceitando qualquer `type` (contrato do ADR-0016). Apontamentos fora da lista ficam no raw como `rejected` e podem ser reprocessados se a lista crescer.
- Cada tipo novo de evento exige uma migration e um ADR.
- A DLQ fica só para falhas inesperadas (banco fora, bug), não para dado inválido.

## Alternativas consideradas
- Tabela única `core.events` com `type` + `data` JSONB: mais genérica, mas as regras teriam que ler JSONB, e o banco não validaria nada.
- Rejeitar tipo desconhecido já no webhook (422): mudaria o contrato do ADR-0016, e o raw perderia esses eventos.
- Deixar o evento inválido ir para a DLQ: ele passaria 3 vezes pelo worker sem chance de dar certo e encheria a DLQ de casos que não são falha.
- Tipo genérico `outro`: guardaria tudo, mas nenhuma regra usaria. A lista cresce quando surgir um caso de uso.
