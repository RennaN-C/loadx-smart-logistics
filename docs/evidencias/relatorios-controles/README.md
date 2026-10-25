# Relatórios e controles profissionais — Issue #308

CONFIRMADO: melhoria visual solicitada pelo responsável em 25/10/2026. Os três
PDFs existentes compartilham identidade LoadX navy/âmbar, resumo, tabelas
proporcionais, linhas alternadas, cabeçalhos repetidos e rodapé paginado com
emissão UTC. O gerencial apresenta barras de contagens reais, com ressalva de
que indicadores distintos não devem ser somados. Tipos e situações conhecidos
são localizados nas colunas próprias; códigos de produto permanecem literais.

CONFIRMADO: também foram padronizados plano salvo, odômetro, renovação documental
de caminhões/motoristas, cadastro de tipos e políticas. A sobreposição do
cabeçalho móvel sobre modais foi corrigida. Permissões, endpoints, CSV, dados,
handlers e regras operacionais são os existentes. Nenhuma dependência de runtime
ou migration foi adicionada.

## Exemplos exportados

CONFIRMADO: estes arquivos foram gerados pelos métodos reais de ReportService e
ManagementReportService com fontes fictícias em memória, sem gravação no banco.
Datas, placa e identificadores são de demonstração. Os exemplos não representam
resultados humanos de usabilidade nem uma operação real.

- [Carregamento](carregamento-exemplo.pdf): duas páginas, dez volumes, sete conferidos.
- [Viagem](viagem-exemplo.pdf): duas páginas com entregas, ocorrência e identidades dos volumes.
- [Gerencial](gerencial-exemplo.pdf): uma página com nove indicadores e gráficos.

CONFIRMADO: PNGs de cada página foram renderizados para inspeção. A verificação
das coordenadas do texto não encontrou conteúdo fora da página A4. PyMuPDF foi
usado somente como ferramenta local de inspeção, isolado em `.tmp/pdf-tools`;
não foi adicionado às dependências do sistema.

## Validação

CONFIRMADO: onze testes unitários de PDF/gerencial passaram, cobrindo caracteres
especiais e escape, UUID completo, 180 linhas em múltiplas páginas, linha maior
que uma página sem perda de texto, conjunto vazio, valores zero e rótulos de
situação sem alterar códigos de produto. O teste gerencial confirma uma página.

CONFIRMADO: três testes de integração/E2E passaram em Python 3.12, PostgreSQL 16
exclusivo `loadx_test` de `compose.test.yaml`: download dos dois PDFs,
autorização/fonte ausente e duas pernas multi-caminhão com PDFs reais e extração
de seus UUIDs. A suíte mantém as verificações de não misturar partes ou volumes.
Não usa o banco local da aplicação. O ambiente Windows mínimo não possuía todas
as dependências de integração; essa validação foi concluída em container efêmero
com as dependências de runtime e ferramentas de teste isoladas.

CONFIRMADO: 1.130 testes frontend passaram; o recorte dos componentes alterados
teve 185 aprovações. ESLint, TypeScript/build, Ruff e orçamento do bundle passaram.
O build mantém aviso preexistente de tamanho do chunk 3D, com orçamento aprovado.

CONFIRMADO: Chromium abriu a aplicação React local com respostas HTTP fictícias
controladas, sem credenciais nem alterações no banco. Foram 30 verificações:
cinco estados × temas claro/escuro × larguras 1366/768/375 px. Os estados são
quilometragem, renovação do caminhão, documentos e renovação do motorista e plano
salvo. Nenhum erro JavaScript, rolagem horizontal ou botão nativo sem estilo foi
encontrado nos modais. Houve verificação de foco por teclado, retorno de Cancelar,
link do plano e hit testing para títulos de modais não encobertos. Essas capturas
não constituem validação de autenticação real; os testes API e E2E acima cobrem
os contratos e a operação.

RISCO IDENTIFICADO: o aceite visual final e os demais gates da v1.2.0 continuam
independentes desta revisão. Os relatórios registram o estado consultado, sem
prometer snapshot transacional de todo o sistema.
