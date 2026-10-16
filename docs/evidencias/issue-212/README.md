# Evidências — aparência (#212)

`CONFIRMADO`: Chromium headless local, viewport 375×900, 768×1000,
1280×1000 e 1920×1000. Conta ADMIN fictícia com respostas de consulta
interceptadas no navegador; não constitui teste do backend ou de autenticação real.

Oito capturas `aparencia-<largura>-<light|dark>.png` mostram Meu perfil com o
sistema em aparência oposta à escolha manual. Revisadas as capturas desktop e
mobile: controles legíveis, sem sobreposição e com adaptação em coluna no mobile.
`resultados.json` registra tema efetivo, `color-scheme`, ausência de overflow e
erros JavaScript, troca automática do sistema, teclado (seta em rádio) e F5.

`CONFIRMADO`: testes de componente cobrem armazenamento bloqueado/inválido,
persistência, atualização da cena 3D e sincronização de abas. Testes existentes
de Meu perfil verificam acesso aos quatro perfis. Sem API/migration nova.

`RISCO IDENTIFICADO`: preferência é por navegador, não por conta; armazenamento
bloqueado impede persistência. O bootstrap externo evita esperar React e não
altera CSP; velocidade de carregamento depende da rede/cache.

`PENDENTE DE DEFINIÇÃO`: revisão visual integrada de MFA/recuperação depende da
OC98 (PR #211 ainda aberta na validação). Essas telas não foram incorporadas nem
validadas nesta branch. Não foi produzida métrica de cobertura instrumentada.
