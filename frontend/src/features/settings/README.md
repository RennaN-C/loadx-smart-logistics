# Configurações administrativas — OC85

`CONFIRMADO`: `/settings`, menu Administração → Configurações, somente ADMIN
ativo. RequireAuth conserva carregamento e redirecionamento de sessão ausente;
RequireSettingsAdmin nega acesso direto de LOGISTICS_MANAGER/CHECKER/DRIVER,
ator ausente ou inativo, sem montar a página protegida. 401 e falha de restauração
seguem AuthProvider/LoginPage existentes; 403 de perfil apresenta Acesso negado.
A OC85 preserva autenticação e RBAC gerais; OC91 adiciona seu contrato administrativo e tabela institucional.

`CONFIRMADO`: contexto somente leitura vindo de useAuth (/auth/me existente),
sem outra cópia de identidade, storage ou dados institucionais inventados.
SettingsSection compõe seções identificadas/rotuladas semanticamente; conta e
administração ficam separadas das configurações próprias do módulo LoadX.
Layout, navegação, alertas e tokens visuais existentes são reutilizados.

`PENDENTE DE DEFINIÇÃO`: gestão de usuários OC86 permanece informativa, sem chamadas ou rotas fictícias. Segurança da própria conta (OC92) usa a rota autenticada `/account`, disponível a todos os perfis; Configurações continua ADMIN. Configurações logísticas permanecem no módulo e futuras funções de conta podem ser delegadas sem alterar páginas operacionais.
CoreFlow, SSO, tenant e licenciamento não são implementados nem dependências.

`CONFIRMADO`: não persiste preferências críticas no navegador. Nenhum cadastro
institucional é chave de isolamento. Página responsiva, títulos hierárquicos,
regiões nomeadas, navegação por fragmento da URL e foco visível, sem interação por ícone só.

## Dados da empresa — OC91

`CONFIRMADO`: Administração → Configurações → Dados da empresa, na mesma
rota `/settings` e guarda ADMIN. Consulta `GET /api/v1/company-profile`;
resposta inicial nula não cria cadastro. Edição explícita e substituição via
`PUT /api/v1/company-profile`, com salvar/cancelar, confirmação, loading,
repetição de consulta em falha e erros por campo associados ao controle.
Depois de F5 os dados são consultados novamente na API.

Nome empresarial e de exibição são obrigatórios. CNPJ numérico com dígitos
verificadores, telefone com DDD, e-mail e referência HTTPS são opcionais;
vazio limpa o campo. A referência não é carregada como imagem, não recebe
arquivos e não aceita credenciais na URL. Histórico mostra ator, data e
nomes dos campos alterados, sem valores. Outros perfis não consultam nem
editam o cadastro ou seus eventos. Não há tenant nem autenticação adicional.

Decisão e limites: [ADR-035](../../../../docs/decisions/ADR-035-configuracoes-institucionais-standalone.md).

## Integrações e Saúde — OC108

`CONFIRMADO`: seção da mesma rota/guarda ADMIN, âncora `#settings-integrations`.
Consulta real à API administrativa, atualização manual somente leitura com
limite de 8 s; sem polling, envio de mensagem, prompts ou botões de teste falso.
Seis cards distinguem simulados/pendentes/falha/timeout e configuração desconhecida.
loading, erro/repetição, vazio, falha parcial e última consulta marcada como
possivelmente desatualizada. 401/403 limpa snapshot anteriormente carregado.

`CONFIRMADO`: interface mostra data e UUID para correlação, sem logs brutos ou
mensagens privadas da API. Layout responsivo, texto de estado além de cor,
regiões/labels existentes e loading em output sem alteração das guardas OC85/OC91.
Sem storage local. Não implementa OC83, OC84, OC103 ou provider externo de IA.


`CONFIRMADO` (OC92): Conta e administração agora oferece link funcional para `/account` (Meu perfil, senha e sessões). Gestão de usuários permanece em preparação na OC86. A conta pessoal está disponível para todos os perfis via Minha conta, sem liberar Configurações aos demais. Dados da empresa e Integrações e Saúde preservados.

## Experiência de Configurações — manutenção #200

`CONFIRMADO`: a página usa quatro abas horizontais: Conta, Empresa,
Integrações e Operação. A sidebar principal é a única navegação lateral.
No celular, as abas priorizam os nomes, com indicador ativo e foco visível.
São links nativos em navegação nomeada com `aria-current`, acessíveis por Tab/Enter;
não simulam o padrão ARIA de tabs sem seu comportamento de teclado. Somente uma seção fica visível e disponível à
tecnologia assistiva por vez. Os fragmentos existentes (`#settings-account`,
`#settings-company`, `#settings-integrations`, `#settings-logistics`) abrem a
seção correspondente após F5 ou acesso direto. Anterior/próxima do navegador
restaura a seção; fragmento desconhecido abre Conta e administração.

`CONFIRMADO`: os painéis permanecem montados ao alternar seções para preservar
rascunhos e consultas em andamento. Isso não persiste dados no navegador:
sair da página ou F5 descarta alterações não salvas e reconsulta a API. Cancelar
restaura os valores consultados, enquanto salvar continua usando o contrato
institucional existente. A edição foca o primeiro campo; erro de validação
preserva o rascunho e foca o campo inválido.

`CONFIRMADO`: o formulário institucional agrupa identificação, contato e marca
em uma única superfície de formulário, com divisórias entre grupos e orientação
lateral no desktop. Labels associados, campos de 48 px, indicação de
obrigatoriedade e grid responsivo preservam leitura e alinhamento.
Consulta e edição possuem apresentação distinta. Histórico fica recolhido em
`details` nativo, disponível por teclado. Nenhum campo, formato, regra de
validação, payload ou endpoint mudou.

`CONFIRMADO`: os indicadores de saúde mostram nome, status e propósito de cada
serviço em cards compactos. Motivo, modo, configuração, escopo/limites e referência
de correlação podem ser expandidos, sem
inventar histórico ou métricas. Atualização continua somente leitura; falha,
timeout, configuração desconhecida e último resultado desatualizado mantêm as
regras da OC108. WhatsApp continua identificado como simulado.

`CONFIRMADO`: a conta apresenta identidade real da sessão e ação de segurança em uma
única superfície com separadores, sem cards aninhados, e link para `/account`.
Gestão de usuários continua preparação discreta da OC86. Configurações do LoadX
não cria controles para parâmetros inexistentes: oferece contexto e dois atalhos independentes para
as rotas existentes `/fleet` e `/planning`. ADMIN continua sendo o único perfil
com acesso a Configurações, incluindo os serviços administrativos no backend.

### Validação de interface

1. Entrar como ADMIN e abrir Configurações; alternar as quatro seções.
2. Abrir `/settings#settings-company` diretamente e recarregar a página.
3. Editar dados, alternar para Integrações e voltar; verificar o rascunho.
4. Cancelar; editar/salvar e verificar persistência após F5.
5. Testar campo inválido, falha/retentativa da API e carregamento sem inventar dados.
6. Expandir histórico e limites de integração; usar Tab, Enter e foco visível.
7. Validar acesso negado a LOGISTICS_MANAGER, CHECKER e DRIVER.
8. Inspecionar 375, 768, 1280×720 e 1920×1080 px nos temas escuro e claro.

`CONFIRMADO`: manutenção exclusivamente de frontend, sem migration, dependência
nova, alteração de RBAC ou contrato HTTP. Backend permanece fonte de verdade.
