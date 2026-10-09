# ADR-029: endereços reutilizáveis e destino contratado do pedido

Status: aceita para a v1.2.0 standalone em 09/10/2026 (OC99, PR #175). As regras documentadas estão integradas; integrações futuras não são aprovadas implicitamente.

## Contexto

`CONFIRMADO`: o cliente possui um endereço textual com cidade/UF. O pedido tem
seu próprio delivery_address e deve manter o destino contratado, mesmo após
alteração cadastral. A Issue #146 autoriza múltiplos endereços e seleção explícita
sem geocodificação, roteirização ou dependência nova. OC105 define arquivamento
lógico e a matriz atual permite gestão por ADMIN e LOGISTICS_MANAGER.

## Decisão implementada

`CONFIRMADO`: customer_addresses pertence a customers, com UUID próprio,
cliente, rótulo, texto, cidade, UF, CEP opcional, active e is_primary. Não existe
exclusão física. Cada cliente com ativos mantém um principal; primeiro ativo é
principal, troca desmarca anterior e arquivamento promove o ativo mais antigo
(created_at, id). Sem ativos, permanece o último texto legado conhecido.

`CONFIRMADO`: preservar customers.address/city/state como projeção do principal
mantém consumidores existentes. Criação/PATCH legado sincroniza esse endereço
na mesma transação. Cadastro legado não inventa CEP. Consulta ViaCEP existente
é auxiliar; preenchimento manual continua possível.

`CONFIRMADO`: orders seleciona pelo serviço público de customers, que bloqueia
cliente e endereço, valida estado/pertencimento e retorna uma cópia. FK composta
(customer_address_id, customer_id) protege origem, UNIQUE parcial protege um
principal e CHECK exige principal ativo. Alterações são serializadas pelo lock
do cliente, antes dos endereços. Falha faz rollback da projeção, endereço e
auditoria. Eventos de endereço identificam ator, entidade e campos, sem copiar
dados pessoais para o evento.

`CONFIRMADO`: pedido guarda texto original e snapshot JSONB com rótulo, texto,
cidade, UF, CEP e UUID da origem. POST aceita seleção ou texto legado, nunca
ambos. Campos omitidos no PATCH DRAFT preservam a cópia; seleção explícita
recontrata o destino, texto explícito desfaz a proveniência. Troca de cliente
exige destino explícito. Cadastro alterado/arquivado não reescreve pedidos,
planos, carregamentos, viagens, entregas ou evidências. Sem novo estado de pedido.

`CONFIRMADO`: migration 20261008_0017 segue 0016, cria um principal por cliente
sem alterar seu estado e copia para pedidos antigos somente seu delivery_address.
Não inferir UUID/cidade/UF a partir do cadastro atual evita história fabricada.
Downgrade seguro cobre backfill intocado; se descartaria dados novos, é bloqueado
na mesma transação conforme proteção adotada na OC105.

## Consequências

`CONFIRMADO`: endpoints antigos e resumo minimizado permanecem compatíveis;
novos campos aparecem somente na leitura detalhada. A API oferece filtro
explícito para arquivados; seleções operacionais usam ativos. Frontend mantém
texto manual e preservação do destino na edição, apresentando erros da consulta.
ADMIN e LOGISTICS_MANAGER gerem endereços, CHECKER/DRIVER não consultam cadastro;
leitura de destinos contratados segue o RBAC já existente dos pedidos.

`RISCO IDENTIFICADO`: SQL externo pode deixar cliente sem principal apesar de
haver ativos; a constraint garante no máximo um principal, e o serviço garante
exatamente um. Integrações devem usar os serviços públicos. Após uso da OC99,
downgrade automático não remove cadastros/histórico; eventual reversão requer
estratégia explícita de preservação de dados.
