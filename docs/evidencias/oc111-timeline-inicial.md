# OC111 — timeline operacional inicial

API GET /api/v1/trips/{trip_id}/timeline?page=1&page_size=50.

O servidor confirma acesso real a viagem atraves do TripService e aplica RBAC.
A timeline projeta eventos da fonte de verdade, sem duplicar historicos:
- Mudancas de estado da viagem e de suas entregas (StatusHistory).
- Ocorrencias registradas para a viagem (Occurrence).

Ordenacao ascendente por instante UTC, origem e UUID para desempate estavel.
Somente tipo, referencias e ator autorizado sao expostos; descricao livre e
fotos das ocorrencias nao sao retornadas nesta projecao. A API e somente leitura.

Limite explicito de 3000 eventos por viagem nesta primeira versao; a API retorna
409 se exceder, sem apresentar resultado parcial enganoso.

AINDA PENDENTE para concluir OC111: integrar a OC94 (excecoes e reentregas),
navegacao e componente visual apos OC93, testes E2E/PostgreSQL multi-caminhao,
paginacao com cursor escalavel para operacoes acima de 3000 eventos.
