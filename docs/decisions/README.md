# Decisões de arquitetura (ADRs)

Cada decisão relevante vira um arquivo `NNNN-titulo-curto.md`. Decisões não são apagadas: quando mudam, um ADR novo marca o antigo como **substituído**.

Status possíveis: `proposta` · `aceita` · `substituída por ADR-NNNN` · `descartada`.

| # | Decisão | Status |
|---|---|---|
| [0001](0001-registrar-decisoes-como-adr.md) | Registrar decisões como ADRs, espelhadas no second brain | aceita |
| [0002](0002-idempotencia-na-ingestao.md) | Idempotência na ingestão com chave única e `ON CONFLICT DO NOTHING` | aceita |
| [0003](0003-sqs-standard-com-dlq.md) | SQS Standard + DLQ, idempotência na aplicação | aceita |
| [0004](0004-publicar-apos-commit-sem-outbox.md) | Publicar na fila após o commit, sem outbox por enquanto | aceita |
| [0005](0005-canal-de-notificacao-como-adaptador.md) | Canal de notificação como adaptador (Console → WhatsApp) | aceita |
| [0006](0006-stack-e-ambiente-local.md) | Infraestrutura local: Postgres 19 e Floci no Docker do WSL | aceita |
| [0007](0007-harness-deterministico-antes-do-llm.md) | Harness determinístico antes do LLM | aceita |
| [0008](0008-fluxo-de-branches.md) | Fluxo de branches: nada de commit direto na `main` | aceita |
| [0009](0009-migrations-versionadas.md) | Toda mudança de tabela é uma migration versionada | aceita |
| [0010](0010-schemas-do-banco.md) | Schemas do banco: `raw`, `core` e `read` | aceita |
| [0011](0011-python-uv-e-testes.md) | Python 3.14, `uv` e testes unitários com `pytest` desde o início | aceita |

## Template

```markdown
# NNNN. Título

- **Status:** proposta
- **Data:** YYYY-MM-DD

## Contexto
O problema e as forças em jogo.

## Decisão
O que foi decidido, em uma ou duas frases.

## Consequências
O que fica mais fácil, o que fica mais difícil, o que aceitamos pagar.

## Alternativas consideradas
- Opção — por que não.
```
