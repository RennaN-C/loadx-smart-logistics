# ADR-032: documentos e elegibilidade dos motoristas (OC102)

Status: decisão técnica implementada por autorização da Issue #149; revisão
independente pelo contrato normal do PR. Aprovação independente não é presumida.

## Contexto e decisão

`CONFIRMADO`: OC101 define versões documentais, políticas explícitas, validade
UTC exclusiva e alertas de 30 dias. OC65 reserva motoristas na criação/início de
viagens. OC105 mantém arquivamento separado da disponibilidade.

`RECOMENDAÇÃO`: reutilizar a regra temporal em shared/document_validity.py,
consumida por caminhões e motoristas. Documento do motorista tem tipo aprovado
por ADMIN/LOGISTICS_MANAGER; CNH é tipo nativo. Outros tipos são cadastrados
explicitamente pelos gestores, sem inventar MOPP, exames ou exigência legal.
Tipos são imutáveis, código único, auditados. Não há upload/storage/notificação
externa nesta OC. Documentos não têm URLs nem referências de storage.

`RECOMENDAÇÃO`: uma versão corrente por motorista/tipo; renovação cria UUID novo
e substitui anterior sem apagar. CNH corrente projeta license_number,
license_category e license_expires_at no cadastro. Create/PATCH existentes
preservam contratos e também versionam mudanças nesses campos. Backfill guarda
número/categoria legados sem inventar validade. Dados pessoais não aparecem em
listagens resumidas; documentos usam RBAC existente ADMIN/LOGISTICS_MANAGER.
CHECKER e DRIVER continuam sem acesso.

`RECOMENDAÇÃO`: políticas por motorista/tipo começam sem exigências. Required
exige versão corrente válida; CNH exigida deve ter validade informada e categoria
informada. Categorias aceitas podem ser configuradas explicitamente na política
CNH, usando o catálogo C/D/E/AC/AD/AE já ofertado pelo frontend. Compatibilidade
é pertinência exata ao conjunto aprovado, sem inferir hierarquia de categorias,
classe legal do veículo por peso, ou criar categorias de caminhão. Categoria
legada livre continua legível; novas versões CNH informadas usam o catálogo.
Política desligada não bloqueia frota legada; categoria desconhecida/faltante ou
vencimento ausente são inelegíveis quando CNH é exigida.

`RECOMENDAÇÃO`: emissão futura e vencimento em expires_at são inelegíveis;
alerta EXPIRING até 30 dias não bloqueia. Documentos adicionais podem não ter
validade quando não aplicável. Aprovação de tipos e eventos de criação/renovação/
política ficam na auditoria, preparada para consumo futuro OC103.

## Consistência e limites

`RECOMENDAÇÃO`: escrita documental/cadastral e reserva operacional usam lock na
linha do motorista; índice único parcial protege versão corrente. Unicidade de
CNH no cadastro permanece global. Projeção, histórico e auditoria são atômicos;
falha faz rollback. Criação/início de viagem validam elegibilidade pelo serviço
público de motoristas; viagem já iniciada pode concluir após vencimento.
Nenhum histórico de viagem/entrega é removido; active e conflito continuam
independentes. FleetAvailabilityService compõe disponibilidade, sem persistir.

`RECOMENDAÇÃO`: migration 20261009_0020 segue head 20261009_0019, único head.
Downgrade é permitido somente quando não descartaria dados/auditoria OC102;
backfill CNH intocado pode voltar sem perda porque seus dados já estão no cadastro.

`PENDENTE DE DEFINIÇÃO`: políticas legais automáticas, compatibilidade específica
por classe legal do veículo e notificações externas; não são implementadas nem
inferidas. Tipos adicionais e categorias aceitas exigem configuração explícita.
