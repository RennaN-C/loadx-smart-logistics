# ADR-048 — Assistente LoadX contextual e consultas read-only

Estado: proposta para revisão na Issue #336. Decisões implementadas nesta PR,
sem autorização de implantação ou envio de dados reais nesta execução.

## Contrato e fronteiras

POST /api/v1/assistant/messages usa sessão, Origin/CSRF e perfis ADMIN,
LOGISTICS_MANAGER e CHECKER. CUSTOM/DRIVER não recebem acesso implícito.
O histórico (até oito mensagens) é transitório no navegador; não há persistência
nem memória entre usuários. Contexto por UUID é reconsultado no servidor:
planning.read, e CHECKER apenas planos/distribuições aprovados, como as APIs atuais.
Nenhum dado físico ou estado do navegador vira verdade do servidor.

Groq usa endpoint HTTPS fixo, sem redirects, SDK, SQL ou chamadas arbitrárias.
Segredo SecretStr, modelo configurável, respostas limitadas a 64 KiB/8.000
caracteres, 700 tokens; até duas chamadas e três ferramentas por pergunta,
com orçamento temporal compartilhado. Mock/ausência/falha retorna FALLBACK
explicitamente identificado; a API legada deixa de chamar fake em runtime.
Fakes de teste permanecem disponíveis para testes sem rede.

## Ferramentas e dados

Registro fechado com schemas Pydantic, sem dispatcher de métodos arbitrários.
Consultas usam projeções agregadas parametrizadas do módulo reports;
serviço aplica permissões efetivas antes das queries. Empresa institucional
somente ADMIN. Métricas globais exigem reports.read e permissões dos recursos
envolvidos; CHECKER fica com orientação/contexto aprovado e consulta paginada de disponibilidade
operacional já autorizada por trucks.read, não métricas globais de negócio.
Nenhum comando de escrita, confirmação ou nova permissão financeira é criado.
Impacto financeiro só informa insufficient_data, sem consultar valores financeiros.
A fase futura de escrita requer Issue, permissões próprias, prévia, confirmação,
revalidação, idempotência e auditoria durável; não é executável por este registro.

Período padrão: últimos 30 dias em UTC; máximo 93 dias, início inclusivo e fim
exclusivo. Pedidos por status usam criação e situação atual. Expedição conta
pedido distinto com viagem iniciada, não criação do plano. Entrega completa exige
Order DELIVERED e última perna entregue; pernas parciais são indicador separado.
Frota usa viagens efetivamente iniciadas e snapshots dos respectivos planos:
ocupação média aritmética por plano, volumes/pesos planejados, veículos distintos.
Canceladas usa estado atual e data de criação, nunca presume data de cancelamento.
Sem baseline/receita/custos comparáveis não existe ROI, lucro ou melhoria percentual.
Nomes ambíguos exigem escolha explícita entre cadastros autorizados. Apenas nome,
cidade/UF e final mascarado do documento são exibidos. A referência escolhida é
revalidada no servidor; opções, UUIDs e rótulo do filtro ficam fora do payload Groq.
Não há escolha automática nem permissão concedida pela seleção no navegador.

## Segurança e limites

Mensagens e histórico são dados não confiáveis; ferramentas e permissões não
podem ser concedidas por prompt. Redação determinística de UUIDs, contatos,
e-mails, URLs e padrões de segredos minimiza a mensagem ao provider. Usuário é
orientado a não informar dados pessoais/segredos; filtragem por padrões não é
classificador universal de PII e não substitui essa política. Contexto técnico
não leva nomes, contatos ou IDs. Resultados de empresa/cliente são minimizados
antes de retornar ao provider; números e critérios reais ficam visíveis na UI.
Saída do modelo é texto simples, sem HTML/Markdown executável ou links livres;
links de recurso vêm exclusivamente do servidor autorizado.

Limite por usuário/processo configurável (6/min padrão), buckets limitados a
4.096 entradas. Advisory lock transacional PostgreSQL impede chamadas simultâneas
do mesmo usuário entre workers. O teto por minuto multiplica com workers; um teto
global durável exige contrato próprio/infraestrutura aprovada, não reutiliza a
tabela de throttle de login. A quota Groq e seus 429 continuam barreiras externas.
Auditoria operacional registra apenas ator, nome da ferramenta e evento, sem
mensagens, parâmetros, valores, PII ou segredos. Retenção depende do coletor atual.
Não há tenant_id nem mudança no modelo monoempresa; escopo futuro não é presumido.

As ferramentas ficam limitadas ao conjunto anunciado no início da requisição.
Antes de consultar, o usuário é atualizado no banco e a permissão é revalidada;
revogações bloqueiam a ferramenta e promoções não ampliam o conjunto já anunciado.

### Revisão: proveniência de indicadores e diagnóstico de tentativa

`CONFIRMADO`: o texto livre do modelo não é mais publicado pelo chat. A saída
final interna seleciona até três chaves de orientação de um catálogo fechado.
O backend valida o JSON, rejeita campos extras e redige a resposta pública.
Valores operacionais aparecem exclusivamente nas fontes calculadas pelo servidor.
Mesmo após uma consulta, o modelo não pode substituir ou reproduzir livremente
seus números; texto como “500 pedidos” ou “quinhentos pedidos” resulta em fallback,
conservando somente as fontes reais já consultadas. Sem fontes, `facts` é convertido
em aviso de consulta necessária. Isso limita a redação criativa da IA de propósito;
a interpretação da pergunta e a seleção de ferramentas continuam no provider real.
Não é uma heurística baseada em reconhecer algarismos ou palavras quantitativas.

`CONFIRMADO`: falha `DISTRIBUTION_CAPACITY_INSUFFICIENT` em otimização automática
retorna metadado aditivo `details[].assistant_diagnostic`. É um comprovante HMAC
com chave derivada para finalidade exclusiva, usuário, referência única e validade
de 15 minutos. Contém somente contagens e motivos permitidos, nunca IDs dos volumes,
placas, nomes, pedidos ou texto bruto do erro. Não é credencial de autenticação,
registro de distribuição nem confirmação de persistência. Nenhuma migration nova.

O frontend guarda o comprovante apenas no contexto volátil da conversa e não o
interpreta como fato. O backend verifica assinatura, validade, usuário e permissão
atual de criação de planejamento. Comprovante adulterado/expirado/de outro usuário
falha antes do provider. CHECKER não acessa diagnósticos de tentativas gerenciais.
O comprovante nunca é enviado à Groq. O contexto inclui data UTC e explicita que
se trata da tentativa passada, não da disponibilidade atual. Uma razão pode ocorrer
em conjunto com outras; suas contagens não devem ser somadas como volumes distintos.

`CONFIRMADO`: não reexecutamos o cálculo para explicar uma falha. O receipt não
muda locks, rollback, recuperação idempotente, limite de 200 volumes ou a física.
Falha de rede sem resposta confirmada não recebe um diagnóstico inventado.
