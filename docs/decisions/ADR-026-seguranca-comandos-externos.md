# ADR-026: segurança e idempotência de comandos externos

Status: proposta na OC79, sujeita à revisão do PR

## Contexto

`CONFIRMADO`: a Issue #122 exige uma fronteira reutilizável por OC82/OC83/OC84.
O simulador exige sessão/RBAC e não autentica remetentes externos. Os services
validam vínculo/estado, mas fazem commits próprios. Memória não serializa workers.

## Decisão

`RECOMENDAÇÃO`: `ExternalCommandService` é a entrada interna, sem rota HTTP ou
fornecedor habilitado. Um port autentica bytes originais e retorna identidade e
capabilities configuradas no servidor. Adapter HMAC-SHA-256 genérico usa comparação
constante e chave exclusiva por integração, independente da `SECRET_KEY`.

`RECOMENDAÇÃO`: subject assinado não é user_id. Um resolver associa o par
`(integration_id, subject)` a usuário por bindings do servidor. Papel, atividade
e vínculo são relidos sob bloqueio. Capability da integração não substitui RBAC
do usuário e autorização do objeto nos services públicos.

`RECOMENDAÇÃO`: catálogo fechado de comandos já existentes no MVP: START_TRIP,
START_DELIVERY e FINISH_DELIVERY, com target_id explícito de viagem/entrega.
ARRIVED pode ser normalizado antes de assinar como START_DELIVERY; consultas
STATUS/NEXT_DELIVERY ficam fora desta fronteira de comandos mutáveis.

`RECOMENDAÇÃO`: envelope versão 1 com event_id, subject, command, target_id,
issued_at e expires_at; sem campos extras ou chaves JSON repetidas. Máximo 16 KiB,
validade máxima cinco minutos, tolerância futura 30 segundos. Expiração exclusiva,
reverificada após espera por bloqueios. Assinatura inválida não consulta domínio.

`RECOMENDAÇÃO`: UNIQUE `(integration_id, SHA-256(event_id))` e INSERT ON CONFLICT
serializam duplicatas no PostgreSQL. Fingerprint dos bytes assinados e ator
resolvido devem coincidir: reenvio válido retorna o mesmo receipt, sem domínio;
bytes/ator incompatíveis retornam conflito; expirado é negado mesmo já concluído.
Registros concluídos não são removidos automaticamente. Retry após rollback não
consome identidade; permanece sujeito à validade e às regras de negócio.

`RECOMENDAÇÃO`: uma transação externa contém registro, efeito e histórico.
Session de domínio usa a mesma Connection e `join_transaction_mode=create_savepoint`:
commits existentes liberam savepoints sem confirmar a transação externa. Exceção
antes/depois do commit interno desfaz tudo. Não há IO externo nessa transação.

`RECOMENDAÇÃO`: códigos estáveis distinguem autenticidade, payload, validade,
autorização, conflito, estado e falha interna. Logs reutilizam eventos de segurança
com correlation_id gerado pelo servidor, command_id do receipt e código; não registram
assinatura, subject, event_id, payload, chave, telefone ou traceback. Receipt
contém somente id e indicação de duplicata; registro contém hashes e metadados.

## Consequências

`RECOMENDAÇÃO`: OC82/OC83 implementam autenticidade/bindings confiáveis via ports,
sem assumir identidade apenas por telefone. OC84 envia após commit; outbox/retry
externo pertence à OC109. Falha posterior de envio não reexecuta domínio.
Nenhuma mudança na sessão, CSRF, simulador, RBAC ou regra operacional existente.

`RISCO IDENTIFICADO`: chave comprometida permite falsificar subjects daquela
integração. Gestão segura, revogação e menor privilégio são responsabilidades da
composição do adapter. HMAC não cifra: transporte exige TLS. Não existe promessa
de exactly-once para efeitos externos, fornecedor real ou armazenamento de mídia.

`PENDENTE DE DEFINIÇÃO`: aprovação desta ADR e composição dos adapters reais nas
OCs correspondentes. Nenhuma integração fica habilitada por padrão na OC79.
