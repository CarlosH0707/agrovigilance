# 0008. Fluxo de branches: nada de commit direto na `main`

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
O projeto é pessoal e, por enquanto, só uma pessoa mexe nele. Mesmo assim, a `main` deve ficar sempre estável e o histórico deve mostrar cada task como uma unidade, como num time de verdade.

## Decisão
A partir da **Fase 1**, nenhum commit vai direto na `main`.

1. Cada task começa numa branch criada a partir da `main` atualizada:
   - `feature/<descricao-curta>` para funcionalidade ou mudança de código/docs;
   - `release/<versao-ou-marco>` para fechar e preparar uma entrega.
2. Durante o dia de trabalho, os commits são feitos na branch, pequenos e frequentes.
3. No fim da task, a branch é integrada na `main` com `git merge --no-ff` (mantém um commit de merge que marca a task) e depois apagada.

A Fase 0 (documentação inicial) foi feita direto na `main`.

## Consequências
- A `main` só recebe trabalho terminado.
- O histórico agrupa os commits de cada task.
- Um passo a mais por task (criar a branch e fazer o merge).

## Alternativas consideradas
- Commits direto na `main`: mais rápido, mas mistura trabalho pela metade com trabalho pronto.
- Pull request no GitHub para cada task: dá mais visibilidade no portfólio, mas é cerimônia demais sem revisor. Pode substituir este ADR mais tarde.
