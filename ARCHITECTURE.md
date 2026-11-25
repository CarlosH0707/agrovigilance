# Arquitetura

> Estado: **Fase 1 em andamento.** Implementado até aqui: schemas e tabelas raw (migrations V0001–V0003). Decisões fechadas estão em [`docs/decisions/`](docs/decisions/).

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
                                                            Harness (regras + anti-spam) ─► LLM (opcional)
                                                                                   │
                                                                                   ▼
                                                                Canal (Console → WhatsApp)
```

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
| **Agente LLM** | Redige o alerta a partir do snapshot, com saída estruturada (Pydantic) e evals | 3 |
| **Canal** | Adaptador de saída: `ConsoleChannel` primeiro, `WhatsAppChannel` depois | 3–4 |

## Fluxo de ingestão (Fase 1)

1. A fonte chega (poll ou webhook) e calculamos a `idempotency_key`.
2. `INSERT INTO raw.<fonte>_events ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING id`.
3. Sem `id` de volta → duplicata: responde OK e **não** publica nada.
4. Com `id` → depois do commit, publica uma mensagem fina na fila (`source` + `event_id` + metadados, sem o payload).

Por que assim: [ADR-0002](docs/decisions/0002-idempotencia-na-ingestao.md), [ADR-0003](docs/decisions/0003-sqs-standard-com-dlq.md), [ADR-0004](docs/decisions/0004-publicar-apos-commit-sem-outbox.md), [ADR-0010](docs/decisions/0010-schemas-do-banco.md).

### Chaves de idempotência

| Fonte | Chave |
|---|---|
| Webhook de campo | `field_event:{source_event_id}`, ou hash de `(tenant_id, field_id, type, occurred_at)` se a origem não mandar id |
| Open-Meteo | `weather:{field_id}:{target_hour}:{bucket}` |

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
| `status` | text | ciclo de processamento, `DEFAULT 'received'` (valores definidos na Fase 2) |

Índices: `(field_id, occurred_at DESC)` e GIN em `payload`.

### `read.field_snapshot` (Fase 2)

Uma linha por talhão com o último estado consolidado (clima recente, próximas horas, operações agendadas). Esquema a definir em ADR próprio.

## Domínio: regras do MVP

- **Janela de pulverização:** variáveis `temperature_2m`, `relative_humidity_2m`, `precipitation_probability`, `wind_speed_10m`. Limites exatos a definir com quem é do campo e registrar em ADR.
- **Risco de colheita/tráfego:** chuva acumulada e umidade. Limites a definir.

## Fora do escopo por enquanto

- Outbox transacional (evolução prevista, ver ADR-0004)
- Fila FIFO
- Multi-tenant de verdade (autenticação, isolamento)
- Deploy em nuvem
