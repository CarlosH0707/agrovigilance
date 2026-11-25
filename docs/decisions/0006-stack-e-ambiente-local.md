# 0006. Stack e ambiente local

- **Status:** proposta (pendências abaixo)
- **Data:** 2026-11-24

## Contexto
O ambiente local precisa subir com um comando e imitar os serviços AWS usados (SQS) sem custo.

## Decisão (proposta)
- Python 3.12+ com `uv`; FastAPI para o webhook; `pytest`.
- PostgreSQL na versão estável mais recente, via Docker Compose.
- Emulador de SQS local via Docker Compose. Candidato: **Floci** (sugerido como substituto do LocalStack Community).

## Pendências antes de aceitar
- [ ] Confirmar a versão estável atual do PostgreSQL (a sugestão de usar 18/19 veio do Gemini e não foi verificada).
- [ ] Confirmar a situação do LocalStack Community e se o Floci suporta DLQ e redrive. Se não suportar, avaliar alternativas (ex.: ElasticMQ).
- [ ] Instalar `uv` e Docker no WSL (hoje nenhum dos dois está instalado).

## Consequências
- Tudo roda local, sem conta AWS na fase de desenvolvimento.
- Paridade com a AWS depende do emulador; testes de DLQ precisam rodar contra ele.
