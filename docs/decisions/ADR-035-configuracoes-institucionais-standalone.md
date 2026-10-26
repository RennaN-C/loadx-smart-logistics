# ADR-035 — Dados institucionais standalone (OC91)

Status: Aceita no escopo da Issue #136.

`CONFIRMADO`: a v1.2.0 é monoempresa. `company_profiles` contém no máximo um
registro, com UUID local fixo protegido por CHECK e PK. Esse ID não é tenant,
não é derivado de CNPJ/e-mail e não recebe FKs do domínio logístico.

O cadastro exige `legal_name` e `display_name` (1–160 caracteres). CNPJ numérico
validado pelo mecanismo existente, telefone com DDD, e-mail e `logo_reference`
são opcionais; vazio equivale a null. O logotipo é apenas referência HTTPS sem
credenciais, até 2048 caracteres: não há upload, binário, fetch do servidor nem
carregamento externo automático no frontend. Nenhum outro campo institucional
foi incluído.

GET `/api/v1/company-profile` devolve null antes do primeiro cadastro, sem
criação automática ou dados fictícios. PUT substitui os seis campos e devolve
o registro persistido; ambos são ADMIN-only, incluindo backend. Campos extras
são recusados. CSRF, sessão e origem seguem o middleware existente.

Primeira gravação usa INSERT ON CONFLICT e bloqueio da linha; atualização e
auditoria compartilham uma transação. PUT concorrentes são serializados, com
última gravação válida prevalecendo. Falha reverte cadastro e auditoria.
Eventos registram ator e nomes dos campos alterados, sem valores, segredos ou
URLs. Atualização idêntica não cria evento. O histórico institucional é
ADMIN-only; consultas gerais de auditoria do gerente excluem essa entidade.

Downgrade é permitido em banco sem dados dessa OC; com cadastro ou eventos,
falha explicitamente para preservar informação. Nenhum dado existente é
reescrito no upgrade.

No alvo futuro CoreFlow, esse registro poderá ser migrado ou tratado como
snapshot/cache mediante contrato próprio. Organização, identidade global,
tenancy, licenciamento, billing e SSO não são implementados aqui. Configurações
logísticas permanecem separadas.
