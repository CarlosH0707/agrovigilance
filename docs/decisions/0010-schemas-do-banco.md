# 0010. Schemas do banco: `raw`, `core` e `read`

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
O banco guarda três tipos de dado com regras diferentes: o que chegou das fontes (imutável), o dado normalizado que o sistema usa (modelo de escrita) e as visões prontas para consulta (modelo de leitura do CQRS). Misturar tudo no `public` esconde essas fronteiras.

## Decisão
| Schema | Conteúdo | Regra |
|---|---|---|
| `raw` | Dados como chegaram, **uma tabela por fonte**: `raw.open_meteo_events`, `raw.field_events` | Só `INSERT`; nunca atualizar o payload |
| `core` | Eventos no formato canônico, cadastros (`tenants`, `fields`) e histórico de alertas enviados | Modelo de escrita, fonte da verdade do domínio |
| `read` | Read models, como `read.field_snapshot` | Pode ser apagado e reconstruído a partir de `core` |

- Tabelas sem prefixo repetindo o schema (`raw.open_meteo_events`, não `raw.raw_open_meteo_events`).
- Substitui a tabela única `raw_events` descrita no ADR-0002; a lógica de idempotência continua a mesma, agora por tabela.
- Schema novo só com ADR próprio.

## Consequências
- Fronteiras claras entre ingestão, domínio e leitura; permissões podem ser dadas por schema no futuro.
- Cada fonte tem colunas e índices próprios, em vez de um JSONB genérico para tudo.
- A mensagem da fila precisa dizer de qual tabela raw o evento veio (`source` + `event_id`).

## Alternativas consideradas
- Dois schemas (`raw` e `tratado`): mistura modelo de escrita e de leitura.
- Tabela raw única para todas as fontes: genérica demais; cada fonte tem chave e formato próprios.
