# ADR-031: documentos e elegibilidade documental dos caminhões (OC101)

Status: proposta para revisão humana no PR da Issue #148.

## Contexto

`CONFIRMADO`: OC100 centraliza bloqueios de manutenção no serviço de caminhões.
Issue #148 autoriza CRLV, licenciamento e seguro, validade, histórico e bloqueio
quando configurado; não define obrigatoriedade legal automática.

## Decisão técnica

`RECOMENDAÇÃO`: catálogo fechado CRLV, LICENSING e INSURANCE; cada caminhão
possui uma política explícita por tipo (`required`). Sem política habilitada,
documentos não bloqueiam veículos legados. ADMIN/LOGISTICS_MANAGER configuram
políticas e documentos; CHECKER consulta; DRIVER não acessa.

`RECOMENDAÇÃO`: documentos são versões imutáveis. Cadastro inicial cria uma
versão corrente por caminhão/tipo; renovação substitui somente a versão corrente
do mesmo tipo, mantendo UUID, dados e data de substituição da anterior. Índice
único parcial protege a versão corrente mesmo fora do serviço. Não há DELETE.
Número/referência é obrigatório; emissão e validade UTC são opcionais e, quando
ambas presentes, validade deve superar emissão. Uma versão com emissão futura
não é válida ainda; validade é exclusiva (vencido em `expires_at`). Validade
não informada não supõe expiração. Alerta próximo usa 30 dias inclusivos; é
informativo, sem envio externo, preparado para OC103.

`RECOMENDAÇÃO`: política habilitada exige uma versão corrente válida; ausência,
emissão futura ou vencimento bloqueiam novas operações. Alterar política ou
renovar documento não interrompe operações iniciadas. Aprovação, cálculo,
carregamento e início de viagem consultam a mesma fronteira pública
`TruckService.ensure_operational_eligibility`; disponibilidade compõe cadastro,
conflitos operacionais, manutenção e documentos sem persistir `available`.

`RECOMENDAÇÃO`: `file_reference` é UUID opaco opcional, referência de metadados,
nunca caminho, URL, chave de storage ou link público. Esta OC não publica nem
faz upload/download de bytes; a infraestrutura atual de evidências é exclusiva
de entregas e não é reutilizada como cadastro documental. Resolver/anexar bytes
exige adapter aprovado futuro; nenhuma existência ou verificação de arquivo é
inferida de uma referência. UI identifica explicitamente essa limitação.

## Consistência e compatibilidade

`RECOMENDAÇÃO`: políticas e versões bloqueiam a linha do caminhão antes de
escrever, assim como reservas e inícios operacionais. Auditoria e substituição
são atômicas; falha reverte tudo. Atualização idempotente de política não gera
novo evento. Constraints protegem tipos, período, FK e versão corrente. Sem
novos estados de pedidos ou mudanças em históricos OC99/OC105.
Downgrade recusa descartar documentos, políticas ou auditoria OC101.

`PENDENTE DE DEFINIÇÃO`: obrigatoriedade legal por tipo/empresa, integração de
arquivos e envio de notificações OC103. A política explícita permite gestão
aprovada sem impor essas regras a cadastros existentes.
