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

`CONFIRMADO`: `ADMIN` e `LOGISTICS_MANAGER` podem consultar. Somente `LOGISTICS_MANAGER` pode criar ou atualizar. `CHECKER` e `DRIVER` não acessam o módulo.

## Regras implementadas

- Documento deve ser único.
- Estado é normalizado para maiúsculas.
- Validação formal de CPF/CNPJ ainda está pendente de definição.
- Dados pessoais reais não devem ser usados em seeds, testes ou exemplos.
- Todas as rotas exigem sessão em cookie e consultam o papel e o estado atual do usuário no banco.
