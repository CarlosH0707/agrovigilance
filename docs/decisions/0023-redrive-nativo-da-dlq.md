# 0023. Redrive da DLQ com o recurso nativo do SQS

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
O ADR-0003 manda para a DLQ a mensagem que falha 3 vezes, mas não diz como ela volta depois que a causa é corrigida (banco que voltou, bug consertado). Sem um caminho de volta, a DLQ vira cemitério. Além disso, o `main()` do worker deixava escapar a falha de conexão com o banco e derrubava o processo, o que contradiz o ADR-0021 ("o próximo ciclo se recupera sozinho").

## Decisão
- **Redrive nativo** (`StartMessageMoveTask`) em `scripts/redrive_dlq.py`, ferramenta de operação fora do pacote, como `create_queues.py`. Sem `DestinationArn`: cada mensagem volta para a fila de onde caiu. O script espera a task terminar e diz quantas mensagens moveu.
- **Redrive manual, por pessoa:** roda depois de entender e corrigir a causa. Nada de redrive automático, que só repetiria a falha em loop.
- **Worker não morre com erro de infraestrutura:** o loop do `main()` captura a exceção do ciclo, registra no log, espera 5 s e tenta de novo. A mensagem não apagada volta sozinha e, na 3ª vez, vai para a DLQ.
- **Teste de integração** (`tests/integration/dlq_redrive_integration_test.py`) contra o Floci e o Postgres descartáveis: banco fora → 3 falhas → DLQ → banco volta → redrive → `processed` no raw e uma linha no core. Conferi antes que o Floci 2.5.0 implementa `StartMessageMoveTask` e `ListMessageMoveTasks`.

## Consequências
- Recuperar de uma queda é um comando só, e o mesmo script funciona na AWS.
- Mensagem reprocessada depois do redrive passa pela idempotência do worker (ADR-0021): se parte já tinha sido gravada, não duplica.
- Mensagem envenenada de verdade (bug ainda não corrigido) volta para a DLQ depois de mais 3 falhas. Quem roda o redrive precisa olhar o log antes.
- Não há alerta de DLQ com mensagens ainda; fica para o deploy (métrica `ApproximateNumberOfMessagesVisible` da DLQ).

## Alternativas consideradas
- **Redrive manual com receive/send/delete:** funciona em qualquer emulador, mas reimplementa o que o SQS já faz e perde a origem da mensagem.
- **Redrive pelo console da AWS:** não existe em dev e não é testável.
- **Reprocessar direto do raw (status `received` antigo):** possível no futuro, mas é outro mecanismo; a DLQ já guarda exatamente o que falhou.
