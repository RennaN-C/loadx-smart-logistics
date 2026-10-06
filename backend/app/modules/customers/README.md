# Clientes

Dados mínimos do destinatário usados em pedidos e entregas. Evitar dados reais nos testes.

## Estrutura

- `models.py`: entidade SQLAlchemy `Customer`.
- `schemas.py`: contratos Pydantic `CustomerCreate`, `CustomerUpdate` e `CustomerRead`.
- `repository.py`: consultas e persistência de clientes.
- `service.py`: regras de documento único, criação, consulta e atualização.
- `router.py`: endpoints HTTP.
- `domain/`: objetos e regras puras, quando necessário.

Crie somente os arquivos necessários para a ocorrência atual.

## Endpoints

- `GET /api/v1/customers`: lista paginada com `id`, `name`, `city`, `state` e
  `created_at`; omite documento, telefone, endereço e observações.
- `POST /api/v1/customers`: cria cliente.
- `GET /api/v1/customers/{id}`: consulta cliente por ID.
- `PATCH /api/v1/customers/{id}`: atualiza campos enviados.
- `GET /api/v1/customers/cep/{cep}`: consulta auxiliar de endereço por CEP,
  somente para `LOGISTICS_MANAGER`, com timeout HTTP de 5 segundos por fase.

`CONFIRMADO`: `ADMIN` e `LOGISTICS_MANAGER` podem consultar clientes. Somente
`LOGISTICS_MANAGER` pode criar, atualizar ou consultar CEP. `CHECKER` e
`DRIVER` não acessam o módulo.

`CONFIRMADO`: a OC62 retorna `ViaCEPAddress` em `200` e o envelope padrão nos
erros: CEP inválido `422`, não encontrado `404`, resposta inválida `502`,
indisponibilidade `503` e timeout `504`. A dependência `get_viacep_provider`
permite fake nos testes. Rua, bairro e complemento aceitam até 255 caracteres
cada; cidade, até 120. O cadastro manual não depende desta consulta.
Contrato completo: [ViaCEP — OC62/OC70](../../integrations/viacep/README.md).

## Regras implementadas

- Documento deve ser único.
- Estado é normalizado para maiúsculas.
- `CONFIRMADO` (OC63): create/update aceitam CPF (11 dígitos) ou CNPJ numérico
  (14 dígitos), sem máscara ou com a máscara padrão. Validam os dois dígitos
  verificadores e rejeitam sequências repetidas, letras e máscaras incorretas.
- `CONFIRMADO`: documento e telefone novos/alterados são persistidos sem
  máscara. Telefone é opcional (`null` permitido), aceita 10 ou 11 dígitos com
  DDD não iniciado em zero; celular deve começar com 9 após o DDD.
- `CONFIRMADO`: PATCH mantém campos omitidos; documento `null` e telefone
  vazio são inválidos. Falhas usam o erro Pydantic padrão, HTTP `422`.
- Dados pessoais reais não devem ser usados em seeds, testes ou exemplos.
- Todas as rotas exigem sessão em cookie e consultam o papel e o estado atual do usuário no banco.
