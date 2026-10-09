# Feature: drivers

Cadastro de motoristas (OC28). Consome `GET/POST/PATCH /drivers`.

## O que existe hoje

- `components/DriverPanel.tsx`: busca, filtro por status, grade paginada e modal de motoristas.
- `components/DriverForm.tsx`: criação e edição.
- `components/driversErrorMessages.ts`: tradução dos códigos de erro — o backend distingue
  documento duplicado de CNH duplicada, e as mensagens seguem essa distinção.
- `api/driversApi.ts`: mapeamento snake_case ↔ camelCase.

Esta feature **não tem página própria**: o painel é montado na aba "Motoristas" de
`features/customers/pages/ContactsPage.tsx`, conforme a OC28 pede uma tela só para os dois cadastros.

## A listagem devolve um resumo

`GET /drivers` responde `DriverListRead`: só `id`, `name`, `license_category`, `active` e `created_at`.
**Documento, telefone e número da CNH não saem na listagem.** Por isso o card mostra nome, categoria e
status; a busca cobre só o nome; e editar exige `GET /drivers/{id}` antes de abrir o formulário
(`hooks/useEditTarget`).

## Decisões

**Categoria da CNH é um `<select>`, não campo livre.** O backend aceita qualquer string de até 8
caracteres, mas só faz sentido oferecer as categorias que dirigem caminhão (C, D, E, AC, AD, AE) —
A é moto e B é carro de passeio. Continua opcional: "Não informada" envia `null`.

**CNH é campo só de dígitos.** O padrão da OC63 é `[0-9]{11}`, sem máscara
nenhuma — quem digitasse "012.345.678-90" levava 422 sem nada na tela sugerir
que pontuação era proibida. O campo filtra dígito e para em 11.

**O documento do motorista é CPF, não CPF ou CNPJ.** Motorista é pessoa física,
e o schema do backend usa `CPF`, enquanto o do cliente usa `CustomerDocument`.

**Telefone é obrigatório**, diferente do cliente. O vazio quem barra é o
`required` nativo; a regra da OC63 pega o que está completo e inválido, como DDD
zerado.

**`active` só aparece na edição**, igual a caminhões: a criação não expõe o campo, mesmo o schema
aceitando, porque o backend já assume `true`.

## Permissões

**Só `ADMIN` e `LOGISTICS_MANAGER` leem motoristas — `CHECKER` é bloqueado**, por serem dados
pessoais. ADMIN e LOGISTICS_MANAGER criam e editam.

## Fora de escopo

Busca e filtro server-side (D12): atuam só na página carregada. Exclusão não existe rota; desativar é
`active: false` via PATCH.

`CONFIRMADO`: o vínculo `users.driver_id` existe no backend, é administrado por
`ADMIN` e permite ao `DRIVER` ativo acessar suas viagens e entregas. Usuário
sem vínculo permanece sem acesso operacional, conforme `ADR-022`.

## OC105 — ciclo de vida

`CONFIRMADO`: a tela inicia em somente ativos, permite consultar arquivados ou
ambos pelo filtro `archive_status` no servidor, reiniciando na página 1. A busca
textual e as restrições continuam locais à página. Cards mostram Ativo/Arquivado.
ADMIN e LOGISTICS_MANAGER veem ações Arquivar/Reativar, que usam o PATCH existente, exibem
loading/erro e atualizam a listagem somente após sucesso. Os demais perfis
preservam as permissões de leitura e não recebem botões de gestão.

## OC102 — documentos

`CONFIRMADO`: Documentos no card abre histórico e renovação CNH, validade/categoria,
tipos adicionais aprovados e políticas explícitas. ADMIN/LOGISTICS_MANAGER
gerenciam ativos; arquivados preservam leitura. CHECKER/DRIVER não acessam API.
Status de vencimento/próximo do vencimento vem do backend e rótulos temporais
são compartilhados com OC101. Emissão/validade local são enviadas em UTC.
Categorias aceitas são selecionadas explicitamente; não se calcula classe de
veículo ou exigência legal. Novo tipo não ativa política automaticamente.
Loading/erro/vazio/paginação são tratados; erro de catálogo não supõe política
desligada. Seleção de viagem explica bloqueio documental recebido do backend.
Sem upload/storage/notificação externa.
