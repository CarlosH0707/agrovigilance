# 0020. LLM na entrada em texto livre, não na redação do alerta

- **Status:** aceita
- **Data:** 2026-11-25
- **Substitui em parte:** [ADR-0007](0007-harness-deterministico-antes-do-llm.md) (o papel do LLM; o harness continua igual)

## Contexto
O ADR-0007 colocou o LLM depois do harness, só para redigir o alerta. Mas a decisão de alertar já é das regras, e um alerta como "vento de 18 km/h às 10h, adie a pulverização" sai igual de um template, sem custo de token, sem latência e sem risco de o modelo inventar número. Usar LLM onde um template resolve não se justifica para o usuário nem como decisão de design.

O problema que código determinístico não resolve bem é a entrada. No WhatsApp (Fase 4), o produtor não manda JSON com `scheduled_for` em ISO 8601. Ele escreve "vou passar veneno no talhão de cima amanhã cedo", com gíria, apelido de talhão e horário vago.

## Decisão
- **Alerta por template (Fase 3):** o harness (regras + anti-spam) decide, e o texto sai de um template preenchido com os dados do snapshot. Nada de LLM no caminho do alerta.
- **LLM na entrada (Fase 4):** a mensagem em texto livre do WhatsApp é interpretada por um LLM com saída estruturada (Pydantic), que produz um apontamento no mesmo formato do webhook. A partir daí o fluxo é o de sempre: raw idempotente, fila, `from_raw` e `InvalidFieldOperation`. O LLM só extrai, não grava nem decide nada.
- **Dado faltando ou ambíguo** (ex.: "amanhã cedo" sem hora): o sistema pergunta de volta ao produtor em vez de chutar.
- **Perguntas do produtor** ("dá pra pulverizar amanhã?"): o LLM responde com uma única consulta ao `field_snapshot`, e os números da resposta vêm do snapshot, não do modelo.
- **Evals** com mensagens reais do produtor, anonimizadas, medindo a extração campo a campo (tipo, talhão, horário) e a taxa de "perguntou quando devia".

## Consequências
- A Fase 3 fica sem LLM: mais simples, testável só com unitários e de custo zero por alerta.
- O LLM entra onde há ganho concreto, que dá para medir com evals, e a justificativa em entrevista é direta: interpretar linguagem natural do campo, coisa que regra não cobre.
- A conversa de volta (perguntar o que faltou) usa a janela de 24h de mensagens de serviço do WhatsApp, que é gratuita (ADR-0005).
- Um erro de extração vira apontamento errado, e não alerta errado. Por isso a confirmação com o produtor e os evals são obrigatórios.

## Alternativas consideradas
- **LLM redigindo o alerta (ADR-0007 original):** pouco ganho sobre template, com custo, latência e risco de alucinação no texto que o produtor lê.
- **Parser por regex/palavras-chave para o WhatsApp:** funciona para frases fixas, mas quebra com a variação real ("passar veneno", "aplicar", "jogar o produto") e com horário vago.
- **Sem LLM no projeto:** possível, mas o produtor teria que mandar mensagem em formato rígido, o que mata o uso pelo WhatsApp.
