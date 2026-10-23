# ADR-047 — Recuperação idempotente da otimização

Status: proposta técnica da #254/#256, implementada para revisão humana.
ADR-046 está reservada pela PR #262; esta decisão é independente dela.

## Contexto e decisão

`CONFIRMADO`: a execução continua síncrona. Uma resposta perdida não significa
rollback: repetir sem identidade pode criar outra distribuição. Não transformar
esta correção em fila de jobs nem alterar engine, limite de 200 volumes, dez
partes ou contratos OC90/OC94. Foram revisadas ADR-028, ADR-043 e ADR-045.

`RECOMENDAÇÃO IMPLEMENTADA`: `Idempotency-Key` UUID opcional no POST optimize,
compatível com clientes anteriores. O cliente LoadX sempre o envia. Escopo é
usuário autenticado + operação optimize (tabela exclusiva), não sessão, papel,
payload global ou segredo. Mesmo usuário após novo login pode recuperar.
Hash SHA-256 inclui versão do contrato e order_ids ordenados; a ordem não muda
a semântica, mas qualquer mudança na seleção exige outra chave. Duplicidades e
campos extras continuam recusados pelo schema antes da execução.

Registro (ator, chave, hash, distribution_id, created_at) e distribuição/planos/
volumes/histórico são confirmados no MESMO commit. Não há registro PENDING
confirmado antes do cálculo. Falha/rollback libera chave e não deixa job zumbi.
Registro só existe para sucesso; falhas podem ser tentadas novamente com a mesma
chave, revalidando fontes. Sem purge/TTL automático: não permitir que expiração
recrie uma operação histórica. Downgrade é recusado após uso do registro.

Lock transacional PostgreSQL advisory não bloqueante por ator/chave precede
preflight e escrita. Contenção retorna 409 OPTIMIZATION_IN_PROGRESS, sem iniciar
outro cálculo. Colisão de hash do lock pode produzir contenção conservadora,
nunca replay indevido: PK usa UUIDs completos. Chaves distintas conservam locks,
claims únicos e revalidação da OC87. Crash libera lock; commit concluído é
recuperável, rollback é seguro para repetir. Nenhum lock de sessão/conexão vaza.

Replay com hash diferente retorna 409 IDEMPOTENCY_PAYLOAD_MISMATCH. Replay igual
não calcula nem valida novamente pedidos já planejados: retorna a distribuição
persistida no estado ATUAL (inclusive cancelada), com os mesmos IDs. Não congela
resposta HTTP antiga nem reaplica aprovação. GET optimization-requests/{key}
retorna distribuição pessoal (200), 409 em processamento ou 404 sem sucesso
confirmado. POST permanece 201 também em replay para preservar contrato atual.
GET exige a mesma permissão create do POST e escopo estrito do ator, inclusive
ADMIN; chave alheia não identifica recurso. Autenticação, RBAC efetivo, MFA,
CSRF/Origin e auditoria existentes permanecem. Chaves não vão para logs novos.

Timeout de cliente/proxy é resultado indeterminado, não autorização para criar
nova chave. UI oferece consultar e repetir a MESMA requisição. Metadados locais
(ator, chave e seleção) em sessionStorage permitem F5 na mesma aba; não são
plano, autorização ou prova de persistência. Storage bloqueado mantém memória
sem impedir a operação. Nenhum token/credencial ou volume é armazenado. Sair da
aba/storage perdido exige procurar Planos existentes; recuperação em outro
cliente pode usar a chave pelo contrato, sem prometer rascunhos compartilhados.
Nenhuma execução automática ao montar tela nem polling contínuo.

## Limites e validação

`RISCO IDENTIFICADO`: cálculo lento continua lento; #262 não é incorporada.
Não há cancelamento de CPU pelo timeout, SLA HTTP, orçamento global novo ou job
assíncrono. 404 significa ausência de commit observável, não falha definitiva;
reenvio só é seguro com a mesma chave. Aprovação/alterações posteriores seguem
OC90/OC94; idempotência não substitui autorização nem invariantes físicas.

`CONFIRMADO`: testes PostgreSQL cobrem replay pós-commit/resposta perdida,
concorrência, payload divergente, isolamento, rollback, recuperação e migration.
Testes frontend cobrem erro indeterminado, retomada sem criação e chave estável.
