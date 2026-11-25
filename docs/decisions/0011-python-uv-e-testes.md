# 0011. Python 3.14, `uv` e testes unitários com `pytest` desde o início

- **Status:** aceita
- **Data:** 2026-11-24

## Contexto
Precisamos fixar a versão do Python, a ferramenta de dependências e a estratégia de testes antes de escrever código.

## Decisão
- **Python 3.14**: madura (um ano de correções) e com suporte de todas as bibliotecas previstas. A 3.15 (out/2026) é recente demais; subir depois é trocar `requires-python` e o `.python-version`.
- **`uv`** para instalar o Python, criar o ambiente virtual e travar dependências (`pyproject.toml` + `uv.lock`).
- **`pytest`** para testes.
- **Testes unitários desde a primeira linha de lógica.** Toda regra nova (cálculo de chave de idempotência, normalização, regras de alerta, anti-spam) chega com teste unitário, sem depender de banco ou fila: essas dependências ficam atrás de interfaces simples e são substituídas por fakes nos testes.
- **Testes de integração** (contra Postgres e Floci reais) ficam para depois, com ADR próprio.

## Consequências
- Feedback rápido: a suíte unitária roda em segundos, sem Docker.
- O que só o banco garante (`UNIQUE` + `ON CONFLICT`) não é coberto por teste unitário. Até existirem testes de integração, essa parte é conferida manualmente e documentada no roadmap.
- O `uv` pertence à Astral, cuja compra pela OpenAI foi anunciada em mar/2026. É open source e usa `pyproject.toml` padrão, então trocar de ferramenta é barato.

## Alternativas consideradas
- Poetry: mais lento e não gerencia a versão do Python.
- pip + venv: não trava versões transitivas sozinho.
- `unittest` (biblioteca padrão): mais verboso, menos plugins.
