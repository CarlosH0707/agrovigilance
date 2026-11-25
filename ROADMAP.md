# Roadmap

Ritmo: **45–60 min por semana** (quartas). Cada item cabe em uma sessão. Uma fase só começa quando a anterior cumpre o critério de pronto.

## Fase 0 — Documentação ✅ em andamento

- [x] README, AGENTS, ARCHITECTURE, ROADMAP
- [x] ADRs iniciais (0001–0008)
- [ ] Confirmar a versão estável atual do PostgreSQL
- [ ] Confirmar se o emulador AWS escolhido suporta DLQ e redrive (ver ADR-0006)

## Fase 1 — Setup e ingestão idempotente

**Pronto quando:** o mesmo evento enviado duas vezes gera uma linha em `raw_events` e uma mensagem na fila.

- [ ] Esqueleto Python com `uv`, `pytest` e `src/agrovigilance/`
- [ ] Docker Compose com Postgres + emulador de SQS subindo e respondendo
- [ ] Migration de `raw_events`
- [ ] Filas `agrovigilance-events` e `agrovigilance-events-dlq` (`maxReceiveCount=3`)
- [ ] `POST /webhooks/field` com idempotência
- [ ] Ingestão Open-Meteo para um talhão fixo
- [ ] Teste de envio duplicado (webhook e Open-Meteo)

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
