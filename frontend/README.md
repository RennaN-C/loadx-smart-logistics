# Frontend

Interface React + TypeScript do LoadX.

## Organização

- `src/app`: inicialização, rotas e providers.
- `src/components`: componentes realmente compartilhados.
- `src/features`: funcionalidades organizadas por domínio.
- `src/services`: cliente HTTP e adaptadores do navegador.
- `src/types`: tipos globais mínimos.
- `src/tests`: configuração e testes de integração visual.

O frontend exibe o plano calculado. Ele não decide validade física nem recalcula posições.

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
