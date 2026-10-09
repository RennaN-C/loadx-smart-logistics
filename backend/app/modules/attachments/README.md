# Anexos operacionais — OC110

`CONFIRMADO`: contrato da Issue #157 e [ADR-033](../../../../docs/decisions/ADR-033-anexos-operacionais.md).
Módulo único para pedidos, viagens, entregas e ocorrências; services públicos dos
recursos autorizam antes de validar/persistir/ler bytes. FKs RESTRICT e CHECK de
exatamente um recurso impedem órfãos; arquivo não altera estados operacionais.

## Contrato HTTP

Prefixo `/api/v1/attachments/{resource_type}/{resource_id}`. Tipos aprovados:
`orders`, `trips`, `deliveries`, `occurrences`. Outros tipos retornam 422.

| Método | Caminho | Resultado |
|---|---|---|
| POST | prefixo | 200 AttachmentRead, registro/retry |
| GET | prefixo | PageResponse, page/page_size/sort_order |
| GET | /{attachment_id} | metadata, inclusive REVOKED |
| GET | /{attachment_id}/content | binário autorizado ACTIVE |
| POST | /{attachment_id}/revoke | corpo {}, 200, idempotente |

`CONFIRMADO`: POST aceita somente event_id UUID e content_base64. Gere event_id
por arquivo intencional; retries do mesmo arquivo preservam identidade. Autor vem
da sessão, recurso do caminho. Metadata inclui id, resource_type/resource_id,
media_type, size_bytes, sha256, status, recorded_by/recorded_at, revoked_by/
revoked_at; não expõe evento/fingerprint/caminho/URL/bytes. Remoção é irreversível,
metadata histórica continua consultável, bytes confirmados não são descartados.

`CONFIRMADO`: limite OC80 5 MiB antes/depois da normalização, imagens estáticas
PNG/JPEG até 20 milhões de pixels. Formato deriva dos bytes; Pillow valida e
regrava sem EXIF/ICC/texto/trailers. PDF/Office/SVG/HTML/ZIP não são aceitos.

## RBAC e auditoria

`CONFIRMADO`: pedidos: ADMIN/LOGISTICS_MANAGER gerenciam, CHECKER consulta,
DRIVER negado. Demais recursos: ADMIN/LOGISTICS_MANAGER e DRIVER ativo/vinculado
à própria viagem consultam e gerenciam; CHECKER negado. Backend relê estado do
ator sob lock. Sessão, Origin e CSRF obrigatórios conforme contratos existentes.
ATTACHMENT_REGISTERED/ATTACHMENT_REVOKED são auditados na mesma transação; retry
não duplica eventos. Histórico preserva ator e data mesmo com cadastro arquivado.

## Storage, retenção e falhas

`CONFIRMADO`: reutiliza EvidenceStorage e LocalEvidenceStorage OC80. Nenhum SDK
ou URL pública no domínio. Configuração opt-in APP_ENV=local e
EVIDENCE_STORAGE_DIR dedicado/privado fora do checkout. Pasta 0700/arquivo 0600,
no-follow/UUID. Sem adapter upload/download retorna ATTACHMENT_STORAGE_UNAVAILABLE
503; consulta/revogação não dependem dele. Produção permanece desabilitada.
Download protegido verifica tamanho/checksum e usa attachment/nosniff/no-store.

`CONFIRMADO`: UNIQUE por ator/evento serializa concorrência. Fingerprint original
inclui recurso; conflito 409; retry revogado permanece revogado. Upload exige
Session ligada a Engine com commit real, não Connection/savepoint. Falha desfaz
metadata/auditoria e compensa somente chave nova confirmadamente não persistida.
COMMIT incerto conserva blob se a ausência não pode ser verificada. Órfão não é
baixável; não se promete transação distribuída. Download/revogação usam row lock.

`RECOMENDAÇÃO`: bytes confirmados locais ficam até descarte deliberado do
ambiente. `PENDENTE DE DEFINIÇÃO`: política legal/técnica de retenção, purge,
backups, proteção em repouso e fornecedor antes de produção; sem ativação
silenciosa. Não há notificações externas, OCR ou antivírus.

Migration 20261009_0021 → 20261009_0020, único head. Downgrade somente sem anexos
ou auditoria OC110; revogados também bloqueiam perda.

## Erros e validação

Envelope padrão code/message/details: AUTH_FORBIDDEN 403;
ATTACHMENT_RESOURCE_NOT_FOUND/ATTACHMENT_NOT_FOUND 404;
ATTACHMENT_IDENTITY_CONFLICT/ATTACHMENT_REVOKED 409; VALIDATION_ERROR/
ATTACHMENT_CONTENT_INVALID 422; ATTACHMENT_STORAGE_UNAVAILABLE 503.
Não há dados binários/path/provider error em logs.

Testes PostgreSQL 16 exclusivo TEST_DATABASE_URL: `python -m pytest -q
tests/integration/test_operational_attachments.py tests/unit/test_attachment_contract.py`.
