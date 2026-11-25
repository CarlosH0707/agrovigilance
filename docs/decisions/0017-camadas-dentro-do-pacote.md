# 0017. Código organizado em camadas dentro do pacote

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
Com o primeiro caso de uso (ingestão do webhook), o código passou a misturar regra de domínio, acesso a banco, fila e HTTP. Juntar tudo em `src/agrovigilance/` não separa nada e dificulta testar a regra sem IO.

## Decisão
`src/agrovigilance/` fica só como raiz de import, dividida em camadas:

| Pasta | O que tem | Pode importar |
|---|---|---|
| `domain/` | Regras puras, sem IO (ex.: `FieldEvent`, `idempotency_key`) | só bibliotecas (Pydantic, stdlib) |
| `application/` | Casos de uso e as portas que eles precisam (`Protocol`) | `domain` |
| `infrastructure/` | Adaptadores de IO que implementam as portas (Postgres, SQS) | `domain` |
| `entrypoints/` | Por onde o mundo entra: API HTTP; depois worker e poller | todas |

Dentro de `infrastructure/`, cada recurso tem a sua pasta, porque vão crescer:

```
infrastructure/
  database/
    connection.py              conninfo_from_env
    <schema>/<tabela>/         uma pasta por tabela (ex.: raw/field_events/)
      repository.py            o repositório da tabela
      queries/<query>.sql      uma query por arquivo, lida pelo repositório
  queues/
    <fila>/publisher.py        um publisher por fila (ex.: events/ → agrovigilance-events)
```

SQL em arquivo próprio fica legível, com destaque de sintaxe, e pode ser copiado direto para o `psql`. O nome da fila mora no publisher dela; `scripts/create_queues.py` importa de lá.

`entrypoints` monta tudo (liga as portas aos adaptadores). Ferramentas de dev continuam em `scripts/` e podem importar do pacote; o pacote nunca importa de `scripts/`. Testes unitários continuam ao lado do módulo ([ADR-0012](0012-testes-ao-lado-do-codigo.md)).

## Consequências
- Regra de domínio e caso de uso testáveis com fakes, sem banco nem fila.
- Trocar SQS ou Postgres mexe só em `infrastructure/`.
- Mais pastas para um projeto pequeno; vale porque o objetivo é treinar System Design.
- `conninfo_from_env` saiu de `scripts/migrate.py` e foi para `infrastructure/database/connection.py`.
- Os `.sql` vão no pacote (o `uv_build` inclui arquivos que não são Python).

## Alternativas consideradas
- Camadas direto em `src/` (sem `agrovigilance/`): cria pacotes top-level genéricos (`import domain`) que podem colidir com bibliotecas instaladas e exige configuração extra no `uv_build`.
- Nomes `cmd` (convenção de Go) ou `handlers` (sugere só HTTP) para os pontos de entrada: `entrypoints` cobre API, worker e CLI.
