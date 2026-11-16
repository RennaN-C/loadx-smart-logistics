# Issue #430 — proposta para decisão de Rennan

`RECOMENDAÇÃO`: manter a API síncrona atual com 200 volumes enquanto não houver
orçamento comprovado por operação. A expansão para 500/1.000 precisa considerar
o pior caso geométrico, comparação de vários candidatos e frota heterogênea,
além da persistência e do navegador. O benchmark não estabelece SLA de produção.

`DECISÃO NECESSÁRIA`: Rennan deve decidir se cargas maiores serão jobs, qual o
orçamento máximo de CPU/RAM/tempo, o isolamento do executor e a experiência de
acompanhamento. Nenhuma fila, worker computacional, endpoint ou infraestrutura
foi implementado nesta branch. A outbox OC109 continua sendo de notificações.

Direção técnica proposta, sujeita a contrato e ADR próprios:

- Job persistido com ator/organização autorizados pelo servidor, chave
  idempotente e hash canônico da seleção/snapshot/versão do algoritmo. Chave
  repetida não cria cálculo duplicado; payload diferente recebe conflito.
- Estados e transições do **job**, sem novos estados de Order, com lease e
  fencing para que um executor antigo não confirme resultado após perder posse.
- Processo isolado com memória/CPU/parede limitadas. Cancelamento e timeout
  encerram o cálculo; não bastam fechar a conexão HTTP ou cancelar uma thread.
- Snapshot imutável de volumes/capacidades/versionamento; nenhum lock de banco
  mantido durante busca. Antes de persistir, revalidar fontes, disponibilidade,
  claims e contexto operacional nas transações existentes. Mudança de snapshot
  invalida o resultado, sem publicá-lo silenciosamente contra dados atuais.
- Resultado recuperável após falha de resposta. Commit atômico da proposta e
  ligação ao job; repetição de confirmação retorna o mesmo recurso. Falha antes
  do commit não deixa uma distribuição parcial nem perde identidades físicas.
- Consulta e cancelamento por autorização atual e ownership, incluindo futura
  organização contextual. Não aceitar tenant/ator arbitrário do cliente.
- Limites de jobs ativos/enfileirados por usuário/organização e globais;
  admissão/backpressure antes de expandir grandes quantidades. Retenção e coleta
  de snapshots/resultados precisam de política, sem apagar auditoria logística.
- Acompanhamento explícito de estado, progresso sem percentual inventado e
  causas sanitizadas. Retry distingue erro transitório de resultado insuficiente
  válido; não repetir indefinidamente uma busca determinística que já falhou.
- Navegador: revisar resposta JSON, tabela e cena 3D antes de liberar milhares
  de objetos. Otimização da renderização não pode alterar posições aprovadas.

`PENDENTE DE DEFINIÇÃO`: tecnologia de fila, pool de executores, cancelamento,
retenção, recuperação/checkpoint, quotas e custo operacional. Reiniciar uma
heurística pura com o mesmo snapshot é reproduzível; prometer retomada a partir
de checkpoint exige contrato/versionamento que ainda não existem.

`RISCO IDENTIFICADO`: elevar só MAX_VOLUMES pode ampliar simultaneamente CPU,
cache, linhas SQL, duração de locks na gravação e carga do visualizador, mantendo
timeout como resultado indeterminado. Esta proposta não autoriza deploy.
