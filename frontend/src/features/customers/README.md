# Feature: customers

Cadastro de clientes (OC28). Consome `GET/POST/PATCH /customers`.

## O que existe hoje

- `pages/ContactsPage.tsx` (+ `.css`): a tela `/contacts` inteira, com as abas **Clientes** e
  **Motoristas**. A OC28 pede uma tela só para os dois cadastros, então esta página compõe o painel
  desta feature com o de `drivers`.
- `components/CustomerPanel.tsx`: busca, grade e modal de clientes.
- `components/CustomerForm.tsx`: criação e edição.
- `components/customersErrorMessages.ts`: tradução dos códigos de erro.
- `api/customersApi.ts`: mapeamento snake_case ↔ camelCase.

A listagem usa `hooks/useResourceList` (compartilhado), não um hook próprio.

## Import cruzado com `drivers`

`ContactsPage` importa `DriverPanel` de `features/drivers`. É **composição de tela**, não regra
compartilhada: cada feature continua dona do seu próprio painel, formulário, API e mensagens de erro.
A dependência é de mão única — `drivers` não conhece `customers`.

O CSS do card (`.contact-card`) vive em `pages/ContactsPage.css` e serve às duas abas, porque
cliente e motorista exibem a mesma coisa: uma pessoa ou empresa com contato.

## Permissões

**Só `ADMIN` e `LOGISTICS_MANAGER` leem clientes — `CHECKER` é bloqueado**, ao contrário de
caminhões e produtos. O backend chama isso de `PERSONAL_DATA_READERS`
(`tests/integration/test_authorization_matrix.py`). Por isso o link "Clientes e motoristas" não
aparece na navegação para o conferente: ofereceria um caminho que responderia 403.

Criar e editar continua exclusivo do `LOGISTICS_MANAGER`.

## Fora de escopo

Paginação e busca server-side (não suportadas pelo backend) e exclusão (não existe rota).
