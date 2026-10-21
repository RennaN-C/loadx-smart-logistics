# ADR-038: recuperação de acesso e MFA standalone — OC98

Status: aceita para implementação no escopo aprovado da Issue #145.

## Decisão

`CONFIRMADO`: standalone mantém identidade em auth/users; domínios logísticos
não recebem credenciais. ADMIN e LOGISTICS_MANAGER exigem TOTP. CHECKER e DRIVER
podem ativá-lo voluntariamente. Senha correta de perfil sensível emite somente
um desafio opaco restrito de cinco minutos, nunca cookie de sessão. O primeiro
acesso exige cadastrar autenticador e comprovar posse; contas existentes não
possuem exceção. A migration revoga sessões antigas dos perfis sensíveis.

TOTP segue RFC 6238, SHA-1, seis dígitos, período de 30 segundos e tolerância de
um período para cada lado. O último contador aceito é persistido sob lock de
usuário: nenhum código aceito pode ser reutilizado. Segredos aleatórios de 160
bits são criptografados com Fernet (cryptography), chave própria
MFA_ENCRYPTION_KEY, distinta de SECRET_KEY, fornecida por cofre/secrets. Não há
fallback em texto puro. Rotação exige recriptografia controlada antes de retirar
a chave antiga; perda da chave impede validação, não autoriza bypass.

Desafios guardam somente SHA-256 da credencial, fingerprint do hash da senha,
papel e versão de segurança. Cinco falhas os consomem. Throttling durável por
conta/origem permanece independente da emissão de novos desafios. Locks seguem
usuário primeiro. Consumo/emissão bloqueia fatores/desafios/códigos antes das
sessões; gestão revalida a sessão própria sob o mesmo lock de usuário antes
de verificar fatores. Nenhum desses fluxos obtém conta alheia. Revogação integral invalida
simultaneamente todos os desafios. Emissão de sessão e consumo do desafio
compartilham transação. Mudança concorrente de senha, papel, atividade ou sessão
invalida a autorização intermediária.

Ativação entrega dez códigos aleatórios individuais de 128 bits, uma vez,
armazenados somente como SHA-256. Consumo é atômico. Regeneração exige senha e
segundo fator; invalida os anteriores. Troca/desativação exige senha e TOTP ou
código de recuperação, revoga todas as sessões e desafios. Perfil obrigatório
precisa cadastrar novo fator no próximo login antes de acessar o sistema.
Reset de senha nunca desativa MFA. Sem dispositivo, usar código de recuperação;
sem dispositivo e sem códigos, acesso permanece bloqueado. Não existe reset de
MFA por simples papel ADMIN. Contingência assistida exige identificação externa,
duplo controle, backup e procedimento operacional auditado aprovado; não há
endpoint administrativo de bypass nesta OC.

Recuperação usa token CSPRNG de 256 bits, SHA-256 no banco, validade de quinze
minutos e consumo único sob lock. Reenvio limitado; novo pedido invalida tokens
anteriores. Solicitações e confirmações usam contadores duráveis por conta e
origem com política progressiva da ADR-020. Resposta 202 é neutra para contas
existentes, inexistentes e inativas; entrega ocorre fora da resposta, sem afirmar
que houve envio. Sem adapter configurado, 503 igual para todas as contas. SMTP
real exige TLS autenticado, timeout e URL pública aprovada; fake somente em
testes. Token vai no fragmento do link, nunca na query/path de API, logs ou
resposta. O frontend remove fragmento do histórico após capturá-lo em memória.
Expiração, invalidade e reutilização possuem o mesmo erro. Nova senha usa política
central; hash, consumo e revogação integral/auditoria são uma transação.

E-mail da conta só muda com confirmação da senha e segundo fator para contas
com MFA, para impedir tomada de recuperação por sessão roubada. Mudanças de
identidade invalidam tokens de recuperação pendentes. Eventos estruturados
contêm somente UUIDs, tipo e resultado, sem segredos/identificadores brutos.

## Fronteira futura

`CONFIRMADO`: no modo integrado, CoreFlow/IdP assumirá senha, MFA e recuperação;
LoadX consumirá identidade confiável e aplicará autorização logística. Endpoints
locais serão desabilitados por contrato futuro, sem segunda senha/autenticador.
Nenhum segredo JWT, cookie, hash, TOTP ou credencial será compartilhado. SSO não
é implementado aqui.

## Limites e infraestrutura

`RISCO IDENTIFICADO`: SMTP, entrega, sincronização NTP, TLS externo, retenção de
eventos, custódia/rotação de chave e contingência assistida exigem infraestrutura.
Não há envio simulado em produção nem alegação de entrega garantida. Provisionar
MFA_ENCRYPTION_KEY antes da integração: sem ela login sensível falha fechado.
URI/códigos/desafios ficam somente em memória no navegador; F5 no desafio exige
novo login, F5 após autenticação restaura a sessão normal da OC92.

`CONFIRMADO`: revisão técnica também invalida recuperação/desafios pendentes
quando identidade é alterada pelo service público users (inclusive edição ADMIN)
e em revogação de sessões. Gestão do fator bloqueia usuário antes de seus
contadores, preservando a mesma ordem quando chamada durante edição de perfil.

`CONFIRMADO`: a revisão do algoritmo distingue HMAC-SHA-1 (RFC 4226/6238,
compatível com autenticadores comuns) de hash SHA-1 independente. O cálculo
usa `hmac.digest` da biblioteca padrão, com chave CSPRNG de 160 bits, truncamento
RFC e janela/antirreplay/budget. Não usa SHA-1 para senha, token ou código de
recuperação. Ataques de colisão a SHA-1 não permitem forjar esse MAC com chave
secreta; vetores oficiais verificam a construção. Não há supressão do scanner
ou alteração das regras de segurança para aceitar hash fraco.

`CONFIRMADO`: o evento de consumo de código de recuperação só é emitido após
commit. Falha/rollback de auditoria ou atualização não declara consumo que não
ocorreu; testes verificam simultaneamente estado PostgreSQL e logs.

`CONFIRMADO`: emissão de sessão por senha também revalida papel/fator sob lock
de usuário. O hash comparado é o hash efetivamente verificado, não um atributo
ORM recarregado após commit. Promoção para perfil obrigatório, ativação MFA ou
mudança de senha concorrentes impedem emissão sem segundo fator. Testes injetam
essas mudanças exatamente após liberar locks dos contadores e antes da emissão.

`CONFIRMADO`: ativação MFA revoga também sessões por senha emitidas enquanto o
cadastro voluntário estava pendente. O gate de sessão bloqueia a linha do fator
e recarrega seu estado, além da conta, antes de emitir sessão por senha.

## Complemento — QR local e SMTP de desenvolvimento

`CONFIRMADO`: a URI de provisionamento já autorizada pelo servidor é renderizada
como QR SVG no navegador por `qrcode.react`, sem rede, analytics ou persistência.
Preparação é explícita e única por desafio na UI; rerender não rotaciona segredo.
Chave manual/cópia permanece disponível, com fallback sem clipboard. Expiração
remove credenciais da tela e permite novo login; servidor continua autoritativo.

`CONFIRMADO`: SMTP de produção suporta TLS direto (465) ou STARTTLS obrigatório
(587), ambos autenticados e com validação de certificado/hostname e TLS >=1.2.
Não há downgrade. Exceção estritamente local: Mailpit opcional, sem TLS e sem
credenciais, somente `APP_ENV=local` e host de loopback ou serviço `mailpit`.
HTTP é aceito exclusivamente na URL exata
`http://localhost:5173/password-reset`, somente local. Produção continua HTTPS.
Mailbox e SMTP Docker são publicados apenas no loopback. Essa infraestrutura
não é provedor externo nem confirmação de entrega real; não altera tokens,
rate limiting, auditoria, sessions, MFA, OC112 ou schema. Configuração e roteiro
estão no README auth; não se troca a chave de criptografia existente.

## Dispositivo confiável — Issue #222

`CONFIRMADO`: recurso opt-in, desabilitado por padrão (`TRUSTED_DEVICES_ENABLED`).
Quando habilitado, a etapa LOGIN oferece confiança por 30 dias (configuração
`TRUSTED_DEVICE_DAYS`, intervalo 1–30). ENROLL e código de recuperação nunca
criam confiança, mesmo se o cliente enviar opt-in. Somente TOTP válido, sem
replay, cria a credencial na mesma transação de consumo do desafio e emissão da
sessão. Não existe isenção no primeiro cadastro obrigatório. A senha continua
obrigatória em toda nova autenticação, antes da consulta de confiança. Sessão
normal preserva idle de 30 minutos e limite absoluto de 8 horas.

Credencial CSPRNG de 256 bits em cookie próprio HttpOnly, SameSite=Lax, Path=/,
sem Domain, Secure em produção e prefixo `__Host-`. Local HTTP usa nome sem
prefixo. Expiração absoluta e Max-Age seguem o prazo configurado; uso nunca
renova esse prazo. Proxy same-origin `/api` não modifica Path/Domain. PostgreSQL
guarda apenas SHA-256 do token e um vínculo SHA-256 com hash da senha, papel,
perfil CUSTOM e segredo cifrado/estado atual do fator. Não usa IP/User-Agent
como identidade, nem persiste TOTP, senha, recuperação ou token em claro.
A `security_version` do desafio atual muda a cada login e não é versão durável
adequada à confiança: conserva-se seu comportamento, sem revogar outro navegador
por um login comum. A vinculação à credencial/fator é reforçada por revogação
transacional em toda mudança de segurança, inclusive reversões.

Troca/reset de senha, alteração de e-mail/papel/perfil, desativação da conta,
alteração de permissões do perfil CUSTOM, troca/desativação do fator, regeneração
de códigos e revogação explícita de sessões invalidam a confiança. Logout comum
preserva o cookie e não amplia sessão. A confiança não substitui senha/TOTP na
reautenticação de operações sensíveis. Sem cookie válido, fator ativo, storage
ou chave MFA, não se emite sessão por confiança. Desabilitar a flag impede
emissão e uso imediatamente; gestão/revogação continua acessível.

Locks seguem a conta antes de fator/dispositivo/sessão; o gate de emissão
revalida senha, conta, fator e dispositivo sob esses locks. Último uso, auditoria
e sessão compartilham commit; falha não deixa confiança/sessão parcial. Emissão
substitui a credencial anterior própria após TOTP e mantém no máximo vinte
ativas por conta, revogando as mais antigas deterministicamente. Não altera o
cookie de outra conta até opt-in válido da conta atual. Listagem expõe somente
UUID, criação, último uso, expiração e indicador do navegador atual. Identificação
visual usa UUID parcial, sem inferir marca de aparelho/localização.

Gestão própria exige sessão, Origin e CSRF. Remoção individual/todos/atual é
idempotente e sempre limitada ao usuário da sessão; UUID alheio equivale a
inexistente. Remover confiança não encerra a sessão atual: invalida o próximo
bypass imediatamente. Auditoria de criação/uso/remoção explícita registra
USER_UPDATED sem valores secretos; invalidações derivadas compartilham a
transação/auditoria da mudança de segurança que as causou. Eventos JSON próprios
são emitidos somente após commit, com UUIDs e contagens. Histórico revogado é
preservado; downgrade bloqueia tabela populada. Sem nova dependência externa.

`RISCO IDENTIFICADO`: cookie roubado junto da senha pode substituir o fator até
revogação/expiração. Não usar em navegador compartilhado; logout sozinho não
remove a confiança. Não há identificação por hardware, proteção contra cópia do
cookie ou sincronização automática entre dispositivos. Ativação em homologação
requer aplicar migration e configurar a flag no ambiente aprovado, fora desta
entrega sem deploy. Bases legadas precisam reconciliação preservadora antes de
upgrade; não fazer stamp/reset.

## Reconciliação com a base operacional integrada — 21/10/2026

`CONFIRMADO`: a PR #211 permanece aberta para revisão. A reconciliação preserva
os commits anteriores da OC98/#222 e incorpora `desenvolvimento` com OC84,
OC103, OC109 e OC90. O head integrado `20261020_0028` permanece intacto;
as duas revisões ainda não integradas passam a `20261021_0029` (OC98) e
`20261021_0030` (#222), formando uma única cadeia. Não há alteração dos estados,
snapshots, notificações, outbox ou regras de entregas da base operacional.

Preferências da OC103, segurança MFA e dispositivos confiáveis coexistem em
Meu perfil. Configuração e eventos de segurança conservam tanto os contratos de
identidade quanto os de webhook/outbox. Pillow 13 e os hashes dos lockfiles da
base atual são preservados. Testes de rollback também verificam a permanência
de destinatários, outbox e proveniência das entregas multi-caminhão.

`RISCO IDENTIFICADO`: bases de homologações antigas que executaram IDs
experimentais desta PR precisam de reconciliação específica e preservadora.
Esta entrega não atualiza essas bases, não troca suas chaves, não usa `stamp`
e não reseta dados. O caminho oficial é validado em PostgreSQL 16 exclusivo,
a partir de 0028; downgrade após uso continua bloqueado para preservar identidade.
