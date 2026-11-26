# 0026. Cadastro de produtores, contatos, propriedades e talhões no banco

- **Status:** aceita (substitui o talhão fixo do `.env` do ADR-0018 e o `FIELD_TIMEZONE` do ADR-0024)
- **Data:** 2026-11-26

## Contexto
Até a Fase 3, o talhão era fixo no `.env` (`FIELD_TENANT_ID=caliman`, `FIELD_ID=sede`, coordenada e fuso). Isso deixou de servir:
- **O nome não identifica.** Há outros produtores Caliman na região, e dois tenants com o mesmo texto misturariam dados e chaves de idempotência.
- **A "sede" é uma propriedade, não um talhão.** Ela tem 50 ha e várias culturas, das quais 36 ha são de café. Talhão é a unidade de manejo com uma cultura.
- **A regra da Fase 3 precisa de dados do cadastro:** cultura, região, fuso e o que o produtor tolera em cada cultura (ADR-0024).
- **A Fase 4 vai identificar quem escreve pelo celular** (o `wa_id` do WhatsApp), e uma fazenda tem mais de uma pessoa falando com o sistema.

## Decisão
Migration `V0007`, tudo em `core`, sem API de cadastro. As linhas entram à mão, com SQL fora do git, porque o repositório é público.

| Tabela | O que é | Chave | Colunas |
|---|---|---|---|
| `producers` | produtor ou fazenda (o **tenant**) | `id` UUID (`uuidv7()`) | `name` só para mostrar, pode repetir |
| `producer_contacts` | quem fala com o sistema | `id`; `phone` **UNIQUE** | `producer_id`, `name`, `phone` em E.164 (`CHECK`) |
| `producer_crops` | o que o produtor tolera por cultura | `(producer_id, crop)` | `temperature_tolerable_max_c` |
| `farms` | propriedade | `id` UUID | `producer_id`, `name`, `region` (UF), `timezone` (IANA), `total_area_ha` |
| `fields` | talhão, com uma cultura | `(producer_id, field_id)` | `farm_id`, `name`, `crop`, `area_ha`, `latitude`, `longitude` |

- **O `tenant_id` das tabelas `raw`, `core` e `read` passa a ser o UUID do produtor**, em texto. As colunas não mudam, e nenhuma migration aplicada é editada. Os dados de dev antigos (`caliman`) são descartados com `docker compose down -v`.
- **O celular é único, mas não é id.** Número muda e é reciclado, e uma fazenda tem várias pessoas. Ele é o dado de login e de WhatsApp de um **contato**, ligado a um produtor. Login de verdade (código enviado pelo WhatsApp) fica para depois.
- **A tolerância fica por produtor e cultura**, não por talhão. É uma decisão do produtor para o café, não para um pedaço de terra.
- **A coordenada fica no talhão**, e a coleta de previsão continua uma por talhão, com a mesma chave do ADR-0018. O fuso e a região vêm da propriedade.
- **O banco garante:**
  - celular único em E.164;
  - fuso que o Postgres reconhece (o próprio `AT TIME ZONE` falha no insert);
  - UF com duas letras maiúsculas;
  - latitude e longitude na faixa válida;
  - `field_id` em minúsculas, sem `:`, porque ele entra nas chaves de idempotência;
  - talhão só numa propriedade do mesmo produtor (FK composta `(farm_id, producer_id)`).
- **O poller lê os talhões de `core.fields`** e coleta cada um. A falha de um talhão (API fora, por exemplo) não impede os outros, e o processo termina com código 1 se algum falhar. As variáveis `FIELD_*` saem do `.env`.
- `crop` é texto livre. A regra falha na hora para cultura sem perfil (ADR-0024), e uma cultura nova não exige migration.

## Consequências
- Homônimos não se misturam, e um produtor novo é um `INSERT`, não um deploy.
- Vários talhões funcionam sem mudança de código. Talhões na mesma propriedade fazem chamadas quase iguais à Open-Meteo; dá para agrupar por coordenada quando o número crescer.
- A coordenada real sai do `.env` e fica só no banco local. Nada pessoal (nome, celular, coordenada) vai para o git.
- **Ainda não há FK de `tenant_id`/`field_id` para o cadastro** nas tabelas de eventos. O `raw` guarda o que chegou, como manda o ADR-0002, e o webhook ainda aceita talhão não cadastrado. Validar o talhão no worker (evento de talhão desconhecido → `rejected`) entra junto com o agendamento com produto.
- Sem API, o cadastro é trabalho manual. Serve para um produtor; com mais, vira uma tela ou um fluxo no WhatsApp.

## Alternativas consideradas
- **PK `(producer_id, field_id, crop)`**, com várias culturas por talhão: o agendamento precisaria dizer a cultura, e a área por cultura deixaria de somar na propriedade.
- **Celular como id do produtor:** número muda e é reciclado, a fazenda tem várias pessoas, e é dado pessoal que iria parar em chaves, logs e mensagens de fila.
- **Celular direto em `producers`:** mais simples, mas um número só por produtor.
- **Tolerância como lista genérica de ajustes em JSONB:** aceita qualquer ajuste sem migration, mas sem validação. A coluna explícita é suficiente enquanto o produtor só decide o calor.
- **Coordenada na propriedade:** uma coleta por propriedade, mas exigiria trocar `field_id` por propriedade nas tabelas de previsão.
- **Cadastro por seed em migration:** os dados do produtor iriam para o repositório público.
