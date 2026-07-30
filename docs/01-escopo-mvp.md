# Escopo do MVP

## Incluído

`CONFIRMADO`: fazem parte do MVP:

- autenticação simples e perfis;
- caminhões e dimensões internas;
- produtos e características físicas;
- clientes e motoristas;
- pedidos e itens;
- criação de plano de carga;
- rotações permitidas;
- validação de limites e colisões;
- validação de peso máximo;
- validação básica de apoio e empilhamento;
- cálculo de ocupação;
- volumes não carregados;
- ordem de carregamento;
- visualização 3D;
- checklist de carregamento;
- status de viagem e entrega;
- ocorrências com texto e foto opcional;
- WhatsApp simulado ou integração controlada;
- relatório PDF simples.

## Fora do MVP

`CONFIRMADO`: não fazem parte do MVP:

- paletes;
- controle de peso por eixo;
- GPS e mapas em tempo real;
- roteirização por trânsito;
- câmera e OpenCV;
- reconhecimento automático de volumes;
- telemetria;
- MDF-e;
- previsão climática;
- aprendizado contínuo;
- treinamento de modelo de IA;
- aplicativo móvel nativo.

## Requisitos funcionais

- `RF-01` `CONFIRMADO`: cadastrar e manter usuários internos com perfil de acesso.
- `RF-02` `CONFIRMADO`: autenticar usuário com senha criptografada e token.
- `RF-03` `CONFIRMADO`: cadastrar caminhões com placa, modelo, dimensões internas em centímetros, peso máximo em quilogramas e status.
- `RF-04` `CONFIRMADO`: cadastrar motoristas com dados mínimos, CNH e status.
- `RF-05` `CONFIRMADO`: cadastrar clientes com documento, telefone, endereço, cidade, estado e observações.
- `RF-06` `CONFIRMADO`: cadastrar produtos com dimensões, peso, fragilidade, empilhamento e rotação permitida.
- `RF-07` `CONFIRMADO`: criar pedidos com cliente, produtos, quantidades, prioridade, data prevista e endereço de entrega.
- `RF-08` `CONFIRMADO`: criar viagens a partir de plano de carga aprovado, caminhão, motorista e pedidos.
- `RF-09` `CONFIRMADO`: calcular capacidade do caminhão, volume dos produtos, peso total e ocupação.
- `RF-10` `CONFIRMADO`: ordenar volumes por critérios determinísticos de volume, peso, fragilidade, empilhamento e sequência de entrega.
- `RF-11` `CONFIRMADO`: testar rotações permitidas e salvar dimensões usadas.
- `RF-12` `CONFIRMADO`: posicionar volumes com coordenadas `x`, `y`, `z` válidas.
- `RF-13` `CONFIRMADO`: rejeitar volumes que excedam limites, peso ou regras físicas.
- `RF-14` `DECISÃO NECESSÁRIA`: comparar aproveitamento entre caminhões; o documento-base inclui `OC21`, mas também cita comparação automática como funcionalidade futura.
- `RF-15` `CONFIRMADO`: explicar plano validado com IA sem permitir que a IA aprove a solução.
- `RF-16` `CONFIRMADO`: exibir dashboard com indicadores do MVP.
- `RF-17` `CONFIRMADO`: exibir planejamento, volumes carregados e volumes rejeitados.
- `RF-18` `CONFIRMADO`: renderizar visualização 3D baseada nas coordenadas da API.
- `RF-19` `CONFIRMADO`: registrar checklist e estados de carregamento.
- `RF-20` `CONFIRMADO`: atualizar status de viagem e entrega.
- `RF-21` `CONFIRMADO`: registrar ocorrências operacionais.
- `RF-22` `CONFIRMADO`: interpretar comandos controlados do motorista via WhatsApp simulado ou provider controlado.
- `RF-23` `CONFIRMADO`: gerar relatório de carregamento e relatório de viagem em PDF simples.

## Requisitos não funcionais

- `RNF-01` `CONFIRMADO`: backend em Python 3.12 com FastAPI.
- `RNF-02` `CONFIRMADO`: banco PostgreSQL 16 com SQLAlchemy 2 e Alembic.
- `RNF-03` `CONFIRMADO`: frontend em React, TypeScript estrito e Vite.
- `RNF-04` `CONFIRMADO`: visualização 3D com Three.js e React Three Fiber.
- `RNF-05` `CONFIRMADO`: ambiente local com Docker Compose.
- `RNF-06` `CONFIRMADO`: testes com Pytest no backend e Vitest/Testing Library no frontend.
- `RNF-07` `CONFIRMADO`: algoritmo determinístico, testável e reproduzível.
- `RNF-08` `CONFIRMADO`: dados pessoais reais não podem ser usados em seeds ou testes.
- `RNF-09` `CONFIRMADO`: segredos devem vir de variáveis de ambiente e não do código.
- `RNF-10` `RECOMENDAÇÃO`: toda alteração de contrato deve ser pequena, revisada e versionada em documentação antes de frontend/backend divergirem.
- `RNF-11` `PENDENTE DE DEFINIÇÃO`: metas objetivas de performance para o otimizador, como número máximo de volumes e tempo-alvo de cálculo.
- `RNF-12` `PENDENTE DE DEFINIÇÃO`: política final de retenção de fotos de ocorrências.

## Critério de sucesso

`CONFIRMADO`: o sistema deve executar o seguinte cenário sem intervenção direta no banco:

1. cadastrar caminhão e produtos;
2. criar cliente, motorista e pedido;
3. gerar plano válido;
4. salvar posições;
5. exibir o plano em 3D;
6. finalizar carregamento;
7. iniciar viagem;
8. atualizar entrega;
9. registrar uma ocorrência;
10. gerar relatório.

## Funcionalidades futuras

`CONFIRMADO`: o documento-base cita como futuras: reconhecimento de volumes por câmera, QR Code, previsão de atrasos, roteirização inteligente, controle de combustível, análise de peso por eixo, aplicativo móvel, realidade aumentada, aprendizado com viagens anteriores e comparação automática entre veículos.

`DECISÃO NECESSÁRIA`: comparar caminhões aparece como ocorrência do documento-base e também como funcionalidade futura. A equipe deve decidir se a comparação básica entre caminhões entra no MVP ou se fica para uma fase posterior.
