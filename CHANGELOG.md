# Changelog

## OC91 — Configurações gerais da empresa

- Cadastro institucional persistente monoempresa integrado às Configurações,
  com consulta e edição exclusivas do ADMIN e validações existentes.
- Referência HTTPS de logotipo sem upload, binários ou carregamento remoto.
- Auditoria transacional sem valores e protegida contra consulta de outros perfis.
- Migration `20261009_0023`, encadeada em `20261009_0022`; downgrade bloqueia
  remoção de cadastro/histórico existentes. ADR-035 documenta limites standalone.

## [Unreleased] — v1.2.0

`CONFIRMADO`: a v1.2.0 — Administração, comunicação real e operação
multi-caminhão é o ciclo atual.

### Entregas integradas em `desenvolvimento` (não publicadas em `main`)

- **OC105 / PR #170 e correções de permissões:** arquivamento e reativação controlados de cadastros.
- **OC99 / PR #175:** múltiplos endereços por cliente e snapshot imutável do destino do pedido.
- **OC100 / PR #176:** manutenção programada, histórico, quilometragem e bloqueio de frota.
- **OC101 / PR #177:** documentos dos caminhões, renovação, alertas e política de elegibilidade.
- **OC102 / PR #178:** CNH e documentos dos motoristas, histórico, validade, categoria e elegibilidade.
- **OC110 / PR #179:** anexos operacionais com autorização, histórico, storage local privado e remoção lógica.
- **OC104 / PR #180:** importação CSV atômica de clientes, produtos, caminhões e motoristas, com prévia e auditoria.

`CONFIRMADO`: o merge da OC104 (`e3af09d`) em 09/10/2026 passou na CI pós-merge:
2.033 testes backend e 570 frontend, Alembic até `20261009_0022`, Segurança e build.
Isso valida o estado de desenvolvimento, não a publicação da versão.

`PENDENTE`: anexos binários exigem definição de fornecedor, retenção e backup antes
de storage de produção; por padrão, o adapter atual opera somente em ambiente
local. O SonarCloud em Automatic Analysis não importa a cobertura Pytest do código
novo: a cobertura executada na CI não deve ser confundida com os 0% da interface.
Uma futura mudança para análise por CI requer configuração de projeto e credenciais.

### Planejamento aprovado

- comunicação externa segura e idempotente;
- evidências e comprovante de entrega;
- WhatsApp Business, webhook, mídia e notificações reais;
- área de Configurações;
- gestão de usuários pelo ADMIN;
- modelo, algoritmo, interface e fluxo operacional multi-caminhão;
- configurações gerais da empresa atual e Meu perfil;
- central de carregamentos, viagens e entregas;
- exceções operacionais, reentrega e cancelamento;
- busca e filtros avançados no servidor;
- relatórios gerenciais e exportações;
- histórico e auditoria consultáveis;
- recuperação de senha e MFA;
- múltiplos endereços por cliente;
- manutenção e documentos de frota e motoristas;
- central de notificações interna;
- importação em massa e arquivamento de cadastros;
- agenda operacional e busca global;
- painel de integrações, fila de eventos e reprocessamento;
- anexos operacionais e linha do tempo unificada;
- perfis e permissões administrativas flexíveis.

O escopo oficial está em
[docs/planejamento/v1.2.0/00-visao-geral.md](docs/planejamento/v1.2.0/00-visao-geral.md).

## [1.1.0] - 2026-10-06

`CONFIRMADO`: a v1.1.0 — Maturidade operacional foi publicada oficialmente em
2026-10-06.

### Entregas incorporadas

- integração backend com ViaCEP;
- validação formal de CPF, CNPJ, CNH e telefone;
- prevenção de conflito operacional de caminhões;
- prevenção de conflito operacional de motoristas;
- RBAC granular para carregamento e conferência;
- roadmap canônico de versões e política SemVer.

O escopo completo da versão está em
[docs/planejamento/v1.1.0/00-visao-geral.md](docs/planejamento/v1.1.0/00-visao-geral.md).

## [1.0.0] - 2026-09-09

`CONFIRMADO`: primeira versão funcional integrada do MVP LoadX, publicada
oficialmente em 2026-09-09 com a tag e GitHub Release `v1.0.0`.

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
- Adicionado deploy automático do bot do Discord no WispByte após atualizações em `desenvolvimento`.

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
distribuição entre caminhões e demais evoluções futuras permanecem no
[roadmap canônico de versões](docs/planejamento/roadmap-versoes.md).
Recuperação de senha, MFA, storage real e observabilidade operacional continuam
em [riscos e pendências](docs/11-riscos-pendencias.md).
