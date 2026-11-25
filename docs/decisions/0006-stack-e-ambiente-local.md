# 0006. Infraestrutura local: Postgres 19 e Floci no Docker do WSL

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
O ambiente local precisa subir com um comando, imitar a AWS (SQS) sem custo e usar o mesmo banco que a produção usará.

## Decisão
- **PostgreSQL 19** (estável desde 19/11/2026), com a tag da imagem fixada em `postgres:19.x`, nunca `latest`.
- **Floci** como emulador de SQS. Suporta DLQ e redrive pela API da AWS (`StartMessageMoveTask`/`ListMessageMoveTasks`).
- Os dois sobem pelo mesmo `docker-compose.yml`, rodando no **Docker Engine instalado no próprio WSL** (não Docker Desktop).
- Dados do Postgres em **volume nomeado** do Docker (no disco do Linux, nunca em `/mnt/c`). Eles sobrevivem a recriar o container e só somem com `docker compose down -v`.
- **Produção:** fica para a fase de deploy. Opções na mesa: Postgres gerenciado (Neon, Supabase, RDS) ou VPS com o mesmo compose.

Versão do Python e ferramentas de Python ficam em um ADR separado.

## Consequências
- Mesmo banco em desenvolvimento e produção: sem surpresas de SQL ou concorrência.
- O Postgres 19 tem `ON CONFLICT DO SELECT`, útil para a ingestão idempotente.
- A 19 é muito nova: alguns serviços gerenciados podem ainda não oferecê-la quando chegar a hora do deploy.
- Paridade com a AWS depende do Floci; os testes de DLQ rodam contra ele.

## Alternativas consideradas
- **LocalStack:** a Community Edition foi descontinuada em 23/03/2026; agora exige conta e token, e o plano gratuito é só para uso não comercial.
- **ElasticMQ:** só SQS, maduro. Fica como plano B se o Floci falhar.
- **SQLite em dev:** sem JSONB/GIN e sem escrita concorrente; divergiria da produção.
- **Docker Desktop:** funciona, mas é mais pesado e não traz nada que o projeto precise.
- **Banco gerenciado já em dev:** depende de internet e de limites do plano gratuito, e o Floci precisaria de Docker de qualquer forma.
