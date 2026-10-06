# ViaCEP — OC62

`CONFIRMADO`: integração do backend referente à Issue #44, exposta em
`GET /api/v1/customers/cep/{cep}` somente para `LOGISTICS_MANAGER`. Segue o
padrão de Protocol, modelos estritos, erros normalizados e fake da integração
de IA. Não altera Customer, banco, migrations, frontend ou cadastro manual.

## Contrato interno para a OC70

`CONFIRMADO`: a aplicação depende de `ViaCEPProvider`, não do cliente HTTP:

```python
from app.integrations.viacep import ViaCEPAddress, ViaCEPProvider

# ViaCEPProvider.lookup_address(cep: str, *, timeout_seconds: float) -> ViaCEPAddress
```

`CONFIRMADO`: CEP aceita oito dígitos ASCII, com ou sem hífen (`01234567` ou
`01234-567`), ignorando espaços nas extremidades. Preserva zeros iniciais e
retorna oito dígitos sem hífen. Letras, espaços internos, outras pontuações,
dígitos Unicode e tipos diferentes de string são rejeitados antes de qualquer
chamada HTTP. O timeout deve ser um número positivo e finito; configuração
inválida gera `ValueError` antes da consulta.

`CONFIRMADO`: `ViaCEPAddress` é Pydantic estrito/congelado, rejeita campos extras
e revalida inclusive instâncias previamente construídas. A saída contém apenas:

| Campo interno | Campo ViaCEP | Contrato |
| --- | --- | --- |
| `cep` | `cep` | Obrigatório; oito dígitos, igual ao CEP solicitado. |
| `street` | `logradouro` | String de até 255 caracteres ou `null`. |
| `neighborhood` | `bairro` | String de até 255 caracteres ou `null`. |
| `complement` | `complemento` | String de até 255 caracteres ou `null`. |
| `city` | `localidade` | String obrigatória, de 1 a 120 caracteres. |
| `state` | `uf` | Sigla obrigatória de UF brasileira em maiúsculas. |

`CONFIRMADO`: textos são aparados; campos opcionais ausentes, nulos ou vazios
viram `None` (`null` em JSON). Um CEP municipal pode não conter rua, bairro ou
complemento. Ausência de CEP, cidade ou UF, tipos incorretos e CEP divergente
geram resposta inválida, sem devolver preenchimento parcial não validado.
Os limites seguem `Customer.address` (255) e `Customer.city` (120). Textos
acima dos limites são rejeitados, não truncados. Os limites individuais não
substituem a validação de `Customer.address` ao salvar um endereço composto.

## Adapter externo e erros

`CONFIRMADO`: `HTTPViaCEPProvider` utiliza a dependência `httpx2` já existente.
Faz uma consulta síncrona a `https://viacep.com.br/ws/{cep}/json/`, sem corpo ou
query string. Somente o CEP normalizado é enviado; a interface não recebe nome,
CPF/CNPJ, telefone nem objetos de cliente. O cliente é isolado, não utiliza
credenciais/proxy do ambiente (`trust_env=False`), não segue redirecionamentos
e é fechado após cada consulta. Não há retries automáticos nem persistência.

`CONFIRMADO`: `timeout_seconds` é aplicado explicitamente às fases de conexão,
leitura, escrita e espera pelo pool; não representa um prazo total de relógio.
Esse comportamento segue a [documentação oficial de timeouts do HTTPX2](https://pydantic.dev/docs/httpx2/advanced/timeouts/).

`CONFIRMADO`: a resposta externa é não confiável. Somente HTTP `200` e objeto
JSON passam à validação. O adapter projeta os seis campos úteis e descarta
metadados externos. `erro: true` ou `erro: "true"` significa CEP inexistente;
outros valores desse marcador são inválidos. O formato do serviço é descrito
na [documentação oficial do ViaCEP](https://viacep.com.br/).

`CONFIRMADO`: todas as falhas abaixo herdam de `ViaCEPProviderError` e possuem
`code` e mensagem estáticos, sem URL, payload, exceção HTTP ou causa externa:

| Exceção | Código interno | Condição |
| --- | --- | --- |
| `ViaCEPInvalidCEPError` | `VIACEP_INVALID_CEP` | Formato de entrada inválido. |
| `ViaCEPNotFoundError` | `VIACEP_NOT_FOUND` | Marcador de CEP inexistente. |
| `ViaCEPTimeoutError` | `VIACEP_TIMEOUT` | Timeout de comunicação. |
| `ViaCEPUnavailableError` | `VIACEP_UNAVAILABLE` | Falha de transporte ou HTTP diferente de `200`, inclusive `404`. |
| `ViaCEPInvalidResponseError` | `VIACEP_INVALID_RESPONSE` | JSON, codificação ou endereço inválido/incompleto. |

## API pública para a OC70 e cadastro manual

`CONFIRMADO`: `GET /api/v1/customers/cep/{cep}` exige sessão válida e perfil
`LOGISTICS_MANAGER`. Sem autenticação retorna `401 AUTH_INVALID_TOKEN`;
`ADMIN`, `CHECKER` e `DRIVER` recebem `403 AUTH_FORBIDDEN` antes de consultar o
provider. A rota injeta `ViaCEPProvider` por `get_viacep_provider`, aplica
normalização antes da chamada e utiliza timeout de 5 segundos por fase HTTP.

`CONFIRMADO`: resposta `200` usa o próprio `ViaCEPAddress`, sem envelope.
Exemplo fictício para `GET /api/v1/customers/cep/01234-567`:

```json
{
  "cep": "01234567",
  "street": "Rua Fictícia",
  "neighborhood": "Bairro Fictício",
  "complement": null,
  "city": "Cidade Fictícia",
  "state": "SP"
}
```

`CONFIRMADO`: os erros usam o envelope existente `code`, `message`, `details`:

| Exceção | Status HTTP | Código público |
| --- | --- | --- |
| `ViaCEPInvalidCEPError` | `422` | `VIACEP_INVALID_CEP` |
| `ViaCEPNotFoundError` | `404` | `VIACEP_NOT_FOUND` |
| `ViaCEPUnavailableError` | `503` | `VIACEP_UNAVAILABLE` |
| `ViaCEPTimeoutError` | `504` | `VIACEP_TIMEOUT` |
| `ViaCEPInvalidResponseError` | `502` | `VIACEP_INVALID_RESPONSE` |

`CONFIRMADO`: CEP inválido usa `details: [{"field": "cep"}]`. Nas falhas de
consulta, `details` é vazio; mensagens são as normalizadas do provider, sem
detalhes do serviço externo. O OpenAPI referencia `ViaCEPAddress` no sucesso
e `ErrorResponse` nos erros.

`CONFIRMADO`: os serviços de criação/atualização de clientes não chamam o
ViaCEP e continuam aceitando endereço informado manualmente. A consulta é
auxiliar e não autoriza criar campos persistidos nem compor automaticamente
`Customer.address` com uma regra ainda não aprovada.

`RECOMENDAÇÃO`: o consumidor da OC70 deve tratar erros de consulta como falha
de preenchimento auxiliar, preservar os dados digitados e permitir cadastro
manual. Usar apenas `code`/`message`, sem detalhes externos. O frontend deverá
consultar este endpoint do backend, nunca o ViaCEP diretamente.

## Fake e testes sem rede

`CONFIRMADO`: `FakeViaCEPProvider` retorna dados fictícios por padrão, aceita
`response` no formato **interno** ou `error` normalizado e registra `calls`
contendo somente CEP normalizado e timeout. Aplica as mesmas validações do
adapter real. Não realiza HTTP.

`CONFIRMADO`: `tests/unit/test_viacep_provider.py` cobre normalização, fake,
entrada inválida sem chamada, CEP inexistente, timeout, indisponibilidade,
resposta inválida/incompleta, privacidade e revalidação. Os testes do adapter
usam `httpx2.MockTransport`; uma fixture automática bloqueia o transporte HTTP
real. Não exigem credenciais, banco ou disponibilidade do ViaCEP.

`CONFIRMADO`: os testes do endpoint em `tests/unit/test_customer_cep_api.py`
injetam `FakeViaCEPProvider` por override de `get_viacep_provider`, verificam
o RBAC real da rota, os erros e os limites de texto com acesso HTTP externo
bloqueado. O cadastro manual mantém seus testes e comportamento existentes.

Executar a partir de `backend`:

```bash
python -m pytest tests/unit/test_viacep_provider.py tests/unit/test_customer_cep_api.py -q
python -m ruff check app/integrations/viacep app/modules/customers/router.py tests/unit/test_viacep_provider.py tests/unit/test_customer_cep_api.py
```
