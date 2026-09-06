# Roadmap inicial

`CONFIRMADO`: a numeração de referência para ocorrências passa a ser a do documento-base anexado: `OC01` a `OC48`.

`RISCO IDENTIFICADO`: versões anteriores deste documento usavam outra sequência `OC-01` a `OC-30`. Para evitar conflito entre os 4 desenvolvedores, novas issues e PRs devem usar `OCXX` conforme `docs/07-divisao-equipe.md`.

## Sprint 0: fundação técnica

Objetivo: deixar ambiente local, backend, frontend, banco e documentação mínima prontos para desenvolvimento integrado.

- `OC01`: configuração do projeto backend.
- `OC02`: criação e configuração do banco de dados.
- `OC23`: configuração do frontend.
- `OC48`: documentação inicial e guias de trabalho.

Entregável integrado:

- `docker compose up --build` sobe banco, backend e frontend.
- `/health` responde.
- Documentação principal está revisada.

## Sprint 1: cadastros, autenticação e contratos

Objetivo: permitir cadastro e consulta dos dados-base do MVP.

- `OC03`: autenticação e controle de acesso.
- `OC04`: cadastro de caminhões.
- `OC05`: cadastro de motoristas.
- `OC06`: cadastro de clientes.
- `OC07`: cadastro de produtos e volumes.
- `OC08`: cadastro de pedidos.
- `OC24`: tela de login.
- `OC26`: tela de caminhões.
- `OC27`: tela de produtos.
- `OC28`: tela de clientes e motoristas.
- `OC29`: tela de pedidos.

Entregável integrado:

- API de cadastros com testes mínimos.
- Telas consumindo API ou mocks alinhados ao contrato.

## Sprint 2: núcleo do planejamento

Objetivo: implementar o coração determinístico do LoadX.

- `OC11`: cálculo da capacidade do caminhão.
- `OC12`: cálculo do volume dos produtos.
- `OC13`: ordenação dos volumes.
- `OC14`: rotação dos volumes.
- `OC15`: posicionamento dos volumes.
- `OC16`: validação de colisões.
- `OC17`: validação de empilhamento.
- `OC18`: controle de peso.
- `OC19`: cálculo do aproveitamento.
- `OC20`: sequência de carregamento.
- `OC30`: tela de planejamento.

Entregável integrado:

- Endpoint de plano de carga retorna posições, rejeições, peso e ocupação.
- Testes unitários cobrem limites, colisões, rotação, peso e reprodutibilidade.

## Sprint 3: visualização, comparação e explicação

Objetivo: transformar o resultado do planejamento em experiência visual e justificável.

- `OC21`: comparação entre caminhões.
- `OC22`: explicação do planejamento com IA.
- `OC25`: dashboard.
- `OC31`: visualização 3D.
- `OC32`: interação com a visualização 3D.
- `OC33`: animação do carregamento.

Entregável integrado:

- Usuário calcula plano, visualiza carga em 3D e entende volumes posicionados/rejeitados.

`CONFIRMADO`: a `OC21` está concluída no MVP e compara de 2 a 10 caminhões por
execução, sem persistência, ranking, score ou escolha automática. A comparação
automática avançada permanece evolução futura.

`CONFIRMADO`: a `OC22` está concluída com port de IA, provider fake, timeout
configurável de 5 segundos por padrão e fallback determinístico. A IA explica
somente plano persistido e não valida, recalcula ou altera o resultado. O adapter
externo concreto permanece como integração do Desenvolvedor 4.

## Sprint 4: operação, WhatsApp e ocorrências

Objetivo: acompanhar carregamento, viagem, entregas e ocorrências.

- `OC09`: controle de viagens.
- `OC10`: histórico de status.
- `OC34`: tela de acompanhamento.
- `OC36`: configuração da integração com WhatsApp.
- `OC37`: comandos do motorista.
- `OC38`: interpretação de linguagem natural.
- `OC39`: atualização de status pelo WhatsApp.
- `OC40`: notificações automáticas.
- `OC41`: registro de ocorrências.
- `OC42`: envio de fotos.

Entregável integrado:

- Fluxo de carregamento/viagem atualiza status, registra histórico e aceita ocorrências por interface ou provider mock.

## Sprint 5: relatórios, testes finais e apresentação

Objetivo: fechar o MVP demonstrável de ponta a ponta.

- `OC35`: tela de indicadores e relatórios.
- `OC43`: relatório de carregamento.
- `OC44`: relatório de viagem.
- `OC45`: geração de relatório em PDF.
- `OC46`: testes da API.
- `OC47`: testes do fluxo completo.
- `OC48`: documentação final.

Entregável integrado:

- Fluxo completo testado: pedido, plano, 3D, carregamento, viagem, ocorrência e relatório.

## Critérios para avançar de sprint

- Contratos impactados atualizados em `docs/05`.
- Modelo de dados impactado atualizado em `docs/03`.
- Testes mínimos passando.
- PR revisado por outro desenvolvedor.
- Pendências registradas em `docs/11-riscos-pendencias.md` quando não forem resolvidas na sprint.
