# ADR-043: entregas por parte física de distribuição

Status: proposta implementada para revisão na OC90 (#133).

## Contexto

`CONFIRMADO`: ADR-028 preserva a identidade `(order_item_id, volume_index)` no
planejamento e delega à OC90 a liberação operacional. A UNIQUE global de
Delivery.order_id não representa um pedido dividido entre caminhões. Reutilizar
a mesma entrega impediria concluir, comprovar e auditar cada perna independentemente.

## Decisão implementada para revisão

`RECOMENDAÇÃO`: Delivery recebe `distribution_part_id` opcional, derivado pelo
servidor do plano operacional atual. Não há nova tabela de volumes, status de
pedido ou motor de carregamento. Uma parte aprovada possui um plano atual,
um carregamento, uma viagem e até uma entrega por pedido efetivamente presente.
Partes de distribuições com um caminhão usam o mesmo contexto; planos sem
distribuição conservam NULL e a unicidade legada por pedido.

`CONFIRMADO`: FK RESTRICT, UNIQUE parte/pedido, índice único parcial legado e
triggers na revisão 0027 protegem a estrutura. A validação de atribuição bloqueia
Order antes de consultar outras entregas e toma SHARE na viagem/parte/distribuição.
Rejeita plano incompatível, parte não operacional, pedido sem volume e mistura
com entrega legada ou outra distribuição. Vínculos da entrega e plano de viagem
com entregas são imutáveis. Guardas nos pais serializam alterações estruturais
pela distribuição e impedem alterar sua partição/status após a primeira entrega.
As constraints OC87 continuam provando cobertura e identidade exata do plano.
Exclusão administrativa de histórico não é disponibilizada por API.

`CONFIRMADO`: aprovação mantém PLANNED. Início das viagens serializa pedidos em
UUID crescente e muda somente os PLANNED para IN_TRANSIT. Na conclusão, a ordem
é a já existente viagem → entregas dessa viagem (UUID) → pedido/itens (UUID).
Nenhuma conclusão bloqueia entregas de outra viagem: após o lock de Order,
persiste a perna e consulta por escalares as partes entregues em READ COMMITTED.
As partes necessárias vêm da fronteira pública de planejamento, incluindo partes
sem viagem/entrega. Apenas a última perna necessária muda o pedido para DELIVERED.
Histórico é gravado somente para transição efetiva, no mesmo commit. Uma viagem
multi termina pelas próprias entregas; o legado ainda verifica também o pedido.

`CONFIRMADO`: não há ciclo de espera entre conclusões de pernas: a transação
que possui o pedido nunca tenta bloquear outra viagem/entrega. Escritas de
planejamento seguem distribuição → caminhões → planos → pedidos/itens → produtos;
partições aprovadas permanecem imutáveis e não são reprocessadas durante operação.
Os SHARE de atribuição protegem o contexto contra escrita direta concorrente.

`CONFIRMADO`: comprovante ADR-024 continua projetando a conclusão única de cada
Delivery. PDFs identificam distribuição, parte, plano, caminhão e volumes da
própria parte. Auditoria durável usa os relacionamentos e StatusHistory existentes.
ADR-025 permanece intacta: nenhum ID de domínio/PII ou payload é adicionado aos
logs operacionais. Permissões efetivas OC112 e vínculo de motorista permanecem.

## Migração e consequências

`CONFIRMADO`: upgrade conserva entregas legadas e associa entregas operacionais
OC87 de uma parte ao vínculo existente. Downgrade vazio/legado é reversível;
qualquer entrega com parte bloqueia o downgrade antes de DDL, evitando perda de
contexto e retorno a um runtime incapaz de operar múltiplas pernas. Usar migration
compensatória quando necessário; nunca apagar auditoria para forçar rollback.

`PENDENTE DE DEFINIÇÃO`: aceite formal desta ADR pela equipe. Cancelamento,
reentrega e correção de operação (OC94) devem considerar essas guardas e não
remover integridade nem reabrir pernas concluídas implicitamente. UI OC89 permanece
compatível com campos aditivos e não é implementada nesta ocorrência.


`CONFIRMADO` (correção de integridade OC90): a primeira LoadingSession persistida
marca a imutabilidade operacional do LoadPlan; a existência de Trip também é
verificada defensivamente, incluindo planos legados. A função PostgreSQL
`protect_operated_load_plan()` protege UPDATE/DELETE da linha inteira de
`load_plans` e INSERT/UPDATE/DELETE de `load_plan_orders` e `load_plan_items`.
Os triggers `protect_operated_load_plans`, `protect_operated_load_plan_orders` e
`protect_operated_load_plan_items` rejeitam mudanças com SQLSTATE 23514 e
constraint `ck_load_plans__operational_snapshot`. UPDATE sem mudança real é
permitido. Ambos os pais são verificados em reatribuições; não há lista parcial
de colunas editáveis, cópia de volumes ou alteração do contrato HTTP.

`CONFIRMADO`: criação de LoadingSession serializa pelo LoadPlan FOR UPDATE,
recarrega snapshots/itens do identity map após o lock e só então materializa o
checklist e adquire o caminhão. Trip create já adquire plano antes de caminhão,
motorista e pedidos. Escrita direta de filho pode já possuir lock da tupla antes
da trigger; por isso a guarda tenta pais em UUID crescente com FOR UPDATE NOWAIT.
Contenção rejeita a mutação com a mesma constraint e mensagem para repetir a
transação, inclusive antes da operação. Não espera por um pai que possa estar
aguardando a FK do checklist nesse filho, evitando esse ciclo. A guarda não
bloqueia sessão, viagem, distribuição ou pedido; apenas consulta evidências
persistidas. Planejamento sem evidência operacional conserva criação, aprovação
e reprocessamento permitidos. Constraints e locks de contexto/distribuição
existentes permanecem; o congelamento do snapshot físico começa no loading,
antes da primeira entrega que protege a estrutura da distribuição.
