# Feature: drivers

Cadastro de motoristas (OC28). Consome `GET/POST/PATCH /drivers`.

## O que existe hoje

- `components/DriverPanel.tsx`: busca, filtro por status, grade e modal de motoristas.
- `components/DriverForm.tsx`: criação e edição.
- `components/driversErrorMessages.ts`: tradução dos códigos de erro — o backend distingue
  documento duplicado de CNH duplicada, e as mensagens seguem essa distinção.
- `api/driversApi.ts`: mapeamento snake_case ↔ camelCase.

Esta feature **não tem página própria**: o painel é montado na aba "Motoristas" de
`features/customers/pages/ContactsPage.tsx`, conforme a OC28 pede uma tela só para os dois cadastros.
A listagem usa `hooks/useResourceList` (compartilhado).

## Decisões

**Categoria da CNH é um `<select>`, não campo livre.** O backend aceita qualquer string de até 8
caracteres, mas só faz sentido oferecer as categorias que dirigem caminhão (C, D, E, AC, AD, AE) —
A é moto e B é carro de passeio. Continua opcional: "Não informada" envia `null`.

**`active` só aparece na edição**, igual a caminhões: a criação não expõe o campo, mesmo o schema
aceitando, porque o backend já assume `true`.

## Permissões

**Só `ADMIN` e `LOGISTICS_MANAGER` leem motoristas — `CHECKER` é bloqueado**, por serem dados
pessoais. Criar e editar é exclusivo do `LOGISTICS_MANAGER`.

## Fora de escopo

Paginação e busca server-side (não suportadas pelo backend) e exclusão (não existe rota; desativar
é `active: false` via PATCH). O vínculo entre `users` e `drivers` não existe no backend, então o
perfil `DRIVER` ainda não enxerga nada além de `/auth/me`.
