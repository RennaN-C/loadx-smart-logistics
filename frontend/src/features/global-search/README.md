# OC107 — Busca no cabeçalho

`CONFIRMADO`: `GlobalSearch` é integrado ao AppLayout, sem alterar a sidebar,
autenticação, contratos de domínio ou estilos globais da preferência #212.
Usa tokens existentes e acompanha o tema do sistema nesta base; não incorpora
código das PRs #211/OC98 ou #214, ambas ainda abertas na preparação.

`CONFIRMADO`: combobox com categorias/listbox, debounce de 300 ms, termo de
2–120 caracteres, AbortController e descarte de respostas antigas. Estados
inicial/carregando/vazio/falha/retry distintos. Setas percorrem resultados na ordem
visual e mantêm opção visível; Enter seleciona, Escape fecha sem tirar foco.
Blur e navegação fecham o painel. Retry devolve foco à entrada.

`CONFIRMADO`: API é fonte do RBAC. Defesa adicional de apresentação limita
categorias por perfil e aceita somente prefixos internos dos recursos existentes.
Nenhum título pessoal é fabricado ou buscado no cliente. Preferência e formulários
da OC98 não são tocados. `useUrlSearch` sincroniza filtros existentes de clientes,
motoristas e caminhões com URLs de destino, incluindo F5 e navegação de histórico.
Não se trata de uma nova central operacional nem persistência de registros locais.
