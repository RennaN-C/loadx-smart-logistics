# Importação de cadastros — OC104

`CONFIRMADO`: [ADR-034](../../../../docs/decisions/ADR-034-importacao-cadastros.md).
Quatro fluxos create-only: customers, products, trucks, drivers. Pedidos,
upsert, reativação e XLSX ficam fora do escopo. Services públicos conservam
unicidade inclusive arquivados, endereço principal OC99, odômetro OC100 e CNH OC102.

## Arquivo

CSV UTF-8/BOM, vírgula ou ponto-e-vírgula, cabeçalhos do Create nativo. Template
contém todos os campos; obrigatórios presentes, opcionais omitidos/vazios usam
default/null. Extras/repetições recusados. Booleanos true/false/1/0, decimais com
ponto e datas ISO conforme schema. Limites: 1 MiB, 1000 registros, 4096 caracteres
por célula, base64 limitado antes de decodificar. Dimensões respeitam INTEGER
PostgreSQL (2147483647); odômetro conserva inteiro estrito. Encoding inválido,
binário/controles, colunas incoerentes e fórmulas recusados; telefone com + também
precisa atender à validação nativa. Nome não aceita caminho. Não executa código.

## HTTP

Prefixo /api/v1/registration-imports, ADMIN/LOGISTICS_MANAGER ativos somente.
Sessão, Origin e CSRF atuais preservados. CHECKER/DRIVER negados.

| Método | Caminho | Resultado |
|---|---|---|
| GET | /{entity_type}/template | CSV privado attachment/nosniff/no-store |
| POST | /{entity_type}/preview | ImportPreview sem persistência |
| POST | /{entity_type}/confirm | ImportRead COMPLETED ou REJECTED |
| GET | prefixo | PageResponse; entity_type, page/page_size/sort_order |
| GET | /{import_id} | Resultado, erros e UUIDs por linha |

Prévia recebe file_name/content_base64; confirmação acrescenta preview_sha256 e
event_id UUID. Prévia retorna linhas normalizadas, checksum, totais, can_confirm
e erros {line,field,code,message}, sem ecoar valor inválido. Linha é a posição
física inicial do registro; line=0 indica arquivo. Duplicidades são normalizadas.
Trocar arquivo exige nova prévia/evento; retry conserva evento e conteúdo.
Hash diferente: IMPORT_PREVIEW_MISMATCH 409; evento incompatível:
IMPORT_IDENTITY_CONFLICT 409; IMPORT_NOT_FOUND 404, AUTH_FORBIDDEN 403 e
VALIDATION_ERROR 422 usam envelope padrão. Arquivo inválido confirmado gera
REJECTED auditável, com zero cadastros criados.

## Transação e auditoria

Arquivo inteiro atômico, um commit externo. UNIQUE(ator,event_id) serializa
retries; constraints nativas arbitram unicidade concorrente. Savepoint inclui
cadastros, endereços, CNHs e auditorias internas. Unicidade concorrente desfaz
essa unidade e conserva somente resultado REJECTED/auditoria. Falha inesperada
ou de auditoria desfaz também a tentativa. Nunca commit por linha.
COMPLETED contém created_count=row_count, zero rejeições, UUID por linha;
REJECTED contém created_count=0, rejected_count=row_count, nenhum UUID criado.
CHECKs PostgreSQL protegem tipos, limites, status, contagens e arrays.
PROCESSING é interno, não publicado. IMPORT_COMPLETED/IMPORT_REJECTED registram
ator/data na mesma transação. Retry não duplica registros ou eventos.
Não persiste CSV, nome do arquivo nem valores pessoais nos erros/auditoria.

Migration 20261009_0022 → 20261009_0021, único head. Downgrade bloqueia qualquer
resultado/auditoria OC104, inclusive rejeições; sem perda silenciosa de histórico.

## Interface e testes

Ação contextual nos quatro cadastros, somente papéis autorizados: template,
seleção, prévia/erros paginados, confirmação explícita, resultado e histórico.
Backend decide autorização/integridade; disponibilidade e históricos anteriores
não são alterados.

PostgreSQL exclusivo TEST_DATABASE_URL: `python -m pytest
 tests/unit/test_registration_import_csv.py tests/integration/test_registration_imports.py
 tests/integration/test_openapi.py`.
Frontend: `npm test -- --run src/features/registration-imports`.
