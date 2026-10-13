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
usuário → fatores/desafios/códigos → sessões; revogação integral invalida
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
