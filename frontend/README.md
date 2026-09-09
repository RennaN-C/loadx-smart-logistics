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
