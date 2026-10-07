# ADR-027: contrato de evidências vinculado ao comprovante de entrega

Status: proposta na OC80, sujeita à revisão do PR

## Contexto

`CONFIRMADO`: OC78 projeta a conclusão auditada, sem arquivo; OC79 protege
comandos externos; OC80 (#123) prepara evidências para OC81/OC83 sem fornecedor.

## Decisão

`RECOMENDAÇÃO`: aceitar PHOTO e SIGNATURE (imagem de assinatura simples, sem
valor de assinatura digital avançada), PNG/JPEG verificados pelo Pillow já usado
no backend. Máximo 5 MiB decodificados e 20 milhões de pixels, uma imagem estática.
Não aceitar URL, caminho, nome de arquivo, MIME, usuário ou papel do cliente.
O contrato JSON recebe kind, event_id UUID e content_base64; entrega vem do path.

`RECOMENDAÇÃO`: anexar somente a entrega DELIVERED com comprovante OC78 válido,
inclusive após FINISHED. Nunca concluir a entrega automaticamente. Delivery e
receipt_id do único histórico são obtidos e autorizados pelo TripService.
Gestor/motorista vinculado operam; administrador consulta; conferente é negado.
Usuário/horários são do servidor. O comprovante existente não muda seu schema.

`RECOMENDAÇÃO`: entidade delivery_evidences armazena tipo, formato detectado,
tamanho, checksum, vínculo, responsável e estado ACTIVE/REVOKED. Bytes ficam
atrás de EvidenceStorage; ids UUID gerados pelo servidor são as únicas chaves
de storage. Consulta paginada e download autenticado não expõem caminhos/URLs.
Não guardar payload bruto, cabeçalhos ou dados adicionais do recebedor.

`RECOMENDAÇÃO`: UNIQUE (recorded_by, event_id), fingerprint de delivery/kind/bytes
e lock operacional serializam reenvios; a mesma identidade e conteúdo retornam
o mesmo registro/responsável. Conteúdo/entrega/tipo diferentes geram conflito,
mesmo quando revogado. Outra event_id representa novo registro explícito; checksum
não substitui identidade do evento. Ocorrências simultâneas preservam unicidade
no PostgreSQL. OC83 autentica/resolverá o ator pelos ports da OC79 antes deste
service; nenhum webhook, catálogo novo ou bypass de sessão é criado na OC80.

`RECOMENDAÇÃO`: storage.write só ocorre depois de autorização/validação e flush
do registro. Falha antes do commit desfaz metadata e remove o objeto recém-criado;
compensação falha é logada sem segredo e deixa objeto inacessível sem referência.
Não se promete transação distribuída. Service precisa de Session dedicada que
possua o commit real; não pode usar commit de savepoint como confirmação de IO.
Futura coordenação externa/outbox deve preservar essa fronteira.

`RECOMENDAÇÃO`: revogação lógica idempotente mantém vínculo, ator e horário
originais, acrescenta revoked_by/revoked_at e impede download. Não há endpoint
de exclusão física ou reativação. Registro e histórico permanecem auditáveis.
Bytes revogados são retidos no adapter local; podem ser removidos apenas ao
descartar o ambiente de desenvolvimento inteiro, nunca como compensação de retry.

## Retenção, proteção e produção

`RECOMENDAÇÃO`: adapter local opt-in por EVIDENCE_STORAGE_DIR, somente APP_ENV=local;
diretório privado, sem publicação web, paths derivados de UUID e arquivos sem
follow de symlinks. Adapter fake isolado serve testes. Produção falha fechada
sem provider aprovado. Downloads usam attachment, MIME detectado e nosniff.
Logs nunca incluem bytes, base64, URL, caminho, assinatura visual ou secrets.

`PENDENTE DE DEFINIÇÃO`: equipe aprovar prazo legal/técnico de retenção de bytes
e metadata, base legal, criptografia/gestão de chaves, backups, purge verificado,
acesso e storage real antes de ativar produção. Não inventar prazo ou promessa de
apagamento. OC81 consome API; OC83 adapta mídia/identidade autenticadas à mesma
fronteira; storage genérico de anexos OC110 não é antecipado.

`RISCO IDENTIFICADO`: imagens podem conter dados pessoais. Revogação de acesso
não equivale a apagar bytes/backups; falha de compensação requer limpeza técnica
de órfãos no provider. Não há antivírus, OCR, GPS ou verificação da identidade de
quem desenhou a assinatura. Aprovação desta ADR permanece necessária na revisão.
