# 0005. Canal de notificação como adaptador (Console → WhatsApp)

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
O destino final dos alertas é o WhatsApp, mas a integração oficial exige conta de desenvolvedor, verificação e templates pagos para mensagens proativas. Isso não pode travar o núcleo do sistema.

## Decisão
Os alertas saem por uma interface de canal. Começamos com `ConsoleChannel`; `WhatsAppChannel` entra na Fase 4 usando a **Cloud API oficial da Meta**.

## Consequências
- Núcleo testável sem dependência externa.
- Mensagens de serviço (janela de 24h após o usuário escrever) têm cota gratuita; alertas proativos usam templates e são pagos, então o anti-spam (ADR-0007) também é controle de custo.

## Alternativas consideradas
- APIs não oficiais (Evolution API, Baileys): sem custo de licença, mas com risco de banimento do número.
