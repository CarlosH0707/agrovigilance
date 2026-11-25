# AgroVigilance

Motor assíncrono 24/7 que cruza **clima**, **cotações de commodities** e **apontamentos de manejo no campo** para mandar alertas úteis ao produtor, de preferência pelo WhatsApp.

> Projeto pessoal e laboratório de System Design: ingestão idempotente, arquitetura orientada a eventos, CQRS e um agente de IA com guardrails determinísticos.

## Por que existe

Quem toca uma lavoura olha dez telas diferentes para decidir se dá para pulverizar hoje ou se o talhão aguenta máquina. O AgroVigilance junta essas fontes, avisa só quando há risco real e não repete o mesmo alerta toda hora.

## Casos de uso do MVP

1. **Janela de pulverização:** previsão horária (temperatura, umidade, chance de chuva, vento) × pulverização agendada. Alerta se as condições saírem da faixa.
2. **Risco de colheita ou tráfego no talhão:** chuva acumulada ou umidade alta.
3. **Cotações** (soja/milho): entram depois do núcleo estar estável.

## Estado atual

✅ **Fase 0 (documentação) concluída.** 🚧 **Fase 1** em andamento: setup e migrations prontos (Python + Postgres 19 + Floci, schemas e tabelas raw); falta a ingestão idempotente. Veja o [ROADMAP](ROADMAP.md).

## Documentação

| Arquivo | Conteúdo |
|---|---|
| [ARCHITECTURE.md](ARCHITECTURE.md) | Componentes, fluxo de dados, modelo de dados, domínio |
| [ROADMAP.md](ROADMAP.md) | Fases, entregas e critérios de pronto |
| [AGENTS.md](AGENTS.md) | Regras para agentes de IA (e humanos) que trabalham no repo |
| [docs/decisions/](docs/decisions/) | Registro de decisões de arquitetura (ADRs) |

## Stack prevista

Python 3.14 · `uv` · `pytest` · testcontainers · psycopg 3 · FastAPI · PostgreSQL 19 · SQS (Floci em dev) · Docker Compose. Detalhes em [ADR-0006](docs/decisions/0006-stack-e-ambiente-local.md) e [ADR-0011](docs/decisions/0011-python-uv-e-testes.md).

## Como rodar

Pré-requisitos: Docker Engine com Compose e [`uv`](https://docs.astral.sh/uv/).

```bash
cp .env.example .env        # ajuste se quiser; o .env fica fora do git
docker compose up -d --wait # Postgres 19 (porta 5432) e Floci/SQS (porta 4566)
uv run --env-file .env python scripts/migrate.py  # aplica as migrations pendentes
uv run pytest                  # testes unitários (não precisam do Docker)
uv run pytest -m integration   # testes de integração (sobem um Postgres descartável via testcontainers)
```

Testes unitários ficam ao lado do módulo que testam (`foo.py` → `foo_test.py`); `tests/` guarda só config compartilhada e o smoke test ([ADR-0012](docs/decisions/0012-testes-ao-lado-do-codigo.md)).

Para parar: `docker compose down` (os dados do Postgres ficam no volume `pgdata`; `down -v` apaga).
