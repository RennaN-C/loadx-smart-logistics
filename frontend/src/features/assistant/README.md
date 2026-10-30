# Assistente LoadX

Painel consultivo compartilhado do AppLayout, restrito a ADMIN, LOGISTICS_MANAGER
e CHECKER. O backend é a fonte de autorização. PlanAIExplanation abre contexto;
rotas de plano/distribuição são inferidas somente como referência e revalidadas
no servidor. Nada é calculado ou gravado pelo chat.

Reutiliza Modal, Icon, AlertBanner, cliente HTTP/CSRF e tokens existentes. Portal
no body evita containing block do backdrop-filter do cabeçalho. Conversa rola
separadamente do composer; Escape/restauração de foco seguem Modal. Histórico
em memória (até quatro turnos, oito mensagens enviadas), sem localStorage,
abortado/limpo ao trocar identidade, perfil, permissões ou contexto.

Respostas são texto simples, não HTML/Markdown. Links só apontam a rotas internas
permitidas no contrato; fatos mostram critérios e UTC. Não colocar GROQ_API_KEY
ou configuração de provedor no frontend. Erro, retry, loading, vazio e fallback
são reais; mocks existem somente em Vitest, não na aplicação.

Falhas de capacidade oferecem ação junto ao diagnóstico. Ela abre o painel com o
comprovante opaco do servidor e uma pergunta preparada, sem envio automático ou
repetição do cálculo. O contexto da tentativa substitui o plano da rota. O token
não aparece na conversa, no histórico nem em local/sessionStorage. O backend
valida e transforma esse comprovante em fatos; nenhum detalhe bruto é enviado.

## Intenção e experiência Loxi (#371)

Cabeçalho `Loxi - Assistente`; fontes de documentação e conversa geral são distintas
de dados verificados. Artigos não são duplicados em tabelas de indicadores. Links
continuam em allowlist de rotas existentes, filtrados por permissão no backend.
A rolagem acompanha a identidade da última resposta (inclusive depois do limite do
histórico), alinha seu começo e não desloca o cabeçalho/compositor. Sugestões fixas
não foram reintroduzidas. A fonte opcional da página é tratada pelo roteador do
servidor; navegação e troca de usuário/perfil preservam as regras de isolamento.
