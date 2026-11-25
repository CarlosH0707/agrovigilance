# 0022. `read.field_snapshot` recalculado por talhão a partir de `core`

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
A Fase 2 fecha com um read model por talhão (ADR-0010) que as regras da Fase 3 vão ler numa consulta só. O worker processa uma mensagem por vez, mas a SQS Standard não garante ordem e pode entregar duas vezes (ADR-0003, ADR-0021). Uma coleta antiga da Open-Meteo pode chegar depois de uma nova, e o snapshot não pode voltar no tempo.

## Decisão
- **Tabela `read.field_snapshot`**, uma linha por `(tenant_id, field_id)`:
  - `forecast` (JSONB): as próximas horas (`target_hour >= hora atual`), ordenadas, com a coleta de maior `fetched_at` de cada hora.
  - `scheduled_spraying_for`: o `scheduled_for` do último `pulverizacao_agendada`, enquanto não houver `pulverizacao_concluida` apontada depois dele.
  - `last_operation_type` e `last_operation_at`: o apontamento mais recente.
  - `updated_at`.
- **Recalcular em vez de aplicar o evento:** depois de gravar no core e antes de marcar o raw, o worker chama `refresh(tenant_id, field_id)`. É um único `INSERT ... SELECT ... ON CONFLICT DO UPDATE` que monta a linha inteira lendo `core`. O resultado só depende do que está no core, então ordem de chegada e reentrega não mudam nada.
- Se o worker cair entre o core e o refresh, a mensagem volta, o insert no core não faz nada e o refresh roda de novo. Evento `rejected` não chama o refresh.
- **Reconstruir** o read model é rodar o `refresh` para cada talhão. Não há script para isso ainda, porque não houve necessidade.
- JSONB no `forecast` é aceitável aqui porque é modelo de leitura: a regra recebe tudo numa linha. O core continua tipado (ADR-0019).

## Consequências
- O snapshot fica consistente com o core depois de cada mensagem, sem lógica de "esse evento é mais novo?" no código.
- Cada mensagem relê o talhão inteiro (2 dias × 24 h de previsão + poucos apontamentos), o que é barato no volume atual.
- Hora passada só sai do `forecast` no próximo refresh. A regra da Fase 3 ainda precisa filtrar pelo horário atual.
- **Limite de concorrência:** com dois workers, um refresh que leu o core antes pode gravar depois de um mais novo. Com um processo só (ADR-0021) isso não acontece. Quando houver concorrência, a saída é travar a linha do talhão (`pg_advisory_xact_lock`) ou rodar o refresh numa transação `SERIALIZABLE`.

## Alternativas consideradas
- **Atualização incremental por evento** (aplicar só a mudança na linha): menos leitura, mas cada tipo de evento precisaria comparar `fetched_at`/`occurred_at` com o que já está lá para não regredir com mensagem fora de ordem, e o rebuild seria outro código.
- **`MATERIALIZED VIEW`:** mesma consulta, mas o `REFRESH` recalcula todos os talhões de uma vez e não por talhão.
- **`VIEW` simples:** sempre atual e sem worker, mas o cálculo roda a cada leitura e não existe um read model persistido para mostrar o CQRS.
