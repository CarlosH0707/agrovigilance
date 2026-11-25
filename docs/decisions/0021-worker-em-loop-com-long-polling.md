# 0021. Worker em loop com long polling

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
A Fase 2 precisa de um consumidor da fila `agrovigilance-events` que leve cada evento do raw para o formato canônico em `core` (ADR-0019). O poller da Open-Meteo roda uma vez por execução (ADR-0018), porque a previsão muda de hora em hora. A fila é diferente: os eventos chegam quando acontecem, e o webhook não deveria esperar minutos para ser processado.

## Decisão
- **Processo em loop** (`entrypoints/worker.py`) com long polling: `receive_message` com `WaitTimeSeconds=20` e até 10 mensagens por vez. Na prática, a latência é de segundos.
- **Miolo separado do loop:** `process_once()` faz um ciclo (recebe, processa e apaga). É o que os testes chamam, e `main()` só repete esse ciclo até receber SIGTERM/SIGINT. O pior caso para encerrar é o tempo de um long polling.
- **Falhar é não apagar:** a mensagem só é apagada depois que o processamento deu certo. Se houver erro inesperado (banco fora, bug, mensagem malformada), ela volta após o visibility timeout e, no 3º recebimento, vai para a DLQ (ADR-0003). Evento inválido (`InvalidFieldOperation`) é marcado `rejected` e apagado (ADR-0019).
- **Idempotência sem transação entre tabelas:** o worker grava no core (`ON CONFLICT (raw_event_id) DO NOTHING`) e depois marca o status do raw. Se cair entre os dois passos, a mensagem volta, o insert não faz nada e o status é marcado. Mensagem entregue duas vezes pela SQS Standard cai no mesmo caso.
- **Conexão com o banco por ciclo com mensagens:** se o banco cair e voltar, o próximo ciclo se recupera sem reiniciar o processo.
- **Mensagem validada com Pydantic** (`EventMessage`: `source` + `event_id`); os outros campos da mensagem fina são ignorados.
- **Código:** `infrastructure/queues/events/consumer.py` ao lado do publisher; `domain/raw_event.py` é a linha do raw que os repositórios devolvem, porque `infrastructure` não importa `application` (ADR-0017).

## Consequências
- O webhook vira dado canônico em segundos, e a fila funciona como fluxo de eventos, não como lote.
- Um processo fica rodando. O long polling quase não gasta CPU nem chamadas, mas em produção ele precisa de um supervisor (container, systemd), decidido junto com o deploy.
- Um processo só, mensagens em sequência. Concorrência fica para quando o volume pedir.
- A ordem entre mensagens não é garantida (SQS Standard). O `core` guarda todas as coletas, e quem decide a mais recente é o `read.field_snapshot`, pelo `fetched_at`.

## Alternativas consideradas
- **Uma execução por chamada (cron), como o poller:** mais simples, mas a latência vira o intervalo do cron e a fila vira lote.
- **Lambda com gatilho SQS:** sem processo para manter, mas é decisão de deploy (fase "Depois"), e não verifiquei se o Floci emula o gatilho. O miolo (`handle` + casos de uso) serve de handler se um dia for o caminho.
- **Transação única core + raw:** exigiria uma unidade de trabalho entre repositórios. A idempotência já cobre a queda no meio, sem essa camada.
