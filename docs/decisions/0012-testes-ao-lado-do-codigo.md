# 0012. Testes unitários ao lado do código

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
O ADR-0011 definiu `pytest` e testes unitários desde o início, mas não disse onde os testes ficam. Uma pasta `tests/` espelhando `src/` separa o teste do código que ele cobre e fica dessincronizada quando módulos mudam de lugar.

## Decisão
- Cada teste unitário fica **na mesma pasta do módulo que testa**, com o sufixo `_test.py`: `src/agrovigilance/<modulo>.py` → `src/agrovigilance/<modulo>_test.py`.
- A pasta `tests/` guarda só configuração e fixtures compartilhadas de teste, além do smoke test (`tests/test_smoke.py`).
- O `pytest` procura em `src/` e `tests/` (`*_test.py` e `test_*.py`) com `--import-mode=importlib`.
- Fixtures compartilhadas pelos testes colocated, quando existirem, moram em módulos de `tests/` e são carregadas por um `conftest.py` na raiz via `pytest_plugins`.
- Os arquivos `*_test.py` ficam fora do pacote distribuído (wheel).

## Consequências
- Teste e código andam juntos: ao abrir, mover ou apagar um módulo, o teste está do lado.
- Fica visível quais módulos não têm teste.
- Um `conftest.py` em `tests/` não alcança os testes de `src/`; fixtures globais precisam passar pela raiz.
- O build precisa excluir os testes explicitamente.

## Alternativas consideradas
- Pasta `tests/` espelhando `src/`: convenção comum do Python, mas afasta o teste do código.
- Prefixo `test_<modulo>.py` ao lado do módulo: funciona, mas separa teste e módulo na listagem alfabética.
