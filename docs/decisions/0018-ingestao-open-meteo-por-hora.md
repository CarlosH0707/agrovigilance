# 0018. Ingestão da Open-Meteo: uma linha por hora prevista e por coleta

- **Status:** aceita
- **Data:** 2026-11-25

## Contexto
A Fase 1 precisa ingerir a previsão horária da Open-Meteo de forma idempotente (ADR-0002) para um talhão. Uma resposta traz várias horas, e a mesma hora alvo é prevista de novo a cada coleta, com valores que mudam. Ainda não existe cadastro de talhões em `core`.

## Decisão
- **Granularidade:** cada coleta é quebrada em uma linha por hora prevista em `raw.open_meteo_events`. O `occurred_at` é a hora prevista, e o `payload` é a resposta como chegou, com `hourly` recortado naquela hora (metadados e unidades inteiros).
- **Chave:** `weather:{tenant_id}:{field_id}:{target_hour}:{bucket}`, com o bucket sendo a hora da coleta truncada, tudo em UTC. Coletar de novo na mesma hora é duplicata, e a coleta da hora seguinte é uma versão nova (DO NOTHING, correção vira nova chave). O `tenant_id` entra na chave, como no hash do webhook, para dois clientes com o mesmo `field_id` não colidirem.
- **Requisição:** `hourly=temperature_2m,relative_humidity_2m,precipitation_probability,wind_speed_10m`, `timezone=UTC`, `forecast_days=2` (o caso de uso é a janela de pulverização, de curto prazo). Chamada com `urllib` da biblioteca padrão. A URL vem de `OPEN_METEO_URL` (padrão: a API pública), para trocar por um endpoint pago ou por um mock sem mexer no código. A lista de variáveis fica no código, porque as regras de alerta dependem dela.
- **Talhão fixo:** `FIELD_TENANT_ID`, `FIELD_ID`, `FIELD_LAT` e `FIELD_LON` no `.env`. A coordenada real não vai para o git, porque o repo é público. O `.env.example` traz um ponto genérico.
- **Execução:** `entrypoints/poller.py` faz uma coleta por execução. O agendamento fica para depois.

## Consequências
- Uma coleta por hora gera cerca de 48 linhas e 48 mensagens. Volume pequeno para o MVP, e o worker da Fase 2 pode juntar por talhão.
- Dá para comparar como a previsão de uma mesma hora mudou ao longo das coletas.
- Sem cadastro, um talhão só. Vários talhões dependem de `core.fields`.

## Alternativas consideradas
- Uma linha por coleta, com a resposta inteira: menos linhas, mas a idempotência e o read model ficam por hora de qualquer jeito.
- Chave sem bucket (só a hora alvo): a primeira previsão de cada hora venceria para sempre, e as atualizações seriam descartadas.
- `httpx` como cliente HTTP: hoje ele só está no grupo dev, e uma chamada GET não justifica mais uma dependência de produção.
