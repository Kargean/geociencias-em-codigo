# Geociências em Código

Livro-laboratório em **Quarto** (HTML publicado no GitHub Pages) sobre geoprocessamento, estatística e modelagem de fenômenos da Terra. Cada capítulo executa código de verdade, gera as figuras e termina com experimentos, exercícios com gabarito conferido e autoavaliação.

**Foco:** a pilha de ferramentas da análise e modelagem ambiental (Python, dados, GIS, sensoriamento remoto e PDI, estatística, aprendizado de máquina, bancos de dados, APIs e interfaces), do básico ao avançado; hidrologia, hidrogeologia, geoquímica, geotecnia, estrutural e oceanografia entram como aplicações.

**Estado:** estão escritos o **módulo de partida P0-00** (Git e GitHub, Python, SQL e testes, em seis capítulos: visão geral e Semanas 0 a 4) e um capítulo de exemplo (*Atitudes e projeção estereográfica*, módulo P9-06). O resto do mapa (partes P0 a P11, ver `index.qmd`) será produzido semana a semana, a partir de P1.

## O que há aqui

```
_quarto.yml                  configuração do livro (capítulos, tema, idioma)
index.qmd                    apresentação e mapa do livro
p0-00-*.qmd                  módulo de partida P0-00: visão geral e Semanas 0 a 4
cap-estrutural-atitudes.qmd  capítulo de exemplo (texto + código + figura interativa)
projeto_chuva/               projeto de referência do P0-00 (Python, SQL e testes; só biblioteca padrão)
references.bib               bibliografia
requirements.txt             pacotes Python do livro
geocodigo/                   funções reutilizáveis (estrutural.py, graficos.py, laboratorio_git.py)
dados/                       dados do livro e o gerador dos dados sintéticos
tests/                       testes (matemática, números citados no texto, módulo P0-00)
tools/                       verificadores e gerador de prévia (funcionam sem o Quarto)
.github/                     testes automáticos, publicação no Pages, formulários de issue, modelo de PR, Dependabot
CLAUDE.md                    memória do projeto: regras, fluxo de trabalho, o que falta verificar
CHANGELOG.md                 histórico de mudanças
CITATION.cff                 como citar
```

## Colocar o livro no ar (uma vez só, ~1 hora)

> **Atalho com Git e `gh` instalados** (o módulo P0-00 ensina isso). Dentro da pasta do livro: `git init -b main`, `git add .`, `git commit -m "Primeira versão do livro"`, `gh auth login` e `gh repo create geociencias-em-codigo --public --source=. --remote=origin --push`. Depois, pule para o passo 5. Os passos 1 a 4 abaixo são o caminho **sem** Git, pelo navegador.

1. **Conta no GitHub:** crie em github.com (se ainda não tem). Dica: para o benefício *GitHub Education* de professores, é preciso verificar vínculo com a instituição; isso pode ser feito depois, sem pressa.
2. **Repositório vazio:** clique em **+ → New repository**. Nome: `geociencias-em-codigo`. Marque **Public** (a publicação gratuita no GitHub Pages funciona direto em repositórios públicos). **Não** marque “Add a README”.
3. **Enviar os arquivos:** na página do repositório vazio, clique em **uploading an existing file**, arraste o *conteúdo* desta pasta (arquivos e subpastas `geocodigo`, `dados`, `tests`, `tools`, `projeto_chuva`) e clique em **Commit changes**.
4. **Criar os arquivos “ocultos” pelo navegador** (pastas que começam com ponto costumam ser ignoradas no arrastar-e-soltar):
   * **Add file → Create new file**, nome `.github/workflows/publicar.yml` (digitar as barras cria as pastas), cole o conteúdo do arquivo de mesmo nome que acompanha este pacote e confirme o commit;
   * repita para `.gitignore` e para cada arquivo da pasta `.github/` (`workflows/testes.yml`, `ISSUE_TEMPLATE/*`, `pull_request_template.md`, `dependabot.yml`). É trabalhoso, e é um bom motivo para aprender o Git no módulo P0-00.
5. **Ativar a publicação:** abra o **seu repositório** (`github.com/SEU-USUARIO/geociencias-em-codigo`), clique na aba **Settings** que fica na barra do repositório (a última, à direita de Insights) e, no menu à esquerda, em **Pages**. Em **Build and deployment → Source**, escolha **GitHub Actions**. Atenção: o *Settings* do seu perfil (menu da foto, `github.com/settings/pages`) tem uma página "Pages" que só mostra domínios verificados; não é essa.
6. **Acompanhar:** aba **Actions**. O fluxo “Publicar livro” roda a cada `push` na branch `main`. Se a primeira execução falhar com mensagem sobre o Pages ainda não estar ativado, faça o passo 5 e clique em **Re-run all jobs**.
7. O livro aparece em `https://SEU-USUARIO.github.io/geociencias-em-codigo/`. Depois, em `_quarto.yml`, descomente `repo-url` e troque `SEU-USUARIO`.

## Usar no seu computador

```bash
pip install -r requirements.txt     # uma vez
python tests/test_estrutural.py     # a matemática confere?
python tests/test_capitulo.py       # os números do texto conferem?
python tests/test_modulo_p0.py      # módulo P0-00: capítulos, números citados, configuração do GitHub
cd projeto_chuva                    # testes do projeto de chuva: entre na pasta,
python -m unittest discover -s tests -v
cd ..                               # e volte para a raiz do livro
quarto preview                      # abre o livro no navegador, atualizando ao salvar
```
O Quarto se instala à parte (quarto.org). Sem ele, ainda dá para: `python tools/executar_codigo_qmd.py cap-estrutural-atitudes.qmd` (roda os blocos de código), `python tools/testar_widget.py` (testa a figura interativa; precisa do pacote `playwright`) e `python tools/previa_html.py cap-estrutural-atitudes.qmd previa.html` (gera uma prévia estática; precisa do `pandoc`).

## Git em seis comandos

| Comando | Para quê |
|:--|:--|
| `git status` | o que mudou desde o último commit |
| `git add -A` | separar todas as mudanças para o próximo commit |
| `git commit -m "mensagem"` | gravar um ponto na história, com um recado |
| `git push` | enviar para o GitHub (e disparar a publicação do livro) |
| `git pull` | trazer do GitHub o que mudou lá |
| `git log --oneline` | ver a história resumida |

## O que foi e o que NÃO foi testado

**Testado:** a matemática do capítulo de exemplo (9 testes) e todos os números citados no texto dele (47 conferências); a execução ponta a ponta de todos os blocos de código dos seis capítulos do módulo P0-00, **inclusive os gabaritos** (`tests/test_modulo_p0.py`, 19 testes); os 104 testes do projeto de chuva; os comandos de Git das Semanas 0, 1 e 3, **executados de verdade** num laboratório descartável (com um "GitHub de mentirinha" local); a validade dos arquivos de configuração do GitHub (YAML) e as opções de `gh` citadas, conferidas na ajuda da versão instalada; a figura interativa no Chromium; uma prévia estática dos capítulos; e, **no próprio GitHub** (primeiro `push`, 07/10/2026), o fluxo **Testes** em Python 3.11, 3.12 e 3.13 e o fluxo **Publicar livro** inteiro (testes do livro e do projeto de chuva, renderização do Quarto e publicação no Pages), todos verdes.

**Não testado:**

* a **aparência final** do livro publicado (cores, tamanho das figuras, leitura no celular): a publicação funciona (o Pages foi ativado e o job `deploy` ficou verde em 07/10/2026) e o texto dos capítulos foi lido na página, sem repetição de saídas entre aspas, sem erro e com as referências entre capítulos resolvidas, mas a leitura foi feita por um leitor de texto, não por um navegador;
* **os passos de clique na interface do GitHub** descritos na Semana 3 (issues, pull requests, rulesets, Insights): vêm da documentação e do uso comum, e devem ser conferidos na tela atual;
* **o laboratório de Git (`geocodigo/laboratorio_git.py`) no Windows:** nunca rodou lá (o teste automático do Windows roda só o projeto de chuva); os níveis C e D de execução do livro e o `tests/test_modulo_p0.py` também não;
* **os passos do capítulo da Semana 0 que dependem do seu computador:** a instalação dos pacotes por `pip` em ambiente novo (o PyPI não era acessível na sessão de escrita; a lista de pacotes foi conferida pelos `import`), a ativação do ambiente virtual e o terminal integrado no Windows, o PowerShell 5.1 sem `&&`, a pasta sincronizada pelo OneDrive, e as abas do site do GitHub como estão hoje;
* `pytest`, `coverage`, `pre-commit` e `act`, citados só como próximos passos.

## Licença

A definir (sugestão: CC BY-NC-SA para o texto e MIT para o código).
