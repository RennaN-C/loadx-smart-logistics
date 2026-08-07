# Core

Configurações globais, segurança, logging e exceções compartilhadas.

Não coloque regras de caminhão, pedido ou carga aqui. O core deve conhecer infraestrutura, não detalhes de negócio.

## Arquivos

- `config.py`: variáveis de ambiente e configurações globais, incluindo `APP_ENV=local|production`.
- `exceptions.py`: handlers globais de validação e erros inesperados da API.
- `responses.py`: envelope de erro HTTP e metadados compartilhados do OpenAPI.
- `security.py`: hash de senha e JWT usados pela autenticação.
- `json_decimal.py`: contrato compartilhado que valida e serializa `Decimal`
  como número JSON conforme D06 e ADR-016, sem alterar a aritmética de domínio.
- `pagination.py`: parâmetros, resultado de repository e envelope compartilhado
  da paginação definida por D12 e ADR-017.

`CONFIRMADO`: Swagger, ReDoc e OpenAPI são expostos somente em `local`. Em `production`, `/docs`, `/docs/oauth2-redirect`, `/redoc` e `/openapi.json` não são registrados pela aplicação.

`CONFIRMADO`: na ausência de `APP_ENV`, o backend assume `production` e mantém a documentação desabilitada.
