# Regras de negócio

## Unidades

- dimensões em centímetros;
- peso em quilogramas;
- porcentagem de 0 a 100;
- horário armazenado em UTC.

## Caminhão

- dimensões internas e peso máximo devem ser maiores que zero;
- placa deve ser única;
- caminhão inativo não pode receber novo plano.

## Produto

- dimensões e peso devem ser maiores que zero;
- quantidade pertence ao item do pedido, não ao cadastro do produto;
- produto com rotação bloqueada mantém sua orientação original;
- produto não empilhável não pode receber outro volume por cima.

## Pedido

- deve possuir cliente e pelo menos um item;
- quantidade de item deve ser maior que zero;
- pedido cancelado não pode entrar em plano novo.

## Plano de carga

- nenhum item pode ultrapassar os limites do baú;
- dois itens não podem ocupar o mesmo espaço;
- peso total colocado não pode superar o peso máximo;
- item sem posição deve ser registrado como não carregado;
- o mesmo volume individual não pode aparecer duas vezes;
- resultado deve registrar a versão do algoritmo;
- somente plano calculado pode ser aprovado;
- plano aprovado não deve ser alterado sem gerar nova versão.

## Coordenadas

- X representa largura;
- Y representa altura;
- Z representa comprimento;
- origem no piso, canto frontal esquerdo;
- todas as posições são relativas à parte interna do baú.

## Carregamento e entrega

- carregamento só começa com plano aprovado;
- viagem só começa com carregamento finalizado;
- toda mudança de status gera histórico;
- ocorrência não apaga o status anterior, apenas adiciona contexto;
- entrega concluída deve registrar horário.

## IA

- pode interpretar texto e explicar resultados;
- não pode aprovar plano;
- não pode ignorar validações determinísticas;
- respostas estruturadas devem ser validadas antes de executar ações.
