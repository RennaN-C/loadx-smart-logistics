# Frontend

Interface React + TypeScript do LoadX.

`CONFIRMADO`: desenvolvimento e build usam Node `>=22.22 <23`; `.nvmrc` e os
Dockerfiles fixam `22.23.1` para manter o ambiente reproduzível.

## Organização

- `src/app`: inicialização, rotas e providers.
- `src/components`: componentes realmente compartilhados.
- `src/features`: funcionalidades organizadas por domínio.
- `src/services`: cliente HTTP e adaptadores do navegador.
- `src/types`: tipos globais mínimos.
- `src/tests`: configuração e testes de integração visual.

O frontend exibe o plano calculado. Ele não decide validade física nem recalcula posições.

## API no desenvolvimento

`CONFIRMADO`: o cliente usa `VITE_API_URL=/api/v1`, e o servidor de
desenvolvimento do Vite encaminha `/api` sem reescrever o caminho. O target vem
de `DEV_API_PROXY_TARGET` e usa `http://localhost:8000` quando a variável não
está definida. No Compose, somente o frontend substitui esse target por
`http://backend:8000` para acessar o backend pela rede interna.

O desenvolvimento local normal não precisa definir `DEV_API_PROXY_ORIGIN`; sem
ela, o proxy não força o header `Origin`. Em um ambiente atrás de túnel ou
reverse proxy, como o GitHub Codespaces, essa variável pode receber
explicitamente a origem pública do frontend. O mesmo valor deve continuar na
lista exata de `BACKEND_CORS_ORIGINS`; não há wildcard nem confiança automática
em headers recebidos pelo Vite.

## Headers do navegador

`CONFIRMADO`: os servidores `vite` e `vite preview` emitem CSP com origens de
conexão limitadas ao próprio frontend e à origem de `VITE_API_URL`, bloqueiam
framing, MIME sniffing, câmera, geolocalização e microfone e não enviam referrer.

`RISCO IDENTIFICADO`: o build em `dist/` é estático. O servidor web ou CDN de
produção deve reproduzir esses headers e servir o frontend exclusivamente por
HTTPS; a configuração do Vite não acompanha os arquivos após a publicação.

`CONFIRMADO`: `Dockerfile.production` usa Node somente no estágio de build e
serve `dist/` com Caddy. O `Caddyfile` reproduz os headers, aplica cache imutável
apenas aos assets versionados e mantém o HTML sem cache. Essa imagem é usada
somente por `compose.production.yaml`.

## OC99 — múltiplos endereços por cliente

`CONFIRMADO`: o botão Endereços no cadastro abre lista paginada, filtro de
ativos/arquivados, formulário com ViaCEP e ações de edição, principal,
arquivamento e reativação. ADMIN e LOGISTICS_MANAGER usam a gestão atual.
Pedidos carregam os endereços ativos do cliente e permitem seleção explícita;
texto manual continua compatível. Edição preserva snapshot se o destino não
foi alterado, mesmo que a origem tenha mudado. Trocar cliente limpa o destino.
Consulta e ações possuem estados de carregamento, erro e vazio.

## OC100 — manutenção da frota

`CONFIRMADO`: Manutenções no card do caminhão abre histórico paginado e próxima
revisão por data/km, com alerta de vencimento e quilometragem atual. Gestores e
administradores registram preventiva/corretiva com período, descrição,
oficina/observação/custo opcional, encerram/cancelam período e atualizam odômetro.
Conferente consulta sem ações de gestão. Estados de carregamento, erro e vazio
são apresentados. Frota explica manutenção; planejamento omite veículos com
bloqueio atual recebido do backend. Não duplica cálculo de disponibilidade.

## OC101 — documentos dos caminhões

`CONFIRMADO`: Documentos no card abre histórico, tipos, validade, renovação
e política explícita de elegibilidade. ADMIN/LOGISTICS_MANAGER gerenciam ativos;
CHECKER e cadastro arquivado consultam. UI destaca vencido, próximo (30 dias),
emissão futura e substituído usando status do backend. Frota explica política
pendente; planejamento oculta veículos documentalmente inelegíveis. Há estados
de loading/erro/vazio e paginação. Referência UUID de arquivo é metadado, sem
upload/download; envio de notificações permanece na OC103.

## OC85 — configurações administrativas

`CONFIRMADO`: Administração → Configurações (`/settings`) somente ADMIN ativo.
Contexto da conta vem da sessão existente, somente leitura. Seções distinguem
conta/administração de configurações do LoadX. Gestão de usuários, dados da
empresa e segurança da conta aparecem em preparação, sem ações nem rotas falsas.
Sessão ausente/expirada segue login; perfil negado recebe alerta e volta ao início;
carregamento usa SessionLoading. Não cria API, preferências locais, tenant ou
integração CoreFlow. [Estrutura extensível](src/features/settings/README.md).
