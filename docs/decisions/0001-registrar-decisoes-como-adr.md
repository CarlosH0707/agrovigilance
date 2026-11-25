# 0001. Registrar decisões como ADRs, espelhadas no second brain

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
O projeto avança em sessões curtas e semanais, às vezes com ajuda de agentes de IA. Sem registro, o motivo de cada escolha se perde entre uma semana e outra, e o projeto também serve de portfólio de System Design, onde o raciocínio importa tanto quanto o código.

## Decisão
Toda decisão de arquitetura, stack ou trade-off vira um ADR em `docs/decisions/`. A nota do projeto no Obsidian (`01-Projetos/AgroVigilance.md`) recebe uma linha de resumo com o número do ADR. O texto completo vive no repo.

## Consequências
- O histórico de decisões fica versionado junto com o código.
- Exige disciplina: decisão sem ADR não vale.
- Duas fontes podem divergir; por isso o vault guarda só o resumo e o link, nunca o texto completo.

## Alternativas consideradas
- Só no Obsidian: fica fora do repo, invisível para quem avalia o projeto.
- Só no repo: perde a conexão com o resto do planejamento pessoal (carreira, agenda).
