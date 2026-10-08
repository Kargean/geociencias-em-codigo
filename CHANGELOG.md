# Histórico de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/). Enquanto o livro estiver em construção, as versões são `0.x`.

## [Não lançado]

### Adicionado
- **Semana 0 · Alicerce** (`p0-00-semana0-alicerce.qmd`), novo primeiro capítulo de semana do P0-00, para quem parte do zero: o que são Git e GitHub e a diferença entre eles; o vocabulário em três tabelas; um passeio pelo repositório real do livro (a história do issue 4 ao PR 5); onde escrever cada informação (README, docstring, comentário, commit, CHANGELOG, issue, teste) com `doctest` executável; nomes e pastas; Markdown; licença e citação; terminal (Git Bash e PowerShell lado a lado); onde guardar as pastas; quatro jeitos de rodar os exemplos do livro; ambiente virtual; a rotina de cada sessão de estudo; como manter o clone do livro atualizado. Seis exercícios e um desafio com gabarito, entregável e autoavaliação. Inclui a seção **E o SQL? Onde rodar as consultas**: o que é um banco relacional, quatro lugares para rodar SQL (só "dentro do Python" foi testado), um exemplo conferido contra Python (o SQL ignora o `NULL` na média) e a injeção de SQL mostrada com parâmetro `?` e sem. O módulo passa de 4 para **5 semanas**.
- Módulo **P0-00**: projeto de partida com Git/GitHub, Python, SQL e testes (`projeto_chuva/`, uma visão geral e cinco capítulos de semana, da Semana 0 à 4).
- `tests/test_modulo_p0.py`: executa os capítulos, confere os números citados, valida a configuração do GitHub, as referências cruzadas e as opções de `gh` citadas.
- Fluxo de testes no GitHub Actions (`.github/workflows/testes.yml`), modelos de issue e de pull request, Dependabot, `CITATION.cff`, `.gitattributes` e `CLAUDE.md`.
- Laboratório de Git descartável (`geocodigo/laboratorio_git.py`) para exibir saídas reais de comandos.

### Corrigido
- `geocodigo/laboratorio_git.py`: o ambiente que o laboratório passa ao `subprocess` agora inclui `SYSTEMROOT`, `TEMP`, `TMP`, `COMSPEC` e `PATHEXT` quando existem. A documentação do `subprocess` exige `SystemRoot` num `env` próprio no Windows. **Não testado no Windows**: o laboratório nunca rodou lá. Achado na revisão independente da Semana 0.
- `chuva/cli.py`: os comandos `sql` e `banco` agora fecham a conexão com o banco em todos os caminhos (`finally`). Antes, o comando `sql --banco arquivo.db` deixava o arquivo aberto e, no **Windows**, `test_banco_cria_e_recusa_sobrescrever` falhava com `PermissionError: [WinError 32]` ao apagar a pasta temporária. Achado pela primeira execução dos testes num Windows (103 de 104 passaram); no Linux o erro era invisível. `test_cli.py` ganhou um espião de conexões, que faz o teste falhar também no Linux.
- `projeto_chuva/sql/esquema.sql`: as colunas numéricas passam a exigir `typeof(...) IN ('real', 'integer')`; antes, o SQLite aceitava texto (`'abc'`) em `chuva_mm`, porque a afinidade `REAL` só converte quando consegue e `'abc' >= 0` é verdadeiro. Achado na revisão independente dos capítulos; coberto por dois testes novos em `test_banco.py`.
- Capítulos das Semanas 3 e 4: explicação do `python -B` (só impede gravar `.pyc`), ordem para lançar uma versão com a `main` protegida, tipos de seção do *Keep a Changelog*, descrição do squash, `ROWS` (linha atual mais quatro), desempenho de índice.
- Prévia estática (`tools/previa_html.py`): resolve referências entre capítulos, respeita `echo: false` e não repete a saída já impressa.

### Alterado
- Visão geral do P0-00 e `index.qmd`: mapa de cinco semanas e uma nota sobre o terminal do Windows. O `README.md` deixa de chamar "Semana 0" a seção de colocar o livro no ar (o nome agora é do capítulo novo).
- Comandos copiáveis que só funcionavam no Git Bash: a Semana 3 ganhou a versão em PowerShell do `gh issue create` com várias linhas; a Semana 4 e o `README.md` não usam mais `&&` nem subshell `(...)`, que o Windows PowerShell 5.1 não aceita. Nova regra 8 no `CLAUDE.md`.
- `tests/test_modulo_p0.py` (20 testes): confere os números e as afirmações da Semana 0 (inclusive os da seção de SQL), executa o capítulo, verifica que blocos `bash` não usam acento grave e que o ambiente do laboratório é isolado.
- `.gitignore`: acrescenta `/.quarto/` e `**/*.quarto_ipynb`, as duas linhas exatas que o Quarto escreve sozinho no `.gitignore` quando faltam (conferido no código-fonte do Quarto; não executado), para que `quarto preview` e `quarto render` não deixem o clone com um arquivo alterado.
- Documentação dos limites (README e `CLAUDE.md`) atualizada com o que o primeiro `push` confirmou: testes verdes em Python 3.11, 3.12 e 3.13, renderização do Quarto e publicação no Pages concluídas. O passo de ativação do Pages agora diz que ele fica no *Settings do repositório*, não no do perfil (`github.com/settings/pages` mostra só domínios verificados).
- `publicar.yml` passa a rodar também os testes do projeto de chuva antes de publicar.
- Roteiro (Notion): **SQL passa a ser alicerce, como Python.** Novos módulos P1-06 a P1-08 (SQL essencial I a III, logo depois do pandas) e P3-11 (aplicativo com banco de dados, do esquema à publicação); P1-06 a P1-08 antigos viraram P1-09 a P1-11 e o P3-01 passou a tratar de modelagem avançada, índices, janelas e DuckDB. Total: 108 módulos, 152 semanas. A Semana 2 cita agora o P1-11 (formatos de tabela).
- Roteiro reorganizado em 12 partes (P0 a P11) com foco na pilha de ferramentas; estrutural e oceanografia viraram aplicações.
- `testes.yml` passa a rodar também em **Windows** (Python 3.13), além do Linux em 3.11, 3.12 e 3.13.

## Antes do primeiro lançamento

### Adicionado
- Estrutura do livro em Quarto e publicação automática no GitHub Pages (não testada no GitHub até o primeiro uso).
- Capítulo de exemplo: *Atitudes e projeção estereográfica* (módulo P9-06), com testes dos números citados no texto.
