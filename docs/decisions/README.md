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
| [0009](0009-migrations-versionadas.md) | Toda mudança de tabela é uma migration versionada | aceita (nomes substituídos pelo 0013) |
| [0010](0010-schemas-do-banco.md) | Schemas do banco: `raw`, `core` e `read` | aceita |
| [0011](0011-python-uv-e-testes.md) | Python 3.14, `uv` e testes unitários com `pytest` desde o início | aceita |
| [0012](0012-testes-ao-lado-do-codigo.md) | Testes unitários ao lado do código (`<modulo>_test.py`) | aceita |
| [0013](0013-migrations-no-padrao-flyway-com-runner-proprio.md) | Migrations no padrão de nomes do Flyway, aplicadas por um runner próprio | aceita |
| [0014](0014-testes-de-integracao-com-testcontainers.md) | Testes de integração com testcontainers | aceita |
| [0015](0015-filas-criadas-por-script-e-testadas-no-floci.md) | Filas criadas por script idempotente e testadas contra o Floci | aceita |
| [0016](0016-fastapi-para-a-api-http.md) | FastAPI + uvicorn para a API HTTP | aceita |
| [0017](0017-camadas-dentro-do-pacote.md) | Código organizado em camadas dentro do pacote | aceita |
| [0018](0018-ingestao-open-meteo-por-hora.md) | Ingestão da Open-Meteo: uma linha por hora prevista e por coleta | aceita |
| [0019](0019-canonical-payload-por-tipo.md) | Canonical payload: uma tabela por tipo de evento em `core` | aceita |
| [0020](0020-llm-na-entrada-e-nao-no-alerta.md) | LLM na entrada em texto livre, não na redação do alerta | aceita |
| [0021](0021-worker-em-loop-com-long-polling.md) | Worker em loop com long polling | aceita |
| [0022](0022-field-snapshot-recalculado-por-talhao.md) | `read.field_snapshot` recalculado por talhão a partir de `core` | aceita |
| [0023](0023-redrive-nativo-da-dlq.md) | Redrive da DLQ com o recurso nativo do SQS | aceita |
| [0024](0024-regras-da-janela-de-pulverizacao.md) | Regras da janela de pulverização: perfis por cultura com ajustes e níveis de alerta | aceita |
| [0025](0025-previsao-de-7-dias.md) | Previsão de 7 dias, sugestão de horário só até 72 h | aceita |
| [0026](0026-cadastro-de-produtores-e-talhoes.md) | Cadastro de produtores, contatos, propriedades e talhões no banco | aceita |

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
