# Evidências de entrega — OC80

`CONFIRMADO`: contrato aditivo da Issue #123. Comprovante OC78 mantém schema/id
e conclusão auditada. Decisão proposta na [ADR-027](../../../../docs/decisions/ADR-027-evidencias-de-entrega.md).

## API para OC81

`CONFIRMADO`: prefixo `/api/v1/deliveries/{delivery_id}/evidences`:

| Método/caminho | Resultado |
|---|---|
| POST prefixo | 200 DeliveryEvidenceRead, registro/reenvio |
| GET prefixo | PageResponse, page/page_size/sort_order, máximo 100 por página |
| GET /{evidence_id} | metadata, inclusive REVOKED |
| GET /{evidence_id}/content | binário privado, attachment, nosniff, sem cache |
| POST /{evidence_id}/revoke | corpo `{}`, revogação idempotente, 200 metadata |

`CONFIRMADO`: POST aceita somente event_id UUID, kind PHOTO/SIGNATURE e
content_base64. Gere uma chave por registro intencional e conserve-a nos retries
com mesmos bytes/tipo/entrega. Delivery vem do path e responsável do backend.
Campos extras, arquivo, MIME, URL, caminho, receipt_id e user_id são negados.
SIGNATURE é imagem de assinatura simples, sem validação do signatário ou
assinatura digital avançada. PNG/JPEG estáticos são verificados pelo Pillow:
5 MiB antes/depois da normalização e 20 milhões de pixels. Formato vem dos bytes.
Imagens são regravadas dos pixels sem EXIF, ICC, texto ou trailers. Checksum
descreve bytes normalizados; fingerprint usa o hash do original para conflitos.
Originais não são persistidos.

`CONFIRMADO`: metadata: id, delivery_id, receipt_id, kind, media_type, size_bytes,
sha256, status, recorded_by/recorded_at e revoked_by/revoked_at. Tempos são UTC;
não expõe evento, fingerprint, path, provider URL ou base64. Download só ACTIVE,
após verificar tamanho/checksum; filename é UUID do servidor. Revogação e download
usam locks operacionais para não disputar um objeto sem estado consistente.

## Domínio e idempotência

`CONFIRMADO`: exige entrega DELIVERED com único histórico válido OC78; anexar
após FINISHED é permitido. PENDING/IN_DELIVERY retornam
DELIVERY_RECEIPT_NOT_AVAILABLE. Não altera pedido, estado ou comprovante.
receipt_id é derivado da conclusão, com FK RESTRICT. TripService fornece a
fronteira pública de autorização/locks reutilizada por estados/evidências.
Gestor opera/consulta, DRIVER ativo/vinculado somente a própria viagem,
ADMIN consulta, CHECKER é negado; sessão, Origin e CSRF são preservados.
Usuário é relido sob lock; identidade enviada no corpo nunca autoriza.

`CONFIRMADO`: UNIQUE (recorded_by,event_id) no PostgreSQL. Mesmo ator/evento,
entrega/tipo/bytes retorna registro original sem outro blob ou responsável.
Reutilização incompatível gera EVIDENCE_IDENTITY_CONFLICT. Chave não autoriza;
novo event_id é outro registro explícito, mesmo com checksum igual. Reenvio
revogado retorna REVOKED sem reativar ou copiar bytes. Concorrência serializa
no banco, sem depender de memória.

## Storage e OC83

`CONFIRMADO`: EvidenceStorage tem put(UUID,bytes), read(UUID), discard(UUID).
Domínio não usa path/URL/SDK; FakeEvidenceStorage isola testes. Adapter local
usa root privado 0700, arquivos exclusivos 0600, no-follow e UUID do servidor.
Opt-in APP_ENV=local e EVIDENCE_STORAGE_DIR em diretório dedicado fora do checkout,
por exemplo `/workspace/.loadx-cloud/evidence-storage`. Root público/symlink é
recusado. Sem configuração retorna 503; produção é desabilitada mesmo com path.
Em Compose o operador precisa montar diretório privado persistente e gravável;
arquivos de container não garantem persistência. Não há fornecedor real ativo.

`CONFIRMADO`: autorização/validação/claim antecedem put. Falha antes de commit
desfaz metadata e compensa somente blob novo. COMMIT incerto só permite remover
se ausência da linha for confirmada; se não for possível, preserva o blob e loga
apenas UUID. Órfão sem linha não pode ser baixado. Não se promete transação
distribuída. Session deve estar ligada a Engine e possuir commit real; registro
recusa Connection/savepoint, pois commit interno não confirma IO de storage.

`CONFIRMADO`: OC83 autentica bytes/ator pelos ports OC79 e chama este service
em Session dedicada, preservando event_id e replay. Não passar mídia ao catálogo
atual OC79 nem derivar ator só do telefone. Não há novo webhook/fornecedor/comando
externo nesta OC. Outbox/reprocessamento distribuído pertencem às OCs próprias.

## Retenção e remoção

`CONFIRMADO`: revogação lógica preserva vínculos/metadata/responsável original e
adiciona ator/horário da revogação; impede download. Não há DELETE físico público,
reativação ou substituição do arquivo. Metadata segue consultável com autorização.

`RECOMENDAÇÃO`: bytes revogados permanecem no adapter local até descarte
deliberado do ambiente inteiro. Não há job de purge ou prazo inventado. Compensação
trata só objetos novos não confirmados; retry nunca apaga evidência histórica.

`PENDENTE DE DEFINIÇÃO`: equipe aprovar prazo/base legal de retenção, proteção em
repouso, backups, purge verificável, fornecedor e acesso antes de produção.
Revogação não apaga backups. Imagens podem conter dados pessoais; usar somente
fixtures fictícias no desenvolvimento. Não há GPS, OCR, antivírus ou assinatura
avançada. A proposta ADR precisa de revisão; OC110 de anexos não é antecipada.

## Erros e testes

`CONFIRMADO`: envelope code/message/details sem conteúdo/path/provider errors.
Logs guardam somente UUID/evento.

| Código | HTTP |
|---|---:|
| AUTH_INVALID_TOKEN / AUTH_CSRF_INVALID / AUTH_FORBIDDEN | 401 / 403 / 403 |
| DELIVERY_NOT_FOUND / EVIDENCE_NOT_FOUND | 404 |
| DELIVERY_RECEIPT_NOT_AVAILABLE / DELIVERY_RECEIPT_HISTORY_INVALID | 409 |
| EVIDENCE_IDENTITY_CONFLICT / EVIDENCE_REVOKED | 409 |
| VALIDATION_ERROR / EVIDENCE_CONTENT_INVALID | 422 |
| EVIDENCE_STORAGE_UNAVAILABLE | 503 |

`CONFIRMADO`: em backend com PostgreSQL 16 exclusivo TEST_DATABASE_URL:

```bash
python -m pytest -q tests/unit/test_evidence_storage.py tests/unit/test_evidence_configuration.py tests/integration/test_delivery_evidences.py tests/integration/test_delivery_receipts_api.py tests/integration/test_external_commands.py
```
