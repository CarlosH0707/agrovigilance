# 0002. Idempotência na ingestão com chave única e `ON CONFLICT DO NOTHING`

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
Webhooks são reenviados, polls se sobrepõem e a fila entrega pelo menos uma vez. Sem idempotência, o mesmo evento vira alertas duplicados para o produtor.

## Decisão
Cada evento recebe uma `idempotency_key` determinística (ver ARCHITECTURE.md) com restrição UNIQUE em `raw_events`. A gravação usa `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING RETURNING id`; sem `id` de volta, é duplicata e nada é publicado. O payload bruto é guardado em `JSONB`.

## Consequências
- Deduplicação atômica feita pelo banco, sem lock nem leitura prévia.
- Payload bruto permite reprocessar quando a normalização mudar.
- Correções de um evento não sobrescrevem o original: chegam como uma nova versão com chave própria.

## Alternativas consideradas
- `ON CONFLICT DO UPDATE`: apagaria o histórico e esconderia reenvios com conteúdo diferente.
- Checar existência antes de inserir: tem condição de corrida.
