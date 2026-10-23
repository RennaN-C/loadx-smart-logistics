# OC106 — agenda operacional: agregacao temporal inicial

GET /api/v1/operations/agenda?start=...&end=...
Parametros de periodo obrigatorios com timezone (UTC normalizado), fim exclusivo,
maximo de sete dias. Filtros opcionais: kind, truck_id e driver_id.

O backend usa UNION ALL sobre fatos persistidos de viagem, carregamento e
conclusao de entrega, com ordenacao deterministica e no maximo 1000 eventos.
Gestores com trips.read consultam todas as operacoes; motorista so as suas
viagens se o vinculo esta ativo. Nao ha dados pessoais, GPS ou ETA ficticios.

**Limites deste recorte:** os modelos atuais nao persistem horario futuro
planejado de inicio e entrega. A API mostra somente atividades efetivas,
nao promete previsao/scheduling. Carregamentos sem viagem vinculada ainda
nao aparecem. Faltam visao calendario no frontend, integracao OC93/OC94,
atrasos e conflitos de programacao, testes de integracao e E2E.
