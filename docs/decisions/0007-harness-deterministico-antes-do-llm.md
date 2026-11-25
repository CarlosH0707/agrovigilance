# 0007. Harness determinístico antes do LLM

- **Status:** aceita, com o papel do LLM substituído pelo [ADR-0020](0020-llm-na-entrada-e-nao-no-alerta.md) (o alerta sai de template; o LLM interpreta a entrada em texto livre)
- **Data:** 2026-11-24

## Contexto
Chamar um LLM para cada evento é caro, lento e imprevisível. Alertas repetidos irritam o produtor e, no WhatsApp, custam dinheiro.

## Decisão
Antes de qualquer LLM, um harness determinístico decide se há algo a alertar: regras de domínio (ex.: janela de pulverização) e anti-spam (não repetir o mesmo alerta dentro de uma janela). Só passando por ele o agente é chamado, com **uma única consulta** ao `field_snapshot`, saída estruturada via Pydantic e evals.

## Consequências
- Custo de tokens e de mensagens sob controle.
- A decisão de alertar é testável e explicável; o LLM só redige.
- O sistema funciona sem LLM (alerta em texto fixo), o que facilita a Fase 3.

## Alternativas consideradas
- Agente com ferramentas livres decidindo tudo: mais flexível, mas caro, difícil de testar e propenso a spam.
