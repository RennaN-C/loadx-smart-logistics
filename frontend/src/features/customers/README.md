# Feature: customers

Cadastro de clientes (OC28). Consome `GET/POST/PATCH /customers`.

## O que existe hoje

- `pages/ContactsPage.tsx` (+ `.css`): a tela `/contacts` inteira, com as abas **Clientes** e
  **Motoristas**. A OC28 pede uma tela só para os dois cadastros, então esta página compõe o painel
  desta feature com o de `drivers`.
- `components/CustomerPanel.tsx`: busca, grade paginada e modal de clientes.
- `components/CustomerForm.tsx`: criação e edição.
- `components/CepLookupField.tsx`: consulta de endereço por CEP (OC70).
- `components/customersErrorMessages.ts`: tradução dos códigos de erro.
- `api/customersApi.ts`: mapeamento snake_case ↔ camelCase.

A listagem usa `hooks/useResourceList` (compartilhado, paginado) e `hooks/useEditTarget` para buscar o
detalhe antes de editar.

## A listagem devolve um resumo

`GET /customers` responde `CustomerListRead`: só `id`, `name`, `city`, `state` e `created_at`. **Documento,
telefone, endereço e observações não saem na listagem** — dado pessoal só no detalhe. Consequências:

- o card mostra apenas nome e cidade/UF;
- a busca client-side cobre nome e cidade, não documento;
- editar exige `GET /customers/{id}` antes de abrir o formulário, senão o PATCH iria sem os campos que
  o usuário não viu. O botão vira "Abrindo…" enquanto isso.

## Documento e telefone (OC71)

O formulário confere CPF, CNPJ e telefone com a MESMA regra da OC63, de
`components/documentRules.ts`, e põe a mensagem embaixo do campo. Antes ele só
contava dígitos: um CPF com verificador errado passava pela tela e voltava como
422, numa faixa que não dizia qual campo consertar.

A validação só começa no primeiro envio e depois dele o campo se corrige a cada
tecla — acusar "CPF inválido" no terceiro dígito atrapalha quem ainda digita.

O 422 do backend pousa no campo que ele mesmo apontou, por `details[].field`.
Quando nenhum campo da tela corresponde, a faixa do topo assume.

Telefone é opcional aqui, diferente do motorista: vazio vira `null`.

## CEP (OC70)

`CONFIRMADO`: a consulta passa pelo BACKEND, em `GET /customers/cep/{cep}`. O
ViaCEP **nunca** é chamado do navegador — quem fala com ele é
`app/integrations/viacep`, que normaliza o CEP, aplica timeout de 5s por fase e
traduz as falhas para códigos estáveis.

A rota exige `LOGISTICS_MANAGER`, que é exatamente o único perfil a abrir este
formulário (`CustomerPanel` já gatilha por `canManage`). Não existe caminho em
que o botão apareça e responda 403.

**O CEP não é salvo.** `Customer` não tem essa coluna e a OC70 não autoriza
criar campo persistido.

O que é preenchido:

| ViaCEP | Campo do cliente |
| --- | --- |
| `city` | Cidade |
| `state` | UF |
| `street` | Endereço (a pessoa completa com número) |
| `neighborhood`, `complement` | Dica abaixo do CEP, **não** preenchimento |

Bairro e complemento não entram no endereço porque `Customer.address` é um texto
só, e compor "rua, bairro" exigiria um formato que ninguém aprovou — a OC62 diz
isso explicitamente. Jogar fora também seria errado: é o que a pessoa lê para
completar o endereço à mão.

O endereço **não é sobrescrito quando a rua já está lá**: quem digitou "Rua X,
120" e só depois preencheu o CEP perderia o número.

Nada disso impede o cadastro. Falha de consulta fica no campo do CEP, preserva o
que já foi digitado, e toda mensagem termina dizendo que dá para preencher à
mão. `404` vindo do ViaCEP vira `VIACEP_UNAVAILABLE`, não "não encontrado" —
quem sinaliza CEP inexistente é o marcador `erro: true` no corpo, com status 200.

`RISCO IDENTIFICADO`: a consulta dispara sozinha ao completar os 8 dígitos.
Trocar o CEP rápido gera duas chamadas, e a ordem de volta não é garantida — por
isso cada consulta carrega uma sequência e a resposta atrasada é descartada.

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

Busca e filtro server-side (D12): a busca atua só na página carregada. Exclusão não existe rota.
