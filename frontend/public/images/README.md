# Assets ativos do acesso

A página atual utiliza três arquivos estáticos, todos referenciados em `frontend/src/features/auth/components/BrandPanel.tsx`:

- `login-scene-hd.webp`: cena principal de login para telas grandes.
- `login-scene-1024.webp`: versão responsiva para telas menores.
- `login-globe.svg`: ilustração vetorial decorativa.

A marca de autenticação fica em `frontend/public/branding/loadx-login-mark.svg`. Verifique as dimensões no componente antes de trocar qualquer recurso.

Variantes antigas de login que não são consumidas pelo frontend foram removidas da árvore atual. **Histórico preservado** no [commit ea3f5e10420d](https://github.com/RennaN-C/loadx-smart-logistics/tree/ea3f5e10420d7a29ce52e00ed79cb3e7de0954e2/frontend/public/images). Não reintroduzir arquivos de comparação antigos no deploy. Para alterações visuais, anexar screenshots à PR ou armazenar artefatos na CI.
