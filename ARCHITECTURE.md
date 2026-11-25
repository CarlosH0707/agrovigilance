# Arquitetura

> Estado: **proposta** (Fase 0). Nada aqui está implementado ainda. Decisões fechadas estão em [`docs/decisions/`](docs/decisions/).

## Visão geral

```
 Open-Meteo ──(poll)──┐
                      ├─► Ingestão ─► raw_events (Postgres, idempotente)
 Webhook de campo ────┘        │
                               └─(após commit)─► fila agrovigilance-events ─► Workers
                                                         │ falha 3x                │
                                                         ▼                         ▼
                                                 agrovigilance-events-dlq   field_snapshot (read model)
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
| **Ingestão Open-Meteo** | Busca previsão horária por talhão e grava em `raw_events` | 1 |
| **API de webhook** (`POST /webhooks/field`) | Recebe apontamentos de campo e grava em `raw_events` | 1 |
| **`raw_events`** | Log bruto e imutável de tudo que entrou, com chave de idempotência | 1 |
| **Fila + DLQ** | Desacopla ingestão de processamento; mensagens com falha vão para a DLQ após 3 tentativas | 1 |
| **Workers** | Consomem a fila, normalizam o evento (canonical payload) e atualizam o read model | 2 |
| **`field_snapshot`** | Read model (CQRS): estado consolidado e atual de cada talhão | 2 |
| **Harness** | Regras determinísticas e anti-spam que decidem se vale alertar, antes de qualquer LLM | 3 |
| **Agente LLM** | Redige o alerta a partir do snapshot, com saída estruturada (Pydantic) e evals | 3 |
| **Canal** | Adaptador de saída: `ConsoleChannel` primeiro, `WhatsAppChannel` depois | 3–4 |

## Fluxo de ingestão (Fase 1)

1. A fonte chega (poll ou webhook) e calculamos a `idempotency_key`.
2. `INSERT INTO raw_events ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING id`.
3. Sem `id` de volta → duplicata: responde OK e **não** publica nada.
4. Com `id` → depois do commit, publica uma mensagem fina na fila (`event_id` + metadados, sem o payload).

Por que assim: [ADR-0002](docs/decisions/0002-idempotencia-na-ingestao.md), [ADR-0003](docs/decisions/0003-sqs-standard-com-dlq.md), [ADR-0004](docs/decisions/0004-publicar-apos-commit-sem-outbox.md).

### Chaves de idempotência

| Fonte | Chave |
|---|---|
| Webhook de campo | `field_event:{source_event_id}`, ou hash de `(tenant_id, field_id, type, occurred_at)` se a origem não mandar id |
| Open-Meteo | `weather:{field_id}:{target_hour}:{bucket}` |

## Modelo de dados

### `raw_events`

| Coluna | Tipo | Notas |
|---|---|---|
| `id` | UUID | PK |
| `idempotency_key` | text | UNIQUE |
| `source` | text | `open_meteo`, `field_webhook`, ... |
| `tenant_id` | text | |
| `field_id` | text | talhão |
| `occurred_at` | timestamptz | quando o fato aconteceu |
| `ingested_at` | timestamptz | quando chegou |
| `payload` | JSONB | payload bruto, como veio |
| `status` | text | ciclo de processamento |

Índices: `(field_id, occurred_at DESC)` e GIN em `payload`.

### `field_snapshot` (Fase 2)

Uma linha por talhão com o último estado consolidado (clima recente, próximas horas, operações agendadas). Esquema a definir em ADR próprio.

## Domínio: regras do MVP

- **Janela de pulverização:** variáveis `temperature_2m`, `relative_humidity_2m`, `precipitation_probability`, `wind_speed_10m`. Limites exatos a definir com quem é do campo e registrar em ADR.
- **Risco de colheita/tráfego:** chuva acumulada e umidade. Limites a definir.

## Fora do escopo por enquanto

- Outbox transacional (evolução prevista, ver ADR-0004)
- Fila FIFO
- Multi-tenant de verdade (autenticação, isolamento)
- Deploy em nuvem
