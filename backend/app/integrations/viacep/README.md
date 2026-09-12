# ViaCEP — OC62

`CONFIRMADO`: integração interna do backend referente à Issue #44. Segue o
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
| `street` | `logradouro` | String ou `null`. |
| `neighborhood` | `bairro` | String ou `null`. |
| `complement` | `complemento` | String ou `null`. |
| `city` | `localidade` | String obrigatória, não vazia. |
| `state` | `uf` | Sigla obrigatória de UF brasileira em maiúsculas. |

`CONFIRMADO`: textos são aparados; campos opcionais ausentes, nulos ou vazios
viram `None` (`null` em JSON). Um CEP municipal pode não conter rua, bairro ou
complemento. Ausência de CEP, cidade ou UF, tipos incorretos e CEP divergente
geram resposta inválida, sem devolver preenchimento parcial não validado.

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

## Cadastro manual e futura API

`CONFIRMADO`: os serviços de criação/atualização de clientes não chamam o
ViaCEP e continuam aceitando endereço informado manualmente. A consulta é
auxiliar e não autoriza criar campos persistidos nem compor automaticamente
`Customer.address` com uma regra ainda não aprovada.

`RECOMENDAÇÃO`: o futuro consumidor deve tratar `ViaCEPProviderError` como
falha de preenchimento auxiliar, preservar os dados digitados e permitir
cadastro manual. Usar apenas `code`/`message`, sem serializar traceback ou
detalhes externos. O frontend deverá consultar o backend, nunca o ViaCEP.

`PENDENTE DE DEFINIÇÃO`: esta OC62 entrega o contrato interno, não um endpoint
HTTP público. Caminho, RBAC, status HTTP e composição do endereço precisam de
aprovação antes de expor a consulta para a OC70. Os códigos acima ainda não
são um contrato público de erros HTTP.

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

Executar a partir de `backend`:

```bash
python -m pytest tests/unit/test_viacep_provider.py -q
python -m ruff check app/integrations/viacep tests/unit/test_viacep_provider.py
```
