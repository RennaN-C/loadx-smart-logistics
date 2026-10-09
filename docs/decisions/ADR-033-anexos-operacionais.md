# ADR-033 — anexos operacionais reutilizáveis

Status: aceita para a v1.2.0 standalone em 09/10/2026 (OC110, PR #179). Aprovação restrita ao adapter local e aos contratos implementados; fornecedor, retenção, descarte e storage de produção permanecem pendentes.

## Contexto e decisão

`CONFIRMADO`: OC80/ADR-027 fornece validação segura de PNG/JPEG, limite 5 MiB,
20 milhões de pixels, remoção de metadados e storage privado local. OC110 reutiliza
esses contratos sem alterar evidências/comprovantes. Um módulo attachments é
dono da metadata, serviço e API comuns; recursos iniciais aprovados pela Issue
são pedidos, viagens, entregas e ocorrências. Outros recursos exigem extensão
explícita de FK, autorização e testes; não existe referência polimórfica sem FK.

`RECOMENDAÇÃO`: manter somente PNG/JPEG nesta implementação, com detecção pelos
bytes e normalização OC80. PDF, Office, SVG, HTML, ZIP e executáveis são recusados
até contrato de validação aprovado. Não há nova dependência, OCR ou antivírus.

`CONFIRMADO`: EvidenceStorage é reutilizado como port de objetos opacos, com
put/read/discard e adapter local UUID privado. Binários reais em produção
permanecem desabilitados. Ambiente local requer opt-in EVIDENCE_STORAGE_DIR
privado dedicado; usar fixtures fictícias. Metadata pode ser consultada/removida
sem storage configurado. Upload/download sem adapter retorna 503.

`RECOMENDAÇÃO`: retenção local preserva bytes confirmados até descarte deliberado
do ambiente inteiro. Remoção lógica irreversível impede download, preserva
autor/data/recurso/checksum e registra auditoria. Nenhum purge ou prazo legal
é inventado. `PENDENTE DE DEFINIÇÃO`: retenção legal/técnica, fornecedor, backups,
proteção em repouso, purge e tipos adicionais antes de ativar produção.

## Autorização e consistência

`CONFIRMADO`: pedidos mantêm leitura ADMIN/LOGISTICS_MANAGER/CHECKER e gestão
ADMIN/LOGISTICS_MANAGER; DRIVER não acessa anexos de pedidos. Viagens/entregas/
ocorrências mantêm ADMIN/LOGISTICS_MANAGER e DRIVER ativo vinculado à própria
viagem, CHECKER negado. Serviço relê ator ativo sob lock e usa services públicos
dos recursos; UUID e event_id não autorizam. Sessão, Origin e CSRF são mantidos.

`CONFIRMADO`: exatamente uma FK de recurso; RESTRICT preserva histórico;
UNIQUE(recorded_by,event_id) serializa retries concorrentes. Fingerprint inclui
recurso e hash original; identidade incompatível retorna 409; replay revogado
não reativa. Upload valida/autoriza antes de put, metadata e auditoria commitam
juntas. Falha compensa somente UUID novo cuja ausência no banco foi confirmada;
commit incerto conserva bytes se não for possível confirmar ausência. Não há
promessa de transação distribuída. Session ligada a Connection/savepoint é
recusada para upload, conforme OC80. Download/revogação travam a mesma linha;
download verifica checksum/tamanho e responde attachment/nosniff/no-store sem URL.

## Compatibilidade e consequências

`CONFIRMADO`: rotas /attachments/{resource_type}/{resource_id}, com tipos plurais
orders/trips/deliveries/occurrences; listagem paginada inclui revogados; POST
aceita event_id e content_base64; GET /{id}/content e POST /{id}/revoke.
Nenhum campo dos contratos anteriores muda. UI contextual abre sob demanda,
com upload, download, revogação, paginação e estados loading/erro/vazio.
Anexos gerais não se tornam comprovantes de entrega OC78/OC80 e não mudam
estados operacionais. Downgrade com histórico é bloqueado para evitar perda.
