# 0013. Migrations no padrão de nomes do Flyway, aplicadas por um runner próprio

- **Status:** aceita
- **Data:** 2026-11-25
- **Substitui:** o padrão de nomes do [ADR-0009](0009-migrations-versionadas.md) (o resto do 0009 continua valendo)

## Contexto
O ADR-0009 definiu migrations SQL versionadas e imutáveis, no formato `<Numero>__DDL__<nome>.sql`, e deixou a ferramenta que as aplica para a Fase 1. O formato "lembrava" o do Flyway sem ser compatível com ele, e o marcador `DDL` obrigaria a inventar outro formato para migrações de dados.

## Decisão
- **Nome:** padrão do Flyway, `V<versão>__<descrição>.sql`, com versão de 4 dígitos e descrição em snake_case. Ex.: `migrations/V0001__create_schemas.sql`. Migração de dados (DML), quando existir, segue o mesmo padrão.
- **Runner próprio** em `scripts/migrate.py` (psycopg 3), rodado com `uv run --env-file .env python scripts/migrate.py`:
  - aplica as pendentes em ordem de versão, cada uma numa transação junto com o registro em `public.schema_migrations` (`version`, `checksum` sha256, `applied_at`);
  - recusa nome fora do padrão e versão repetida;
  - falha se uma migration aplicada mudou (checksum diferente) ou sumiu do disco, garantindo a imutabilidade do ADR-0009;
  - usa `pg_advisory_lock` para que duas execuções não rodem ao mesmo tempo.
- O runner fica **fora do pacote** (`scripts/`, não `src/agrovigilance/`): é ferramenta de desenvolvimento e operação, o app nunca o importa, e ele depende do layout do repo (`migrations/` na raiz). Critério geral: o que o app usa em execução vai no pacote; ferramenta fica em `scripts/`, com o teste unitário ao lado (ADR-0012).

## Consequências
- ~90 linhas de código nosso, sem imagem nem binário extra; o psycopg já seria necessário para a ingestão.
- Os arquivos são compatíveis com o Flyway: se um dia valer a pena trocar, basta apontá-lo para `migrations/` (a tabela de controle é que muda).
- Não há `down`/rollback: corrigir é criar uma migration nova, como já dizia o ADR-0009.
- Migrations que não podem rodar em transação (ex.: `CREATE INDEX CONCURRENTLY`) não são suportadas; quando aparecer a necessidade, o runner ganha essa opção ou a ferramenta é trocada.

## Alternativas consideradas
- **Flyway:** padrão de mercado, mas traz uma imagem Java para fazer o que ~90 linhas fazem hoje.
- **dbmate:** binário pequeno, mas com formato próprio (timestamp + `-- migrate:up/down`).
- **Manter `NNNN__DDL__nome.sql`:** formato só nosso e sem resposta para DML.
