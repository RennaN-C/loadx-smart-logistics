# Feature: trucks

Listagem e cadastro de caminhões (OC26) e o painel de situação da frota (OC73).
Consome `GET/POST/PATCH /trucks` e `GET /trucks/operational-status`.

## O que existe hoje

- `pages/TruckListPage.tsx` (+ `.css`): tabela responsiva paginada, busca e filtro de
  arquivamento no servidor antes da paginação (OC95), estados de carregando/vazio/erro e o
  modal de cadastro.
- `components/TruckCard.tsx`: placa, modelo, status, desenho técnico e specs de um caminhão.
- `components/TruckForm.tsx`: criação e edição, com pré-visualização do desenho e do volume interno
  atualizando conforme as medidas são digitadas.
- `components/TruckSchematic.tsx`: ilustração do baú (vista lateral e traseira) com as cotas do cadastro.
  As imagens ficam em `frontend/public/trucks/` e são **fixas**: não deformam conforme as medidas. O que
  muda é só o valor das cotas ao lado do desenho — decisão de produto, o desenho situa quem cadastra e o
  número é que carrega a informação. As imagens são decorativas (`alt=""`), então nada de acessibilidade
  depende delas.

  Ficam em `public/` (e não em `src/assets/`) de propósito: assim uma imagem ausente não quebra o build.
  Devem ser PNG com fundo transparente e recortadas na silhueta do caminhão — o CSS as encaixa com
  `object-fit: contain` e `object-position: bottom`, para as duas vistas ficarem apoiadas no mesmo chão.
- `pages/FleetStatusPage.tsx` (+ `.css`): painel de disponibilidade (OC73), incorporado à área de caminhões.
- `components/fleetStatusLabels.ts`: como a situação do caminhão vira rótulo e tom.
- `components/trucksErrorMessages.ts`: tradução dos códigos de erro do backend.
- `api/trucksApi.ts`: mapeamento snake_case ↔ camelCase.
A carga paginada vem de `hooks/useResourceList` (compartilhado). O `useTrucks` desta feature
deixou de existir quando o hook virou genérico, na OC28.

`CONFIRMADO`: `max_weight_kg` é consumido e enviado como `number`, sem união com
`string` ou coerção no adapter, conforme D06 e ADR-016.

## Painel de situação da frota (OC73)

`CONFIRMADO`: `GET /trucks/operational-status` devolve, por caminhão, `active`,
`has_operation_conflict` e `available`. O `available` chega **calculado** —
`fleet/service.py` o compõe a partir das regras de conflito da OC64, que
pertencem ao módulo de caminhões.

**A tela não refaz essa conta.** `active` e `has_operation_conflict` servem só
para EXPLICAR por que um caminhão não está disponível. Repetir a fórmula aqui
criaria uma segunda fonte de verdade, e no dia em que a regra mudar no backend a
frota pareceria uma coisa neste painel e outra no planejamento. Há teste que
passa uma combinação impossível pela regra de hoje (conflito **e** disponível) e
exige que a tela obedeça.

Os dois motivos podem valer ao mesmo tempo — caminhão arquivado que ainda está
numa operação —, e nesse caso os dois aparecem. Quando o backend recusa sem
apontar motivo que esta tela conheça, ela diz "Indisponível" e para: inventar
causa seria pior que não explicar.

`RISCO IDENTIFICADO` (OC95): os contadores e available/unavailable permanecem
na **página carregada**, com aviso explícito. A fronteira pública calcula por ID
depois de paginar; movê-los exige evolução arquitetural sem duplicar regras
de conflito, documento ou manutenção e sem carregar toda a frota em memória.

`CONFIRMADO`: na manutenção #206, a disponibilidade integra **Caminhões e frota**
em Cadastros. O lote UI08 acrescenta a aba Documentação, que reutiliza o contrato
real por caminhão e exige a seleção do veículo em vez de simular uma coleção global.
As abas são Veículos, Disponibilidade e Documentação. O item separado Frota foi
removido; a mudança de organização não altera a fonte dos estados operacionais.

## Permissões

`ADMIN`, `CHECKER` e `LOGISTICS_MANAGER` leem a lista. `ADMIN` e `LOGISTICS_MANAGER` criam e editam — a UI
esconde "Novo caminhão" e "Editar" para os demais, mas quem barra de verdade é o backend.

`CONFIRMADO`: a listagem consome o envelope e parâmetros da ADR-017, com
busca server-side adicionada pela whitelist da OC95.

## Fora de escopo nesta ocorrência

Exclusão física (não existe rota; arquivar é
`active: false` via PATCH).

## OC105 — ciclo de vida

`CONFIRMADO`: a tela inicia em somente ativos, permite consultar arquivados ou
ambos pelo filtro `archive_status` no servidor, reiniciando na página 1. A busca
textual e as restrições aprovadas passaram ao servidor na OC95. Cards mostram Ativo/Arquivado.
ADMIN e LOGISTICS_MANAGER veem ações Arquivar/Reativar, que usam o PATCH existente, exibem
loading/erro e atualizam a listagem somente após sucesso. Os demais perfis
preservam as permissões de leitura e não recebem botões de gestão.

## OC101 — documentos e políticas

`CONFIRMADO`: `api/documentsApi.ts` mantém DTOs documentais snake_case para
não duplicar mapeamento. DocumentsPanel abre pelo card, lista histórico paginado
e políticas por CRLV/licenciamento/seguro; DocumentForm registra/renova sem
apagar versões. Datas locais do formulário são enviadas em UTC; status de
validade/alerta vem do backend. Política carregada só permite gestão a ADMIN e
LOGISTICS_MANAGER em caminhão ativo; erro de consulta não apresenta exigências
supostas. CHECKER e arquivados consultam histórico.

`CONFIRMADO`: frota explica has_document_conflict e planejamento oculta veículos
com bloqueio documental. UUID de arquivo é referência opaca de metadados;
não há link público, upload ou download. Notificações externas ficam na OC103.

## Área consolidada — manutenção #206

`CONFIRMADO`: `TruckWorkspacePage` monta os componentes existentes sem reescrever
cadastro, importação, arquivamento, documentos ou manutenção. `/trucks` abre
Veículos; `/trucks?tab=availability` abre Disponibilidade;
`/trucks?tab=documents` abre a consulta documental por veículo; `/fleet` é um alias
seguro para a segunda URL. ADMIN/LOGISTICS_MANAGER/CHECKER preservam leitura;
DRIVER não monta a área nem faz consultas protegidas.

`CONFIRMADO`: trocar abas mantém busca, paginação, filtros e rascunhos montados.
A disponibilidade é consultada ao visitar a aba pela primeira vez. Um modal
oculto libera foco/rolagem e retoma seu rascunho quando a aba é reaberta. Ao sair
da página/F5, consultas e estado temporário são reconstruídos a partir da API.
`available` nunca é recalculado. Filtros e contadores de disponibilidade seguem
restritos à página carregada, com aviso explícito.

## OC95 — pesquisa na coleção

`CONFIRMADO`: a tela envia `search` por plate e model.
Combina com `archive_status=active|archived|all`.
Mudança de busca/filtro volta à página 1; navegação/refetch preservam critérios.
A API usa SearchListParams e tipos específicos somente onde necessário; o
loader estável não refiltra items localmente. O total vem do conjunto filtrado.
Busca limitada a 120 caracteres; vazio/erro/loading permanecem tratados.
Nenhum campo pessoal proibido pela ADR-017 foi incluído no resumo ou na busca.
