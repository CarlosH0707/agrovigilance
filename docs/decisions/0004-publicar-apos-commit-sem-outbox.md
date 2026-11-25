# 0004. Publicar na fila após o commit, sem outbox por enquanto

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
Gravar no banco e publicar na fila são duas operações sem transação comum (dual write). Se o processo cair entre as duas, o evento fica gravado mas nunca é processado.

## Decisão
No MVP, publicar logo depois do commit. A coluna `status` em `raw_events` permite achar eventos que ficaram sem publicar. Outbox transacional fica como evolução planejada.

## Consequências
- Implementação simples para a Fase 1.
- Risco conhecido e aceito: perda de publicação se o processo cair entre commit e publish. Mitigação: varredura por `status` pendente.
- A migração para outbox depois é um bom exercício e deve virar um ADR que substitui este.

## Alternativas consideradas
- Outbox desde o início: correto, mas atrasa a primeira entrega funcionando.
- Publicar antes do commit: pode publicar evento que nunca foi gravado.
