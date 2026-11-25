# 0015. Filas criadas por script idempotente e testadas contra o Floci

- **Status:** aceita
- **Data:** 2026-11-25
- **Antecipa:** os "testes de integração contra o Floci" que o ROADMAP deixava para depois

## Contexto
A fila `agrovigilance-events` e a DLQ `agrovigilance-events-dlq` ([ADR-0003](0003-sqs-standard-com-dlq.md)) precisam existir antes da ingestão publicar nelas. O Floci guarda tudo em memória: as filas somem quando o container reinicia. E o redrive para a DLQ só se prova num SQS de verdade.

## Decisão
- As filas são criadas por `scripts/create_queues.py` (ferramenta fora do pacote, como o `migrate.py` do [ADR-0013](0013-migrations-no-padrao-flyway-com-runner-proprio.md)): cria a DLQ, lê o ARN dela e cria a fila principal com `RedrivePolicy` (`maxReceiveCount=3`). Como o `CreateQueue` é idempotente, pode rodar quantas vezes precisar. Em dev, roda depois de cada `docker compose up`.
- Cliente SQS: **boto3**, que também será usado pela ingestão para publicar. Ele lê `AWS_ENDPOINT_URL` do ambiente, então o mesmo código serve para o Floci e para a AWS.
- Testes de integração também sobem um **Floci descartável** (`floci/floci:2.5.0`) via testcontainers, como o Postgres do [ADR-0014](0014-testes-de-integracao-com-testcontainers.md). Eles provam que o script é idempotente e que uma mensagem recebida 3 vezes sem ser apagada cai na DLQ.

## Consequências
- Ambiente de dev reproduzível com dois comandos (`migrate.py` e `create_queues.py`).
- Esquecer de rodar o script depois de reiniciar o Floci quebra a publicação com `QueueDoesNotExist` (erro claro).
- boto3 é síncrono: se o worker precisar de I/O assíncrono, revisar (aiobotocore).
- Mais uma imagem baixada na primeira execução da integração.

## Alternativas consideradas
- **Script de init do próprio Floci:** cria as filas sozinho no boot, mas amarra a definição ao emulador e não serve para a AWS de verdade.
- **AWS CLI em container:** sem código Python, mas mais uma imagem e lógica de ARN em shell.
- **aiobotocore:** assíncrono, porém mais complexo; ainda não há consumidor que precise disso.
- **Terraform/CloudFormation:** pesado demais antes da fase de deploy.
