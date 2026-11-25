# 0009. Toda mudança de tabela é uma migration versionada

- **Status:** aceita (nomes substituídos pelo ADR-0013)
- **Data:** 2026-11-24
- **Nota:** o padrão de nomes abaixo foi substituído pelo padrão do Flyway (`V0001__nome.sql`) e a ferramenta foi escolhida no [ADR-0013](0013-migrations-no-padrao-flyway-com-runner-proprio.md). O resto continua valendo.

## Contexto
O esquema do banco vai evoluir semana a semana. Sem um registro ordenado, não dá para recriar o banco do zero nem saber o que mudou e quando.

## Decisão
- Toda mudança de estrutura no Postgres (schemas, tabelas, colunas, índices, constraints) vira um arquivo SQL em `migrations/`.
- Nome: `<Numero>__DDL__<nome_da_migration>.sql`, com número de 4 dígitos e nome em snake_case. Ex.: `0001__DDL__create_schemas.sql`.
- Migrations são **imutáveis** depois de aplicadas: corrigir algo é criar uma migration nova.
- Nada de mudar o esquema à mão no banco.
- A ferramenta que aplica as migrations será escolhida na Fase 1 (o formato lembra o do Flyway).

## Consequências
- O banco pode ser recriado do zero aplicando as migrations em ordem.
- O histórico do esquema fica legível no repo.
- Se surgir necessidade de migração de dados (DML), o formato será decidido em um ADR novo.
