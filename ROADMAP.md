# Roadmap

Ritmo: **45–60 min por semana** (quartas). Cada item cabe em uma sessão. Uma fase só começa quando a anterior cumpre o critério de pronto.

## Fase 0 — Documentação ✅ concluída

- [x] README, AGENTS, ARCHITECTURE, ROADMAP
- [x] ADRs iniciais (0001–0011)
- [x] Confirmar a versão do PostgreSQL (19) e o suporte do Floci a DLQ/redrive (ADR-0006)
- [x] Padrão de migrations (ADR-0009)
- [x] Schemas do banco e nomes das tabelas raw (ADR-0010)
- [x] Python 3.14, `uv` e `pytest` (ADR-0011)

## Fase 1 — Setup e ingestão idempotente

**Pronto quando:** o mesmo evento enviado duas vezes gera uma linha na tabela raw e uma mensagem na fila, e a lógica tem testes unitários passando (e de integração onde só o banco garante, ADR-0014).

- [x] Esqueleto Python 3.14 com `uv`, `pytest` e `src/agrovigilance/`
- [x] Instalar Docker Engine e `uv` no WSL
- [x] Docker Compose com Postgres 19 + Floci subindo e respondendo
- [x] Migrations: schemas `raw`/`core`/`read`, `raw.open_meteo_events`, `raw.field_events` (runner próprio, ADR-0013)
- [x] Testes de integração com testcontainers (ADR-0014)
- [x] Filas `agrovigilance-events` e `agrovigilance-events-dlq` (`maxReceiveCount=3`), com teste de integração contra o Floci (ADR-0015)
- [x] `POST /webhooks/field` com idempotência, publicação na fila e teste de integração (ADR-0016, ADR-0017)
- [x] Ingestão Open-Meteo para um talhão fixo (ADR-0018)
- [x] Testes unitários das chaves de idempotência e do fluxo de ingestão (com fakes)
- [ ] Conferência manual do envio duplicado (webhook e Open-Meteo)

## Fase 2 — Processamento e read model

**Pronto quando:** um worker consome a fila e `field_snapshot` reflete o último estado do talhão; mensagem que falha 3x cai na DLQ.

- [ ] Canonical payload (formato interno único por tipo de evento)
- [ ] Worker consumidor idempotente
- [ ] `field_snapshot` por talhão (ADR do esquema)
- [ ] Teste de DLQ e redrive

## Fase 3 — Harness e alertas

**Pronto quando:** a regra de janela de pulverização gera um alerta no console, sem repetir o mesmo alerta dentro da janela de anti-spam.

- [ ] Regras determinísticas da janela de pulverização (limites em ADR)
- [ ] Anti-spam / deduplicação de alertas
- [ ] `ConsoleChannel`
- [ ] Agente LLM com uma consulta ao snapshot, saída Pydantic e evals

## Fase 4 — WhatsApp e cotações

- [ ] `WhatsAppChannel` (Cloud API oficial, medir custo dos alertas proativos)
- [ ] Cotações de soja/milho
- [ ] Risco de colheita/tráfego no talhão

## Depois (sem data)

- Outbox transacional
- Deploy em nuvem com custo mensal medido
- Mais de um produtor
