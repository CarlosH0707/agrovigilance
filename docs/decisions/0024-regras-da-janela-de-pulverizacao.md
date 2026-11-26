# 0024. Regras da janela de pulverização: perfis por cultura com ajustes e níveis de alerta

- **Status:** aceita (`FIELD_TIMEZONE` e ajuste do produtor passam ao cadastro do [ADR-0026](0026-cadastro-de-produtores-e-talhoes.md))
- **Data:** 2026-11-26

## Contexto
A Fase 3 precisa decidir, sem LLM (ADR-0007, ADR-0020), se a pulverização agendada de um talhão está numa janela boa. O snapshot (ADR-0022) entrega a previsão horária (`temperature_2m`, `relative_humidity_2m`, `precipitation_probability`, `wind_speed_10m`) e o agendamento em aberto.

O que a pesquisa e o produtor mostraram:
- Não existe uma tabela oficial de limites de tempo só para café (Embrapa Café, Incaper e Procafé). Os estudos com café usam os limites gerais de tecnologia de aplicação (Antuniassi, Embrapa).
- O que mais muda os números é o **produto**: cada bula traz umidade, vento e tempo sem chuva próprios, e o biológico (*Beauveria*) exige ar úmido.
- O **equipamento** muda o vento mínimo: no turbo do trator e no drone, a corrente de ar empurra a gota, e calmaria não atrapalha. O produtor confirma: "quanto mais parado melhor; parado não tira a força do pulverizador do trator".
- O **produtor** decide o quanto tolera: no ES "precisa aplicar mesmo no calor pra dar conta".

## Decisão

### Perfis como dados
Ficam em `domain/spraying_profile.py`, separados da regra.
- `SprayingProfile` por cultura. Cada limite é um `Bound` (mínimo ou máximo) com valor **ideal**, faixa **tolerável** opcional, **motivo** e **fonte**. O texto do alerta sai do motivo, então limite e explicação não se separam.
- `ApplicationContext`: `crop` obrigatório; `region`, `producer`, `equipment`, `product_class`, `brand` e `product` opcionais.
- `ProfileAdjustment` troca campos do perfil quando todos os campos do `match` batem com o contexto. A ordem de aplicação é: menos campos no `match` primeiro; no empate, o campo mais específico por último (`region` < `producer` < `equipment` < `product_class` < `brand` < `product`). Um campo com erro de digitação falha na criação, em vez de nunca casar.
- **Cada fator mexe só no que é dele**, para não haver disputa entre ajustes:

  | Fator | Mexe em |
  |---|---|
  | Produtor | temperatura tolerável |
  | Equipamento | vento mínimo |
  | Produto ou classe | umidade, vento máximo e tempo sem chuva |

### Perfil base do café

| Limite | Ideal | Tolerável | Fonte |
|---|---|---|---|
| Vento mínimo (a 2 m) | 3 km/h | — | Antuniassi & Baio (2004); Embrapa, Documentos 102 |
| Vento máximo (a 2 m) | 10 km/h | — | idem |
| Temperatura máxima | 30 °C | — | idem; Embrapa Soja |
| Umidade mínima | 55% | 50% | Antuniassi (55%); Embrapa, Documentos 102 (50 a 55%) |
| Probabilidade de chuva máxima | 30% | 50% | faixas do projeto: a Open-Meteo dá probabilidade, não certeza |

- **Sessão de aplicação:** 2 h a partir da hora agendada. A regra julga se a sessão do dia é viável, não o talhão inteiro; a duração por área × rendimento do equipamento fica para quando houver cadastro de talhão.
- **Horas sem chuva depois:** 6 h ("contra praga, pelo menos 5 a 6 h", segundo o produtor). A bula de cada produto ajusta.
- **Chuva no resto do dia:** depois das horas sem chuva, até o fim do dia local, chuva acima do ideal vira **atenção**, nunca bloqueio ("o ideal é nem chover no dia").

### Ajustes registrados

| Match | Muda | Fonte |
|---|---|---|
| `equipment=trator` | sem vento mínimo | produtor; o turbo empurra a gota |
| `equipment=drone` | sem vento mínimo | produtor; o rotor empurra a gota |
| `equipment=costal` | calmaria vira atenção (ideal 3, tolerável 0 km/h) | Antuniassi; produtor |
| `product_class=biologico` | umidade ≥ 65% | Incaper, Documentos 266 (2019) |
| `product_class=herbicida` | 2 h sem chuva | produtor ("mato: mínimo 2 h") |
| `product=priori_xtra` | umidade ≥ 50%, vento ≤ 15 km/h | bula Priori Xtra (25/06/2025), aplicação terrestre |
| `product=opera` | umidade ≥ 60%, 4 h sem chuva | bula Opera (rev. 16, 18/07/2025) |
| `product=altacor` | vento ≤ 15 km/h | bula Altacor (05/08/2026), aplicação terrestre |
| `product=marshal` | umidade ≥ 50% | bula Marshal (FMC) |
| `product=roundup` | 4 h sem chuva | bula Roundup Original DI |

**Ajustes do produtor não ficam no código:** são dados de cada produtor e virão do cadastro (próximo passo), passados a `resolve_profile` junto com os do código. O primeiro é o do produtor do talhão fixo: temperatura tolerável até **35 °C** ("precisa aplicar mesmo no calor pra dar conta").

Ficaram de fora até confirmar: Curyom (bula não baixou), Clopam e Rite (não identificados) e a marca do *Beauveria* (vale a classe `biologico`). Esses produtos usam o perfil base.

### Avaliação
Fica em `domain/spraying_window.py`, função pura `assess(scheduled_for, forecast, profile, now, tz)`.
- **Vento a 2 m:** a Open-Meteo dá o vento a 10 m, e o bico fica perto de 2 m. A regra converte pelo perfil logarítmico da FAO-56 (eq. 47): u₂ = u₁₀ × 4,87 / ln(67,8 × 10 − 5,42) ≈ **0,748** u₁₀.
- Nas horas da aplicação valem todos os limites. Nas horas sem chuva depois dela, só a chuva. No resto do dia, chuva vale como atenção.
- Horas que já passaram são ignoradas, porque o snapshot pode tê-las até o próximo refresh.
- Agendamento no passado, hora faltando ou valor nulo na aplicação ou nas horas sem chuva → `None` (ainda não há o que dizer). Assim não se afirma que o tempo está bom sem dado.
- Todos os limites são inclusivos: 10 km/h ainda é ideal.

### Níveis

| Nível | Quando |
|---|---|
| `ok` | Nenhum valor fora do ideal |
| `attention` | Só violações toleráveis (incluindo chuva no resto do dia) |
| `postpone` | Alguma violação bloqueante, e existe um início nas próximas 72 h (ADR-0025) com a aplicação e as horas sem chuva no ideal. O primeiro desses inícios vira a sugestão, mesmo que seja antes do agendado. |
| `no_window` | Bloqueado e sem janela ideal nas próximas 72 h. Na Fase 3 o alerta é um texto fixo: "nenhuma janela boa nos próximos 3 dias; melhor esperar do que perder o produto". |

A sugestão só aceita janela **ideal** (chuva no fim do dia é a única exceção). Sugerir uma janela tolerável trocaria um risco por outro sem avisar.

### Guardrail de horário da sugestão
- A regra nunca sugere uma aplicação que comece antes das **6h** ou termine depois das **18h** no horário local do talhão. Com 2 h de sessão, o último início sugerido é 16h. As horas sem chuva podem passar das 18h, porque o produto já está na folha.
- É constante do código, não campo do perfil: nenhum ajuste consegue liberar sugestão de madrugada ou à noite. A preferência de cada produtor, quando existir, só aperta essa faixa.
- Vale só para a **sugestão**. O agendamento do produtor fora da faixa (ex.: 5h, para fugir do calor) é avaliado normalmente pelo tempo.
- O fuso do talhão vem de `FIELD_TIMEZONE` (`America/Sao_Paulo`). Sem ele, 6h em UTC viraria 3h no Brasil.

## Consequências
- Produto, marca e equipamento entram como ajustes sem mudar a regra nem o formato do perfil.
- A decisão de alertar é testável e explicável. Cada violação traz hora, condição, valor (vento já a 2 m) e o `Bound` com motivo e fonte.
- O resultado muda com o produto. Na previsão real de 27 a 29/11, o perfil base não teve janela, e o Opera (4 h sem chuva) teve.
- Produtor novo não exige mudar código: a tolerância dele é dado no cadastro.
- **Drone fora de bula:** das bulas lidas, nenhuma recomenda drone em café. A do Opera recomenda drone só para cana, e a do Roundup diz não ter dados para drone. A regra avalia o tempo, não a conformidade da bula; esse aviso fica para o texto do alerta e para o agrônomo.
- **Biológico ao fim da tarde:** a bula do Bovemax (*Beauveria*) recomenda fim de tarde ou noite, por causa do sol. O guardrail das 18h impede a regra de sugerir esse horário. O produtor pode agendar à noite, e a regra avalia normalmente.
- O nível `no_window` é o candidato natural a um LLM no futuro, para **explicar opções**, nunca para decidir. Isso exigirá um ADR que revise o ADR-0020.

## Alternativas consideradas
- **Limites como constantes dentro da regra:** mais simples, mas misturam dado e lógica e não comportam cultura, produtor, equipamento ou produto.
- **Limites no `.env` ou no banco:** são regra de negócio, versionada e testada com o código. Banco só quando houver cadastro por tenant.
- **Herança de classes por cultura e região:** explode em combinações (café × ES × biológico × trator). Os ajustes por `match` combinam sozinhos.
- **Horário permitido como campo do perfil:** um ajuste poderia liberar a madrugada sem querer.
- **Limite de vento a 10 m mais folgado (ex.: 13 km/h):** daria o mesmo número, mas sem explicação. A conversão da FAO-56 tem fonte e mostra o vento na altura do bico.
- **Duração da aplicação por área × rendimento:** mais fiel, mas exige área do talhão e aplicações de vários dias. Fica para depois do cadastro de talhão.
- **Delta T** (diferença entre bulbo seco e úmido), usado em alguns guias: a Open-Meteo não o entrega direto, e temperatura + umidade cobrem o mesmo risco no MVP.

## Fontes
- Antuniassi & Baio (2004), [Boletim SBMET](https://www.alice.cnptia.embrapa.br/alice/bitstream/doc/15393/1/2006AP028.pdf)
- Embrapa, [Tecnologia de Aplicação de Defensivos Agrícolas, Documentos 102](https://www.infoteca.cnptia.embrapa.br/bitstream/doc/426350/1/Dc102.pdf)
- Embrapa, [Tecnologia de aplicação de herbicidas (soja)](https://www.embrapa.br/en/agencia-de-informacao-tecnologica/cultivos/soja/producao/manejo-de-plantas-daninhas/tecnologia-de-aplicacao-de-herbicidas)
- Incaper, [Manejo da broca-do-café, Documentos 266 (2019)](https://biblioteca.incaper.es.gov.br/digital/bitstream/123456789/3950/1/Broca-cafe-Incaper.pdf)
- FAO, [Irrigation and Drainage Paper 56, cap. 3, eq. 47](https://www.fao.org/4/x0490e/x0490e07.htm)
- Bulas: [Priori Xtra](https://www.syngenta.com.br/sites/g/files/kgtney466/files/media/document/2025/07/22/PRIORI%20XTRA_Bula%20Completa_25.06.2025.pdf), [Opera](https://download.basf.com/p1/8a8081c57fd4b609017fe08135d17ecf/pt/Bula_-_Opera%C2%AE_Flyer_portugu%C3%AAs.pdf), [Altacor](https://fmcagricola.com.br/Content/Fotos/Bula-Altacor.pdf), [Marshal](https://www.fmcagricola.com.br/Content/Fotos/Bula-Marshal.pdf), [Roundup Original DI](https://assets.revistacultivar.com.br/6e265a6c-9d36-43f2-9ec1-c757bba8540a_roundup_original_di_bula.pdf), [Bovemax EC](https://agrofit.agricultura.gov.br/agrofit_cons/agrofit.ap_download_blob_agrofit?p_id_file=522215&p_nm_file=F1531559791/Bula+Bovemax+EC_Inclus%EF%BF%BDo+Alvo+V01-25.pdf)
- Estudos de chuva: Instituto Biológico, [fungicidas sistêmicos contra a ferrugem sob chuva simulada](https://www.scielo.br/j/aib/a/MYWBhSkVxnM3hKMJcfxPRgw/?lang=pt); [cúpricos com óleo vegetal (SciELO)](https://www.scielo.br/j/fb/a/JbbYCfwPW3zV658R3hFGszp/?format=html&lang=pt)
