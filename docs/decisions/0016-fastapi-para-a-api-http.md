# 0016. FastAPI + uvicorn para a API HTTP

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
O `POST /webhooks/field` é o primeiro endpoint HTTP. O AGENTS.md pede tipagem com Pydantic nos limites, e a lógica arriscada (idempotência) precisa de teste unitário sem subir servidor.

## Decisão
Usar FastAPI servido pelo uvicorn. O corpo é validado contra o modelo Pydantic (`FieldEvent`) dentro do handler, para gravar no raw o JSON exatamente como chegou; erro de validação vira 422. Banco e fila entram como dependências do FastAPI, trocadas por fakes nos testes (`TestClient`, que exige `httpx` no grupo dev).

Respostas: **202** `{"status": "accepted", "event_id"}` para evento novo, **200** `{"status": "duplicate"}` para reenvio, **422** para corpo inválido.

## Consequências
- Validação, 422 e documentação (`/docs`) prontas, com o mesmo Pydantic do resto do projeto.
- Mais três dependências (`fastapi`, `uvicorn`, `httpx` em dev).
- Duplicata responde sucesso (200): quem reenvia não precisa tratar como erro.
- O Starlette avisa que o `TestClient` vai trocar `httpx` por `httpx2`; trocar quando a migração for necessária.

## Alternativas consideradas
- Starlette puro: mais enxuto, mas validação e 422 ficariam na mão.
- `http.server` da biblioteca padrão: zero dependência, muito código manual e nada pronto para teste.
