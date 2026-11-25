# AGENTS.md

Instruções para agentes de IA (Claude Code, Codex, etc.) e para quem mais contribuir. Leia antes de mexer em qualquer coisa.

## Contexto

- Projeto pessoal, tocado em **entregas pequenas de 45–60 min por semana**. Prefira mudanças pequenas e completas a grandes e pela metade.
- O objetivo é aprender e demonstrar System Design. Cada escolha não óbvia precisa de uma justificativa registrada.
- Visão geral em [README.md](README.md), desenho em [ARCHITECTURE.md](ARCHITECTURE.md), o que vem a seguir em [ROADMAP.md](ROADMAP.md).

## Regras de trabalho

1. **Faça o mínimo que resolve a tarefa.** Nada de abstração "para o futuro", dependência nova sem motivo ou camada extra. Biblioteca padrão e recursos nativos primeiro.
2. **Não corte segurança, validação nem testes** da lógica arriscada (idempotência, deduplicação, anti-spam, parsing de payload externo).
3. **Siga o roadmap.** Não adiante fases. Se a tarefa exigir algo de uma fase futura, pergunte.
4. **Commits pequenos**, mensagem em português no imperativo (`adiciona tabela raw_events`). Não faça commit nem push sem o dono pedir.
5. **Sem segredos no repo.** Configuração via variáveis de ambiente; `.env` fica fora do git.

## Decisões de projeto

Toda decisão de arquitetura, stack ou trade-off vira um **ADR** em [`docs/decisions/`](docs/decisions/), seguindo o template de lá ([ADR-0001](docs/decisions/0001-registrar-decisoes-como-adr.md)).

- Antes de propor algo que contradiz um ADR aceito, aponte o conflito e proponha um ADR novo que o substitua. Não edite o antigo silenciosamente.
- **Espelho no second brain:** cada ADR novo ou alterado também é registrado na nota do projeto no Obsidian (`01-Projetos/AgroVigilance.md`, seção de decisões) com uma linha de resumo e o número do ADR. O repo é a fonte da verdade do texto completo.
- Atualize `ARCHITECTURE.md` e `ROADMAP.md` quando uma decisão mudar o que está descrito neles.

## Convenções de código (a partir da Fase 1)

- Python 3.12+, pacote em `src/agrovigilance/`, dependências com `uv`.
- Nomes de código em inglês; documentação e commits em português.
- Testes com `pytest`. Rode os testes antes de dizer que algo está pronto.
- Tipagem nos limites (payloads externos, mensagens de fila, saída do LLM) com Pydantic.

## Glossário rápido

- **Talhão (field):** área da fazenda manejada como unidade. `field_id` no código.
- **Apontamento de campo:** registro de uma operação (pulverização agendada/concluída, colheita, etc.).
- **Janela de pulverização:** período em que vento, chuva e umidade permitem aplicar defensivo com eficácia.
- **Tenant:** o produtor ou fazenda dona dos dados.
