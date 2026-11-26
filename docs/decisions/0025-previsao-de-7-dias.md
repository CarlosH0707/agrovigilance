# 0025. Previsão de 7 dias, sugestão de horário só até 72 h

- **Status:** aceita (substitui o `forecast_days=2` do ADR-0018)
- **Data:** 2026-11-25

## Contexto
O ADR-0018 coleta 48 h de previsão. Para o nível `postpone` (ADR-0024), o alerta precisa sugerir a próxima janela boa, e 48 h é pouco quando o agendamento é para amanhã à tarde. No futuro, o nível `no_window` vai querer dizer "a semana toda está ruim", o que pede mais dias.

Segundo a [NOAA](https://scijinks.gov/forecast-reliability), a previsão de até 5 dias acerta cerca de 90% das vezes, a de 7 dias cerca de 80%, e a de 10 dias ou mais, cerca de metade. Chuva é a variável mais difícil de prever, e o erro cresce com o prazo.

## Decisão
- O poller passa a pedir `forecast_days=7` (`FORECAST_DAYS` no client da Open-Meteo).
- A regra só **sugere horário** dentro das próximas **72 h** (`SUGGESTION_HORIZON` em `domain/spraying_window.py`). A precisão hora a hora ainda é boa nesse prazo.
- Os dias 4 a 7 ficam disponíveis no snapshot como **tendência**, para uso futuro no nível `no_window`. Nada os usa ainda.
- O resto do ADR-0018 (chave, granularidade, talhão fixo) continua valendo.

## Consequências
- Uma coleta gera 168 linhas e 168 mensagens em vez de 48. Com uma coleta por hora, são cerca de 4 mil linhas por dia no raw e no core. Ainda é pouco para o Postgres, mas limpar coletas antigas vira assunto quando houver agendamento contínuo.
- O snapshot cresce para até 168 horas no `forecast` JSONB, e o refresh continua barato.
- Um agendamento a mais de 7 dias só é avaliado quando a previsão o alcança (`assess` devolve `None`).

## Alternativas consideradas
- **Manter 48 h:** não sugere janela para depois de amanhã nem dá tendência.
- **72 h de coleta:** cobre a sugestão, mas exige mudar a coleta de novo quando a tendência for usada. O custo extra de 7 dias é pequeno.
- **16 dias (máximo da Open-Meteo):** a partir do 8º dia a previsão acerta cerca de metade das vezes, o que é ruído para decidir uma aplicação.
