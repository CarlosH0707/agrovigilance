# 0014. Testes de integração com testcontainers

- **Status:** aceita
- **Data:** 2026-11-25
- **Antecipa:** os testes de integração que o [ADR-0011](0011-python-uv-e-testes.md) deixou para depois

## Contexto
O runner de migrations ([ADR-0013](0013-migrations-no-padrao-flyway-com-runner-proprio.md)) e a idempotência por `UNIQUE` + `ON CONFLICT` ([ADR-0002](0002-idempotencia-na-ingestao.md)) só se provam num Postgres de verdade. Conferir à mão no banco de desenvolvimento é lento, não se repete e suja os dados de dev.

## Decisão
- Testes de integração usam **testcontainers** (`testcontainers[postgres]`, grupo `dev`): cada execução sobe um `postgres:19.0` descartável, separado do banco de dev, e o remove no fim.
- Cada teste ganha um banco novo e vazio (`CREATE DATABASE test_<uuid>`) dentro desse container, apagado ao final.
- Ficam em `tests/integration/` com o sufixo `_integration_test.py` e o marcador `integration` (amplia o [ADR-0012](0012-testes-ao-lado-do-codigo.md), que reservava `tests/` para config e smoke test).
- `uv run pytest` continua rodando só os unitários, sem Docker (`-m 'not integration'` no `addopts`). A integração roda com `uv run pytest -m integration`.
- Sem Docker disponível, o teste **falha**; nunca é pulado em silêncio.

## Consequências
- O que só o banco garante passa a ter teste automático e repetível.
- Nada para subir ou derrubar à mão: o container nasce e morre com a execução.
- Exige Docker para rodar a integração e baixa a imagem na primeira vez.
- Uma dependência de desenvolvimento a mais.

## Alternativas consideradas
- **Serviço `postgres-test` no compose com `tmpfs`:** sem dependência nova, mas precisa subir e derrubar à mão e pode ficar rodando esquecido.
- **Usar o banco de dev:** mistura dado de teste com dado de desenvolvimento.
