# ADR-034 — importação atômica de cadastros

Status: proposta técnica na OC104 (#151), sujeita à revisão do PR.

## Decisão e escopo

`CONFIRMADO`: quatro fluxos separados: clientes, produtos, caminhões e motoristas;
pedidos, endereços adicionais, manutenção, políticas/documentos adicionais e
reativação/atualização em massa não fazem parte da importação. Create-only usa
os schemas e services atuais, incluindo endereço principal OC99, odômetro
OC100, CNH/histórico OC102 e active OC105. Unicidade global inclui arquivados:
duplicado nunca reativa, substitui ou atualiza o registro existente.

`RECOMENDAÇÃO`: CSV UTF-8/BOM, delimitador vírgula ou ponto-e-vírgula, cabeçalhos
snake_case do Create atual; obrigatórios presentes, opcionais podem ser omitidos,
extras/duplicados recusados. Vazio opcional conserva default ou null, vazio
obrigatório gera erro. Booleanos true/false/1/0; decimais com ponto; datas ISO
com timezone conforme schema. Não há XLSX: a biblioteca csv já cobre o mínimo,
sem custo/manutenção de dependência ou execução de fórmulas.

`RECOMENDAÇÃO`: máximo 1 MiB decodificado, 1000 registros e 4096 caracteres por
célula. Base64 tem teto antes da decodificação. Recusar binários, encoding
inválido, NUL/controles, cabeçalhos/quantidade de colunas incoerentes e células
com prefixo de fórmula (=,+,-,@), exceto telefone com + e caracteres de máscara
numérica válidos. Não executar fórmulas, arquivos, URLs ou código. Não refletir
valores recebidos em template: download contém somente cabeçalhos aprovados.

## Prévia e transação

`CONFIRMADO`: preview não grava. Retorna SHA-256, linhas normalizadas, erros
por linha/campo, totais e can_confirm. Linhas usam posição física inicial no CSV,
incluindo campos multiline. Pydantic reutiliza as mesmas normalizações/regras
dos cadastros manuais; duplicidades do arquivo são verificadas após normalizar.
Consulta batelada pelos services públicos inclui registros ativos e arquivados.

`CONFIRMADO`: confirmação envia o mesmo CSV/hash e event_id UUID; revalida
conteúdo, autorização e unicidades atuais. Hash divergente retorna conflito sem
gravação. UNIQUE(ator,event_id) serializa confirmação/retry; evento incompatível
retorna 409, replay retorna resultado anterior sem outro cadastro/auditoria.
Ator ativo ADMIN/LOGISTICS_MANAGER é relido sob lock; CHECKER/DRIVER negados.

`CONFIRMADO`: cada service expõe stage_create sem commit para composição;
create manual usa o mesmo stage e conserva seu commit. Importação reclama o
evento, cria o arquivo inteiro em savepoint e faz um único commit externo.
Falha de unicidade concorrente desfaz todos os cadastros, endereços, CNHs e
auditorias internas do arquivo e persiste somente resultado REJECTED/auditoria.
Constraints de unicidade PostgreSQL continuam fonte de verdade. Falha inesperada
ou de auditoria desfaz também a tentativa; não há gravação parcial silenciosa
nem commit por linha. Resultado COMPLETED contém todos os UUIDs/linhas; REJECTED
tem created_count=0 e rejeita todas as linhas. PROCESSING não é publicado.

## Contrato e rastreabilidade

`CONFIRMADO`: prefixo /api/v1/registration-imports. GET /{entity_type}/template
(CSV privado), POST /{entity_type}/preview e /confirm, GET histórico paginado
com filtro entity_type e GET /{import_id}. Tipos do caminho são plurais em inglês.
Sessão, Origin, CSRF e envelopes de erros atuais preservados. Resultado e
auditoria guardam autor, instante, tipo, checksum, totais, erros sem valor e
linhas/UUIDs criados; não guardam CSV, nome do arquivo ou dados pessoais.
Só resultados de confirmações são persistidos; preview inválido nunca grava.

`CONFIRMADO`: UI contextual em cada cadastro: modelo, seleção, prévia, erros
por linha/campo, confirmação explícita, resultado e histórico. Trocar arquivo
limpa a prévia/evento; retry conserva evento. Frontend não decide integridade.

## Limites

`CONFIRMADO`: importação não reserva veículos/motoristas, não altera disponibilidade,
viagens, entregas, snapshots, políticas ou históricos anteriores. Não inventa
regras legais/categorias. Downgrade com resultados/auditoria é bloqueado.
`PENDENTE DE DEFINIÇÃO`: eventual XLSX, upsert, lotes acima do limite e retenção
de arquivos originais exigem contrato próprio; nenhum deles é ativado aqui.
