# Issue #371 — intenção e cobertura confiável do Loxi

Base `73fd043`, PR separada de planejamento/3D. Sem merge, deploy ou segredos reais.

## Executado

- Reproduzido no backend/base original: “Fale sobre as configurações” no plano
  respondia com o caminhão QA3A234. Captura `before-wrong-settings-1280-dark.png`.
- Depois: orientação de configurações, sem consulta ao plano antigo. Capturas
  `loxi-settings-*`, fonte documentada compacta, começo da resposta visível.
- Chromium/API/PostgreSQL 16 reais, sem interceptar HTTP: nove perguntas/consultas,
  oito combinações 1920/1280/768/375 e claro/escuro, cinco perfis permitidos/negados.
  Sessões são fixtures sintéticas; não valida login/MFA. `browser-results.json`.
- Testes backend: 113 unitários direcionados; 27 integrações/OpenAPI existentes
  revalidadas e cinco integrações novas de documentação, paginação, consultas
  sem PII, comparação com negação parcial e distribuição real. Não executada suíte
  backend completa localmente; CI completa disparada na PR, sem aguardar Pytest.
- Frontend: 27 testes focados, ESLint, TypeScript, build e budget aprovados.
  Backend: Ruff check/format. Pacotes diretos conferidos contra os locks; sem
  mudança de dependências. Sem migration ou mudança de estados/permissões.

## Limitações explícitas

- Sem chave real disponibilizada nesta execução: não há aceite externo da Groq.
  Seleção semântica de ferramenta e conversa natural foram testadas com provider
  simulado em testes; browser valida fontes reais do backend, não inferência externa.
- `capacidades.md` diferencia módulos com leitura de registros daqueles que só têm
  orientação/link. Não declara consulta direta completa a todas as entidades.
- GENERAL não equivale a informação factual verificada. Indicadores/nomes de
  cadastros mantêm fontes e autorização no backend. Proteções linguísticas não são
  prova universal contra toda variação possível de prompt injection.
- Não recebidas as três novas capturas mencionadas no texto; antes/depois são do
  sistema real. As referências visuais anteriores foram preservadas.
- CI/Sonar/Segurança completos ficam para acompanhamento no GitHub conforme pedido.

Verificação de dependências compartilhadas pelas duas PRs: npm audit no nível high
aprovado (zero high/critical; dois moderados preexistentes em dependências de testes).
Os deep links usam hashes reais de Configurações e abas existentes de Contatos.
