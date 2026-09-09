# Integração com IA

Usos permitidos no MVP:

- interpretar mensagem do motorista em intenção estruturada;
- gerar explicação textual de um plano já validado.

Não posiciona volumes e não aprova planos. Toda saída deve passar por schema e lista de intenções permitidas.

## Port da explicação

`CONFIRMADO`: `AIProvider` é a interface consumida por
`LoadPlanExplanationService`. A port recebe somente o contexto técnico imutável
de um plano persistido e devolve uma explicação que o service ainda valida. O
provider não acessa banco, repository, router ou optimizer.

O contexto permitido limita-se a:

- métricas calculadas;
- snapshot técnico do caminhão;
- posições e dimensões usadas;
- rotações e sequência de carregamento;
- volumes rejeitados e motivos de rejeição;
- `algorithm_version`.

`CONFIRMADO`: nome, CPF/CNPJ, telefone e endereço de cliente, bem como nome,
documento, telefone ou qualquer outro dado pessoal de motorista, nunca são
enviados ao `AIProvider`.

## Provider fake e disponibilidade

`CONFIRMADO`: o MVP fornece um provider fake determinístico para desenvolvimento
e testes sem rede, SDK ou credenciais. O adapter externo concreto fica sob
responsabilidade do Desenvolvedor 4 e deve implementar a mesma port sem receber
acesso adicional ao domínio.

O timeout é configurável e usa 5 segundos por padrão. O adapter concreto deve
aplicar o valor recebido à chamada externa e normalizar a expiração como
`AIProviderTimeoutError`. O service trata somente as falhas de disponibilidade
aprovadas:

- timeout do provider;
- provider indisponível;
- resposta ausente ou inválida conforme o schema.

Esses três casos produzem explicação determinística com `source = FALLBACK`.
Resposta válida usa `source = AI`. Fallback não encobre autenticação inválida,
acesso proibido, plano inexistente, plano tecnicamente inválido ou erro de domínio
não classificado como falha do provider.

`CONFIRMADO`: nem a resposta do provider nem o fallback podem substituir
`load_plan_id` ou `algorithm_version`, recalcular métricas, mudar posições,
rejeições ou estado, ou aprovar o plano.
