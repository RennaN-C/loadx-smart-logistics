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
