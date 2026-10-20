# ADR-041 — notificações duráveis e tentativa mock após commit externo

Status: direção aprovada com condições pela revisão de Rennan na PR #226,
comentário 6289881953; implementação sujeita ao aceite final, sem autorização de merge.

## Contexto

`CONFIRMADO`: ADR-026 compõe domínio dentro de savepoints de uma transação externa.
Um Session.commit interno não comprova durabilidade. ADRs 036/037 mantêm WhatsApp
mock, mas exigem que fatos/notificações internas sejam reais. OC83 e OC89 já estão
integradas; OC90/OC98 não são incorporadas por esta decisão.

## Decisão aplicada

`CONFIRMADO`: operational_notifications pertence ao módulo notifications. Registra
apenas início efetivo da viagem e ocorrência persistida, usando os UUIDs originais
de status_history ou occurrences e o motorista operacional da mesma viagem.
Fato, histórico e notificação são atômicos; falha do registro reverte o domínio.

A existência da linha confirma somente o registro interno. mock_status tem
NOT_ATTEMPTED, ATTEMPT_CLAIMED, SIMULATED, FAILED e NO_RECIPIENT. Não representa
lida/não lida ou entrega externa. Unicidade parcial por tipo/origem/motorista,
CHECKs, FKs RESTRICT e triggers validam proveniência, identidade imutável e estados.
Não são armazenados telefone, conteúdo ou credenciais.

`CONFIRMADO`: as composições de HTTP e OC79 despacham após o commit externo.
Session ligada à Connection não autoriza dispatch. A OC79 transfere hints para o
dono da transação, que só então chama dispatch com Sessions novas ligadas ao Engine.
A atualização condicional do claim é persistida antes da simulação e só um processo
vence. Destinatário/vínculo/atividade são revalidados sob locks de viagem/motorista;
a simulação não é redirecionada se o vínculo mudou. Falha do provider não reverte
domínio. Replay de comando externo não cria registro ou tentativa adicionais.

`CONFIRMADO`: sender é adapter de formatação/telemetria mock; não é API de domínio.
Não adicionar endpoint, destinatário novo, template pago ou envio Meta. O simulador
mantém sua confirmação explícita e não recebe aviso automático duplicado.

## Limites e consequências

`RISCO IDENTIFICADO`: crash antes do claim deixa NOT_ATTEMPTED; depois do claim ou
na persistência do resultado deixa ATTEMPT_CLAIMED. Não simular sucesso ou repetir
automaticamente. Hints em memória podem se perder, mas a notificação permanece no
PostgreSQL. Esta composição não promete exactly-once nem processamento eventual.

`CONFIRMADO`: OC109 definirá recuperação/outbox/retries; OC103 definirá leitura,
preferências e autorização interna por destinatário. Sem conta de usuário vinculada,
o motorista continua sendo identidade operacional e não ganha permissão HTTP.
Uma composição externa nova deve assumir a responsabilidade pelo commit/dispatch.

`CONFIRMADO`: migration 20261020_0025 encadeia o head 20261016_0024, sem backfill ou
mudança de estados logísticos. Downgrade com notificações é recusado. PostgreSQL 16
é a fonte de verdade e a suíte testa concorrência, rollback, origem e savepoints.
`PENDENTE DE DEFINIÇÃO`: aceite humano final da implementação na PR #226.
