# Preparação e gravação do teste de usabilidade local

`CONFIRMADO`: roteiro da Issue #302, solicitado em 25/10/2026. O objetivo é
observar facilidade, eficiência e compreensão do fluxo logístico. Testes
automatizados e ensaio técnico não substituem a avaliação com participantes.

## Abrir o ambiente

Na raiz do projeto:

```powershell
docker compose start db backend frontend
docker compose ps
```

Abra **http://localhost:5173**. Use sua conta autorizada. ADMIN permite demonstrar
o ciclo completo; LOGISTICS_MANAGER planeja e organiza viagens, enquanto CHECKER
confere carregamentos. Em um teste por função, cada participante deve receber o
perfil correspondente. Não altere permissões para fazer uma tarefa passar.

Conclua o MFA antes de iniciar a captura. Caso o login faça parte da tarefa,
pause ou oculte a gravação durante códigos, QR, chave de configuração e códigos
de recuperação. Nenhuma credencial faz parte deste material.

## Dados próprios para gravar

```powershell
docker compose exec -T backend python -m scripts.prepare_usability --batch gravacao-01
```

`CONFIRMADO`: esse comando aceita apenas o ambiente/banco local e cria dados
fictícios identificados por **VIDEO gravacao-01**:

- um cliente e dois produtos: caixa LEVE e caixa MULTI;
- três veículos com documentação válida e três motoristas com CNH vigente;
- um pedido simples Pronto com seis volumes, um multi-caminhões Pronto com
  24 volumes e um Rascunho com quatro volumes.

O pedido multi foi dimensionado por peso para ultrapassar a capacidade individual
da frota presente na preparação, mantendo 24 volumes. O otimizador continua
escolhendo a divisão e validando todas as restrições. Alterações posteriores na
frota podem mudar o resultado. A preparação não cria planos nem inicia operações.

Confira os IDs e placas em [dados-gravacao.json](dados-gravacao.json). Para uma
nova tomada após consumir os dados, crie outro lote, por exemplo `gravacao-02`.
Reexecutar o mesmo lote reutiliza seus registros e informa a situação atual;
nunca restaura pedidos entregues ou libera veículos em operação. Uma falha
intermediária pode deixar parte dos cadastros criada, pois os serviços persistem
suas próprias transações. O comando não apaga dados existentes.

## Checagem antes da captura

1. Confirme frontend e backend respondendo e banco saudável.
2. Entre com a conta e o perfil previstos para as tarefas.
3. Confira os pedidos de gravação como Pronto/Rascunho e os veículos disponíveis.
4. Use resolução de pelo menos 1280 × 720, zoom 100% e um tema fixo durante a sessão.
5. Feche notificações do computador e abas com dados pessoais.
6. Abra esta ficha em outro dispositivo ou entregue ao observador. Não deixe
   instruções de navegação visíveis para o participante.

## Instrução inicial ao participante

“Vamos avaliar o sistema. Realize as tarefas como faria no trabalho e conte o
que está procurando ou esperando encontrar. Se algo não estiver claro, diga o
que entendeu. Não há problema em cometer erros ou desistir de uma tarefa.”

O observador não indica botões ou caminhos antes de registrar a dificuldade.
Se for preciso ajudar, registre a intervenção e permita continuar.

## Tarefas para o participante

| ID | Objetivo apresentado | Resultado observável |
| --- | --- | --- |
| T1 | Consulte a situação da operação e diga o que ainda precisa ser feito. | Encontra indicadores e explica ao menos uma pendência. |
| T2 | Cadastre um pedido de seis caixas LEVE para o cliente VIDEO gravacao-01, com destino fictício, e deixe-o pronto para planejamento. | Pedido salvo como Pronto, sem duplicação. |
| T3 | Organize esse pedido em um veículo, confira a disposição da carga e aceite o planejamento. | Plano calculado, visualização 3D consultada e plano aprovado. |
| T4 | Confira todos os volumes desse carregamento e prepare a viagem com um motorista disponível. | Carregamento concluído e viagem criada com o motorista correto. |
| T5 | Registre a saída, a entrega e a conclusão da viagem. Depois confira o pedido. | Viagem finalizada e pedido Entregue. |
| T6 | Distribua o pedido MULTI de 24 volumes entre a frota e explique a proposta. | Proposta completa salva; identifica veículos, volumes e necessidade de aprovação. |

`RECOMENDAÇÃO`: grave T2–T5 em sequência para mostrar continuidade e T6 como
cenário separado. Não é necessário aprovar ou iniciar a distribuição de T6 para
avaliar sua compreensão; se iniciar, acompanhe todas as partes até a conclusão.

## Guia exclusivo do observador

Este trecho contém os caminhos esperados e não deve orientar a execução inicial:

- T2: Pedidos → Novo pedido → salvar → editar situação para Pronto.
- T3: Planejamento de carga → Novo planejamento → Pedidos → Modalidade →
  Veículos → Revisão → calcular → Visualização 3D → aprovar.
- T4: plano aprovado → Conferir carregamento → iniciar conferência → conferir
  cada volume → finalizar → voltar ao plano → criar viagem.
- T5: viagem → iniciar viagem → iniciar entrega → confirmar entrega → finalizar
  viagem → consultar o pedido pelo detalhe.
- T6: novo planejamento → selecionar somente o pedido MULTI do lote → seleção
  automática da frota → conferir elegibilidade → revisar → otimizar. Um resultado
  em um único caminhão é válido se toda a carga couber; não force divisão artificial.

## Como registrar facilidade e eficiência

Use [ficha-observacao.csv](ficha-observacao.csv). Identifique participantes com
códigos fictícios, sem nomes pessoais. Para cada tarefa:

- marque início quando o participante terminar de ler e fim quando atingir o
  resultado ou desistir;
- registre ações equivocadas, retornos de tela, dúvidas verbalizadas e ajudas;
- classifique o resultado como `sem_ajuda`, `com_ajuda` ou `nao_concluida`;
- pergunte: “O que você esperava que acontecesse?” e “O que ficou confuso?”;
- ao terminar, pergunte qual foi a tarefa mais difícil e qual mensagem ajudou.

Compare tempo, conclusão e intervenções entre tarefas. Não transforme o tempo
do robô de testes em tempo de usuário e não preencha resultados humanos sem
participantes. A facilidade percebida deve vir dos relatos e da observação.

## Ensaio técnico e evidências

O lote `ensaio-01` é separado do lote de gravação. O ensaio usa uma conta
fictícia dedicada, autenticação real por senha/MFA, navegador, API e PostgreSQL
locais. Credenciais, cookies e segredos não são incluídos nas evidências.

Resultados e limitações: [ensaio técnico](../evidencias/usabilidade-local/README.md).
Esse registro informa quais fronteiras foram verificadas e quais tarefas foram
executadas; não representa avaliação de facilidade por participantes humanos.
