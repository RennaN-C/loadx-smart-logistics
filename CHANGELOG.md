# Changelog

## [1.0.0] - 2026-09

`CONFIRMADO`: primeira versão funcional integrada do MVP LoadX, em preparação
para revisão e publicação. Esta seção descreve as entregas presentes no código;
a preparação não cria tag nem GitHub Release.

### Acesso e cadastros

- `CONFIRMADO`: autenticação por sessão opaca revogável em cookie, autorização
  por perfis e por vínculo operacional, bootstrap administrativo e gestão de
  usuários, clientes, motoristas, caminhões e produtos.
- `CONFIRMADO`: pedidos com itens, quantidades, prioridade e sequência de entrega,
  transições validadas e histórico de status atômico de pedidos, planos, viagens
  e entregas.

### Planejamento de carga

- `CONFIRMADO`: planejamento tridimensional determinístico com restrições de
  dimensões e peso, rotações permitidas, colisão AABB, empilhamento, fragilidade
  e suporte integral; métricas de ocupação e motivos de rejeição por volume.
- `CONFIRMADO`: persistência do plano e snapshots, aprovação de planos completos,
  recálculo preservando a origem, visualização 3D e sequência de carregamento.
- `CONFIRMADO`: comparação pela API de 2 a 10 caminhões com a mesma engine, sem
  ranking, escolha automática ou distribuição da carga entre veículos.
- `CONFIRMADO`: explicação de plano persistido pela port `AIProvider`, com
  `FakeAIProvider`, timeout e fallback determinístico. A explicação não altera
  o plano nem envia dados pessoais. Comparação e explicação ainda não possuem
  integração na tela de planejamento.

### Operação logística

- `CONFIRMADO`: checklist e finalização de carregamento, criação e listagem
  paginada de viagens, acompanhamento de entregas e registro de ocorrências.
- `CONFIRMADO`: WhatsApp mock com simulador interno protegido, interpretação
  controlada de comandos e execução por services de domínio. Notificações mock
  ao motorista após início da viagem via HTTP e registro de ocorrência.
- `CONFIRMADO`: relatórios PDF de carregamento e viagem, downloads no frontend
  e indicadores de pedidos. Fotos de ocorrências usam apenas referência mock.

### Infraestrutura e qualidade

- `CONFIRMADO`: PostgreSQL com migrations Alembic, Docker Compose local e de
  testes, referência de produção com Caddy/TLS e segredos montados.
- `CONFIRMADO`: CI com Ruff, Pytest e cobertura, ESLint, Vitest, build com
  orçamento do bundle, auditoria npm e verificação de imagem com Trivy.
- `CONFIRMADO`: testes automatizados de regras, contratos, integração e fluxo
  operacional; hardening com Argon2id, CSRF/Origin, limitação de login, headers
  defensivos, minimização de dados e containers sem privilégios.

### Correções para a release

- `CONFIRMADO`: atualização de entrega no frontend interpreta `DeliveryRead`
  e recarrega a viagem pelo backend, eliminando o erro de tratar a entrega como
  `TripRead`. Testes de contrato e de tela cobrem as transições e falhas.
- `CONFIRMADO`: Vitest e seus pacotes internos atualizados de `4.1.10` para
  `4.1.11`, e `js-yaml` transitivo de `4.3.1` para `4.3.2`, para corrigir os
  advisories `GHSA-82fw-gwwq-j7x9` e `GHSA-2883-xcg3-v3hh`. As atualizações são
  de desenvolvimento/testes/lint; dependências de runtime permanecem iguais.

### Limites e evoluções

`PENDENTE DE DEFINIÇÃO`: WhatsApp real, Grok/xAI, automações por IA externa,
distribuição entre caminhões, ViaCEP e demais evoluções permanecem no
[roadmap pós-v1.0.0](docs/10-roadmap-inicial.md#roadmap-pós-v100).
Recuperação de senha, MFA, validações cadastrais formais, storage real e
observabilidade operacional continuam em [riscos e pendências](docs/11-riscos-pendencias.md).
