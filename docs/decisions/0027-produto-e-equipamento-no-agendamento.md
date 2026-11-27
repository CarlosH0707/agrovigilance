# 0027. Produto e equipamento no agendamento, com catálogo de produtos

- **Status:** aceita (amplia o canonical payload do ADR-0019)
- **Data:** 2026-11-26

## Contexto
A regra da janela (ADR-0024) muda com o produto (umidade, vento e horas sem chuva da bula) e com o equipamento (vento mínimo). Até aqui, o agendamento (`pulverizacao_agendada`) só trazia o horário. A regra não tinha como saber se a aplicação era de Opera com trator ou de herbicida com costal.

Também ficou em aberto no ADR-0026: o worker aceitava evento de talhão não cadastrado.

## Decisão
- **Três campos opcionais no apontamento**, guardados em `core.field_operations` (migration `V0008`):

  | Campo | Regra |
  |---|---|
  | `product` | Texto livre, procurado no catálogo pelo id ou pelo nome, sem ligar para caixa, acento ou separador ("Priori Xtra", "priori-xtra"). Se for conhecido, vira o id do catálogo e define a classe. Se for desconhecido, é **aceito** e guardado como veio. |
  | `product_class` | Lista fechada: `fungicida`, `inseticida`, `herbicida`, `biologico`. Sozinha, basta para dizer "vou bater mato" (`herbicida`). Classe que contradiz o produto do catálogo (ex.: Opera + herbicida) é inválida. |
  | `equipment` | Lista fechada: `trator`, `drone`, `costal`. **Nunca é assumido:** sem valor fica vazio, e o alerta pergunta qual equipamento vai ser usado. |

  Valor fora de lista fechada, produto vazio ou que não é texto → `rejected`, como os outros apontamentos inválidos (ADR-0019). O banco repete as listas fechadas com `CHECK`.
- **Catálogo** em `domain/products.py`: Priori Xtra, Opera, Altacor, Marshal, Curyom, Roundup e *Beauveria bassiana*, cada um com a classe. Os ids são os mesmos dos ajustes de perfil, e um teste garante que todo ajuste por produto aponta para um produto do catálogo.
- **Snapshot:** o agendamento em aberto leva junto `scheduled_product`, `scheduled_product_class` e `scheduled_equipment`. Vale o último agendamento, como no ADR-0022, e a conclusão limpa os três.
- **Talhão não cadastrado → `rejected`.** O worker confere `core.fields` antes de converter o apontamento. Talhão inexistente não passa a existir tentando de novo, então não vai para a DLQ. O webhook continua gravando no raw o que chegou (ADR-0002).

## Consequências
- A regra recebe produto, classe e equipamento do snapshot e monta o `ApplicationContext` sem perguntar nada a mais.
- **Produto desconhecido** (Clopam, Rite) não bloqueia o agendamento. O alerta avisa "produto sem bula cadastrada", e vale a classe, se informada, ou o perfil base.
- **Sem equipamento**, o alerta pergunta qual vai ser usado. O vento mínimo, que depende do equipamento, fica no valor do perfil base até a resposta.
- Incluir um produto no catálogo é mudança de código, com a fonte (bula) no ajuste. Faz sentido: cada produto novo traz limites que precisam de revisão.
- O texto livre de produto desconhecido fica no banco como veio. Se o produto entrar no catálogo depois, os agendamentos antigos continuam com o texto original.

## Alternativas consideradas
- **Recusar produto desconhecido (422 ou `rejected`):** obrigaria o produtor a reenviar o agendamento por causa de um cadastro que é nosso.
- **Assumir trator quando o equipamento não vem:** errado em metade dos casos (drone e costal), e o vento mínimo muda com o equipamento.
- **Apelidos no catálogo** ("Prioriestra", "Randape"): os nomes errados eram de digitação, não do uso do produtor. Na Fase 4, quem interpreta a mensagem do WhatsApp é o LLM, e ele já entrega o nome certo.
- **Validar o talhão no webhook:** o raw deixaria de guardar tudo o que chegou (ADR-0002), e o webhook passaria a depender do cadastro.
