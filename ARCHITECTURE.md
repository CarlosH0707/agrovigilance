# Arquitetura

> Estado: **Fase 2 concluída.** Fase 1 concluída (raw, fila + DLQ, webhook e poller idempotentes). Na Fase 2: formato canônico em `core` (migrations V0004–V0005, ADR-0019), worker em loop com long polling (ADR-0021) e `read.field_snapshot` recalculado por talhão (V0006, ADR-0022); DLQ e redrive testados de ponta a ponta (ADR-0023). Decisões fechadas estão em [`docs/decisions/`](docs/decisions/).

## Visão geral

```
 Open-Meteo ──(poll)──┐
                      ├─► Ingestão ─► raw.<fonte>_events (Postgres, idempotente)
 Webhook de campo ────┘        │
                               └─(após commit)─► fila agrovigilance-events ─► Workers
                                                         │ falha 3x                │
                                                         ▼                         ▼
                                                 agrovigilance-events-dlq   read.field_snapshot
                                                                                   │
                                                                                   ▼
                                                            Harness (regras + anti-spam) ─► alerta por template
                                                                                   │
                                                                                   ▼
                                                                Canal (Console → WhatsApp)
```

Na Fase 4, a mensagem do WhatsApp em texto livre passa por um LLM que extrai o apontamento (Pydantic) e entra no mesmo fluxo do webhook ([ADR-0020](docs/decisions/0020-llm-na-entrada-e-nao-no-alerta.md)).

## Componentes

| Componente | Responsabilidade | Fase |
|---|---|---|
| **Ingestão Open-Meteo** | Busca previsão horária por talhão e grava em `raw.open_meteo_events` | 1 |
| **API de webhook** (`POST /webhooks/field`) | Recebe apontamentos de campo e grava em `raw.field_events` | 1 |
| **Schema `raw`** | Log bruto e imutável de tudo que entrou, uma tabela por fonte, com chave de idempotência | 1 |
| **Fila + DLQ** | Desacopla ingestão de processamento; mensagens com falha vão para a DLQ após 3 tentativas; criadas por `scripts/create_queues.py` ([ADR-0015](docs/decisions/0015-filas-criadas-por-script-e-testadas-no-floci.md)) | 1 |
| **Workers** | Consomem a fila, normalizam o evento (canonical payload) em `core` e atualizam o read model | 2 |
| **`read.field_snapshot`** | Read model (CQRS): estado consolidado e atual de cada talhão | 2 |
| **Harness** | Regras determinísticas e anti-spam que decidem se vale alertar, antes de qualquer LLM | 3 |
| **Alerta por template** | Texto do alerta montado com os dados do snapshot, sem LLM ([ADR-0020](docs/decisions/0020-llm-na-entrada-e-nao-no-alerta.md)) | 3 |
| **Agente LLM** | Interpreta o apontamento em texto livre do WhatsApp (saída Pydantic), pergunta o que faltar e responde perguntas com uma consulta ao snapshot; evals com mensagens reais | 4 |
| **Canal** | Adaptador de saída: `ConsoleChannel` primeiro, `WhatsAppChannel` depois | 3–4 |

## Organização do código

Camadas dentro de `src/agrovigilance/` ([ADR-0017](docs/decisions/0017-camadas-dentro-do-pacote.md)):

```
domain/          regras puras (FieldEvent, WeatherReading, idempotency_key; canônicos WeatherForecast e FieldOperation; RawEvent)
application/     casos de uso + portas (ingest_field_event: EventStore, Publisher; ingest_weather: WeatherStore;
                 process_event: RawEvents, CanonicalStore, Snapshot)
infrastructure/  adaptadores
  database/      connection.py + <schema>/<tabela>/{repository.py, queries/*.sql}
  queues/        <fila>/publisher.py e consumer.py
  open_meteo/    client.py (busca + quebra em uma leitura por hora)
entrypoints/     API FastAPI (api.py), poller.py (uma coleta da Open-Meteo), worker.py (loop na fila)
```

## Fluxo de ingestão (Fase 1)

1. A fonte chega (poll ou webhook) e calculamos a `idempotency_key`.
2. `INSERT INTO raw.<fonte>_events ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING id`.
3. Sem `id` de volta → duplicata: responde OK e **não** publica nada.
4. Com `id` → depois do commit, publica uma mensagem fina na fila (`source` + `event_id` + metadados, sem o payload).

`POST /webhooks/field` ([ADR-0016](docs/decisions/0016-fastapi-para-a-api-http.md)) exige `tenant_id`, `field_id`, `type` (texto livre na Fase 1) e `occurred_at` com fuso; `source_event_id` é opcional e campos extras são guardados no payload. Responde **202** (novo, com `event_id`), **200** (`duplicate`) ou **422** (inválido).

O poller da Open-Meteo ([ADR-0018](docs/decisions/0018-ingestao-open-meteo-por-hora.md)) busca 7 dias de previsão horária ([ADR-0025](docs/decisions/0025-previsao-de-7-dias.md)) de cada talhão cadastrado em `core.fields` ([ADR-0026](docs/decisions/0026-cadastro-de-produtores-e-talhoes.md)) e grava uma linha por hora prevista; a falha de um talhão não para os outros: `uv run --env-file .env python -m agrovigilance.entrypoints.poller`.

Por que assim: [ADR-0002](docs/decisions/0002-idempotencia-na-ingestao.md), [ADR-0003](docs/decisions/0003-sqs-standard-com-dlq.md), [ADR-0004](docs/decisions/0004-publicar-apos-commit-sem-outbox.md), [ADR-0010](docs/decisions/0010-schemas-do-banco.md).

### Chaves de idempotência

| Fonte | Chave |
|---|---|
| Webhook de campo | `field_event:{source_event_id}`, ou hash de `(tenant_id, field_id, type, occurred_at)` se a origem não mandar id |
| Open-Meteo | `weather:{tenant_id}:{field_id}:{target_hour}:{bucket}`, com bucket = hora da coleta, tudo em UTC ([ADR-0018](docs/decisions/0018-ingestao-open-meteo-por-hora.md)) |

## Fluxo de processamento (Fase 2)

O worker ([ADR-0021](docs/decisions/0021-worker-em-loop-com-long-polling.md)) roda em loop: `uv run --env-file .env python -m agrovigilance.entrypoints.worker`.

1. Long polling na fila (até 10 mensagens, espera de até 20 s).
2. Valida a mensagem (`source` + `event_id`) e lê a linha do raw. Apontamento de talhão não cadastrado em `core.fields` vira `rejected` ([ADR-0027](docs/decisions/0027-produto-e-equipamento-no-agendamento.md)).
3. Converte para o formato canônico e grava em `core` com `ON CONFLICT (raw_event_id) DO NOTHING`.
4. Recalcula a linha do talhão em `read.field_snapshot` a partir de `core` ([ADR-0022](docs/decisions/0022-field-snapshot-recalculado-por-talhao.md)).
5. Marca o raw como `processed` (ou `rejected`, se o apontamento for inválido) e **só então** apaga a mensagem.
6. Erro inesperado: não apaga. A mensagem volta após o visibility timeout e, no 3º recebimento, vai para a DLQ. Se o erro for de infraestrutura (banco fora), o worker registra, espera 5 s e segue.
7. Corrigida a causa, `uv run --env-file .env python scripts/redrive_dlq.py` devolve as mensagens da DLQ para a fila de origem ([ADR-0023](docs/decisions/0023-redrive-nativo-da-dlq.md)).

## Modelo de dados

Três schemas ([ADR-0010](docs/decisions/0010-schemas-do-banco.md)). Toda mudança de estrutura entra por `migrations/V<NNNN>__<nome>.sql`, aplicada pelo runner `scripts/migrate.py`, que registra versão e checksum em `public.schema_migrations` ([ADR-0009](docs/decisions/0009-migrations-versionadas.md), [ADR-0013](docs/decisions/0013-migrations-no-padrao-flyway-com-runner-proprio.md)).

| Schema | Conteúdo | Regra |
|---|---|---|
| `raw` | Dados como chegaram, uma tabela por fonte | Só `INSERT` |
| `core` | Eventos canônicos, `tenants`, `fields`, alertas enviados | Fonte da verdade do domínio |
| `read` | Read models (`field_snapshot`) | Reconstruível a partir de `core` |

### `raw.open_meteo_events` e `raw.field_events`

Colunas comuns às duas (cada fonte pode ganhar colunas próprias):

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK, `DEFAULT uuidv7()` (ordenável por tempo) |
| `idempotency_key` | text | UNIQUE |
| `tenant_id` | text | |
| `field_id` | text | talhão |
| `occurred_at` | timestamptz | quando o fato aconteceu |
| `ingested_at` | timestamptz | quando chegou, `DEFAULT now()` |
| `payload` | JSONB | payload bruto, como veio |
| `status` | text | `received` → `processed` ou `rejected` ([ADR-0019](docs/decisions/0019-canonical-payload-por-tipo.md)); única coluna que muda |

Índices: `(field_id, occurred_at DESC)` e GIN em `payload`.

### `core.weather_forecasts` e `core.field_operations` (canonical payload)

Formato interno por tipo de evento, com colunas tipadas ([ADR-0019](docs/decisions/0019-canonical-payload-por-tipo.md)). A conversão raw → canônico é código puro em `domain/`.

- Cada linha tem `raw_event_id` (UNIQUE + FK para o raw de origem), o que faz o reprocessamento da mesma mensagem não duplicar nada.
- `core.weather_forecasts`: `target_hour`, `fetched_at` (= `raw.ingested_at`), `temperature_c`, `relative_humidity_pct`, `precipitation_probability_pct`, `wind_speed_kmh` (podem ser nulos). Unidade inesperada no payload é erro.
- `core.field_operations`: `type` na lista fechada (`pulverizacao_agendada`, `pulverizacao_concluida`), `occurred_at` e `scheduled_for` (obrigatório no agendamento), mais `product` (id do catálogo de `domain/products.py` ou o texto como veio), `product_class` e `equipment` (listas fechadas, opcionais; equipamento nunca é assumido) ([ADR-0027](docs/decisions/0027-produto-e-equipamento-no-agendamento.md)). O que não cabe vira `rejected` no raw, sem ir para a DLQ.

### Cadastro (Fase 3, [ADR-0026](docs/decisions/0026-cadastro-de-produtores-e-talhoes.md))

```
producers (id = tenant_id) ─┬─ producer_contacts (phone UNIQUE, E.164)
                            ├─ producer_crops    (crop, temperature_tolerable_max_c)
                            └─ farms (region, timezone) ── fields (field_id, crop, area_ha, lat/lon)
```

Sem API: as linhas entram à mão, com SQL fora do git. O `tenant_id` das outras tabelas é o UUID do produtor.

### `read.field_snapshot` (Fase 2)

Uma linha por `(tenant_id, field_id)` com o último estado consolidado ([ADR-0022](docs/decisions/0022-field-snapshot-recalculado-por-talhao.md)). A cada mensagem processada, o worker recalcula a linha do talhão inteira a partir de `core` (`INSERT ... SELECT ... ON CONFLICT DO UPDATE`), então ordem de chegada e reentrega não mudam o resultado.

| Coluna | Tipo | Notas |
|---|---|---|
| `forecast` | JSONB | próximas horas, ordenadas; por hora, a coleta de maior `fetched_at` |
| `scheduled_spraying_for` | timestamptz | último agendamento sem conclusão apontada depois dele |
| `scheduled_product`, `scheduled_product_class`, `scheduled_equipment` | text | produto, classe e equipamento desse agendamento (vazios se não informados) |
| `last_operation_type`, `last_operation_at` | text, timestamptz | apontamento mais recente |
| `updated_at` | timestamptz | último refresh |

## Domínio: regras do MVP

- **Janela de pulverização** ([ADR-0024](docs/decisions/0024-regras-da-janela-de-pulverizacao.md)): `domain/spraying_profile.py` guarda os limites por cultura (perfil base) e ajustes por contexto (região, produtor, equipamento, classe de produto, marca, produto), cada limite com motivo e fonte. `domain/spraying_window.py` avalia a sessão agendada (2 h + 6 h sem chuva depois, ou o que a bula do produto pedir; vento convertido para 2 m pela FAO-56) e devolve o nível:

  | Nível | Quando |
  |---|---|
  | `ok` | tudo dentro do ideal |
  | `attention` | algum valor só na faixa tolerável |
  | `postpone` | bloqueado, com janela boa nas próximas 72 h (sugere o início, sempre entre 6h e 18h locais) |
  | `no_window` | bloqueado, sem janela boa nas próximas 72 h |
- **Risco de colheita/tráfego:** chuva acumulada e umidade. Limites a definir.

## Fora do escopo por enquanto

- Outbox transacional (evolução prevista, ver ADR-0004)
- Fila FIFO
- Multi-tenant de verdade (autenticação, isolamento)
- Deploy em nuvem
