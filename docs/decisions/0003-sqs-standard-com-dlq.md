# 0003. SQS Standard + DLQ, idempotência na aplicação

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
A ingestão precisa ser desacoplada do processamento, e mensagens que falham repetidamente não podem travar a fila.

## Decisão
Fila SQS Standard `agrovigilance-events` com mensagens finas (`event_id` + metadados). Redrive para `agrovigilance-events-dlq` com `maxReceiveCount=3`. Duplicatas e ordem são tratadas pela aplicação (ADR-0002 e consumidores idempotentes).

## Consequências
- Throughput sem limite prático e custo baixo.
- Consumidores precisam ser idempotentes: a Standard pode entregar mais de uma vez e fora de ordem.
- Mensagem fina obriga o worker a ler o evento no banco, mas evita payload duplicado e limite de tamanho.

## Alternativas consideradas
- SQS FIFO: deduplicação nativa só dentro de 5 minutos e throughput limitado; não elimina a necessidade de idempotência.
- Kafka/Redpanda: operação pesada demais para o volume do projeto.
