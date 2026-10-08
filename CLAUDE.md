# Instruções do projeto para o Claude

Este arquivo é a memória do projeto. Leia-o ao começar uma sessão e atualize-o quando uma regra mudar (no mesmo pull request que muda a regra).

## Quem e para quê

* Autor: Kargean Vianna Barbosa, professor de geologia (IFFluminense, Campos-Guarus). Idioma de tudo: português do Brasil.
* O projeto é um **mega curso pessoal**, dinâmico, sem prazo, que também servirá de base para uma disciplina de pós-graduação em geoprocessamento.
* O foco é a **pilha de ferramentas** da análise e modelagem ambiental: Python, dados, GIS, sensoriamento remoto e PDI, estatística, multivariada, geoestatística, aprendizado de máquina, bancos de dados, APIs e interfaces. Hidrologia, hidrogeologia, geoquímica, geotecnia, estrutural e oceanografia são **aplicações**.
* Preferências do autor: informação **precisa, segura, compreensível e didática**; passo a passo; exemplos aplicados com resultados explicados; nunca inventar nem esconder incerteza. Diga com clareza o que foi testado e o que não foi.

## Onde fica cada coisa

* **Este repositório:** o livro (Quarto, HTML no GitHub Pages) e o código que o acompanha.
* **Notion:** acompanhamento de estudo (módulos, níveis, datas). O roteiro tem 12 partes, P0 a P11, e a numeração dos módulos vem de lá.
* `p0-00-*.qmd`: os seis capítulos do módulo de partida P0-00 (visão geral e Semanas 0 a 4; a Semana 0, `p0-00-semana0-alicerce.qmd`, é o alicerce: Git, GitHub, vocabulário, documentação e ambiente). `projeto_chuva/`: o projeto de referência do módulo (só biblioteca padrão do Python).
* `p1-06-sql-essencial-i.qmd`: primeiro capítulo de SQL (SQLite, qualidade da água sintética, CONAMA 357/2005). `p1-07-sql-essencial-ii.qmd`: agregação, `GROUP BY`, `HAVING`, chaves e `JOIN` (o erro clássico: o `JOIN` que multiplica linhas), com conferência no pandas; `tools/registro_postgresql_p1-07.sql` é o roteiro que o PostgreSQL executou. Os capítulos de P1 em diante usam o prefixo do módulo (`p1-08-...`) e entram na parte P1 do `_quarto.yml`.
* `.github/`: workflows (testes e publicação), formulários de issue, modelo de pull request e Dependabot.
* `geocodigo/`: funções reutilizáveis do livro. `tools/`: verificadores que funcionam sem o Quarto. `tests/`: testes do livro.

## Regras do método (valem para todo capítulo)

1. **Dados sintéticos primeiro**, para a verdade ser conhecida e o erro do método poder ser medido. Dados reais vêm depois.
2. **Construir cada ferramenta uma vez a partir da matemática** antes de usar pacotes prontos; depois conferir o pacote contra o nosso cálculo.
3. **Todo número citado no texto é conferido por teste** que roda o mesmo código do capítulo.
4. **Convenções declaradas** (ângulos, sistemas de coordenadas, unidades, limiares) no início de cada assunto.
5. Cada capítulo termina com **erros clássicos**, **exercícios com gabarito conferido em código** e **autoavaliação** em quatro níveis (reconheço, explico, executo, ensino).
6. Decisões de limpeza e de limiar ficam **em constantes nomeadas e documentadas**, nunca escondidas.
7. **Recursos abertos são fechados em `finally`** (conexões de banco, arquivos). O autor usa Windows, onde arquivo aberto não pode ser apagado; o Linux perdoa. Testes de código que abre arquivos devem conferir o fechamento.
8. **Comandos de terminal nos capítulos são escritos para o Git Bash** (blocos `bash`). O autor usa Windows com PowerShell, e três coisas mudam lá: a continuação de linha (`\` vira acento grave), o `&&` (não existe no Windows PowerShell 5.1) e a ativação do `venv`. Quando um comando copiável depende disso, o capítulo traz um bloco `powershell` ou uma nota (tabela na Semana 0). Blocos `bash` não usam acento grave.
9. **Exemplos sempre ambientais e de aplicação real** (pedido do autor, 08/10/2026). Use dados sintéticos (a verdade é conhecida) ou exemplos existentes (dados abertos e casos publicados, com fonte, data e versão registradas), voltados a questões ambientais e a aplicações reais. Evite exemplos abstratos sem contexto (`foo`, `bar`, `x`, `y`).

## Como rodar os testes

```bash
python tests/test_estrutural.py            # matemática do capítulo de exemplo (precisa de numpy)
python tests/test_capitulo.py              # números citados no capítulo de exemplo
python tests/test_modulo_p0.py             # capítulos do módulo P0-00 e configuração do GitHub
python tests/test_modulo_p1.py             # capítulos P1-06 e P1-07 (SQL essencial I e II; o P1-07 precisa do pandas)
cd projeto_chuva && python -m unittest discover -s tests -v   # testes do projeto de chuva
```

## Fluxo de trabalho no Git

* Nunca trabalhar direto na `main` quando houver mais de uma mudança: criar branch `tipo/descricao` (`feat/`, `fix/`, `docs/`), abrir pull request, esperar os testes ficarem verdes, juntar, apagar a branch.
* Mensagens de commit curtas, no imperativo, uma ideia por commit. Referenciar o issue com `Closes #N`.
* Atualizar o `CHANGELOG.md` quando a mudança aparece para quem lê.
* **Nunca** gravar senhas, tokens ou chaves de API em arquivo do repositório. Se um segredo vazar, revogue-o primeiro; apagar o commit não basta.
* Não mexer em outros repositórios da conta do autor sem pedido explícito.

## Para escrever um capítulo novo

1. Ler a página do módulo no Notion (escopo, erro clássico, prática de domínio).
2. Reunir o material e as fontes (consultar a documentação atual; versões de pacotes mudam).
3. Escrever o código e os testes primeiro; só então o texto, citando números que o teste confere.
4. Rodar `tools/executar_codigo_qmd.py capitulo.qmd --gabaritos` e os testes.
5. Atualizar `_quarto.yml`, o `CHANGELOG.md` e o status do módulo no Notion ("Capítulo no livro").

## O que ainda não foi verificado (atualize ao confirmar)

* **Confirmado no GitHub (07/10/2026):** `testes.yml` verde em Python 3.11, 3.12 e 3.13; `publicar.yml` verde (testes, renderização do Quarto e deploy no Pages). O Pages precisou ser ativado à mão (aba Settings **do repositório**, não a do perfil → Pages → Source: GitHub Actions) e o job `deploy` reexecutado.
* **Lido na página publicada** (por leitor de texto): os capítulos P0-00 aparecem na barra lateral, sem erro, sem saídas repetidas entre aspas (o `Saida._ipython_display_` parece funcionar) e sem referências quebradas. **Não visto:** a aparência (cores, figuras, celular). Se a aparência incomodar, abrir uma issue `melhoria`.
* A figura das quatro áreas do Git é servida como PNG (o arquivo existe), mas não vimos a imagem.
* A interface do GitHub muda com o tempo: passos de clique nos capítulos (issues, pull requests, rulesets, Insights) devem ser conferidos na tela atual. Os comandos `gh` tiveram as opções conferidas na ajuda da versão 2.89.0, mas não foram executados contra o GitHub.
* **`tests/test_modulo_p0.py`, `tests/test_modulo_p1.py` e `tests/test_capitulo.py` não rodam no GitHub Actions** (só `test_estrutural.py` e o projeto de chuva, em `publicar.yml` e `testes.yml`). Antes de juntar um PR que mexe em capítulo, rode-os localmente. Próximo passo: um passo no Actions (instalar `pyyaml` e `matplotlib`), no Linux primeiro.
* **Laboratório de Git no Windows:** `geocodigo/laboratorio_git.py` nunca rodou lá (o job do Windows só roda `projeto_chuva`). O `env` do `subprocess` foi reforçado com `SYSTEMROOT` e afins por precaução, sem teste no Windows. Para cobrir, seria preciso rodar `tests/test_modulo_p0.py` no Windows (instalar `pyyaml` e `matplotlib`); isso muda o `testes.yml` e o texto da Semana 3.
* **Semana 0 (alicerce):** os passos que dependem do computador do leitor não foram executados num Windows: `pip install matplotlib pyyaml` em ambiente novo (o PyPI não era acessível na sessão de escrita; a lista vem dos `import` dos capítulos), a ativação do `venv` e a política de execução do PowerShell, o terminal integrado do VS Code, o `powershell` na barra de endereço do Explorador, o PowerShell 5.1 sem `&&`, o risco de pasta no OneDrive, e os nomes das abas e dos ícones do site do GitHub. O nível D (renderizar o livro com o Quarto no Windows) também não foi testado. Na seção de SQL, só o módulo `sqlite3` do Python foi executado (no Linux); DB Browser for SQLite, o comando `sqlite3` do terminal e as extensões do VS Code não foram testados. Na seção de servidores, o servidor de brinquedo (`socketserver`, só em `127.0.0.1`) foi executado só no Linux (30 execuções seguidas) e **não** num Windows (aviso de firewall, nome do erro depois do desligamento, pasta temporária); a sessão do PostgreSQL 16.15 é um **registro estático** (08/10/2026), que nenhum teste reexecuta (o teste só confere que os números dele batem com os do SQLite do capítulo); a instalação do PostgreSQL no Windows não foi testada. Se o capítulo citar outra versão do PostgreSQL, refaça o registro.
* **P1-06 (SQL essencial I):** testado só no Linux, com o SQLite 3.45.1 e Python 3.11, 3.12 e 3.13 (figuras só no 3.13). O registro das diferenças de dialeto do PostgreSQL 16.15 (08/10/2026) é **estático**: `tests/test_modulo_p1.py` só confere que há uma entrada para cada sonda e que o texto o cita corretamente. Se o capítulo citar outra versão, refaça o registro. **Não foi conferido** se resoluções posteriores à CONAMA 357/2005 (410/2009, 430/2011) mudaram os limites usados. Lição da escrita: o parâmetro numerado `?1` com tupla gera `DeprecationWarning` no Python 3.12 (erro no 3.14); use parâmetros nomeados (`:nome`) com dicionário. O teste do capítulo trata `DeprecationWarning` como erro.
* **P1-07 (SQL essencial II):** rodou de ponta a ponta no Python 3.13 (SQLite 3.45.1, pandas 3.0.5, matplotlib 3.11.2) e, **sem as células do pandas e sem a figura**, no 3.11 e no 3.12 (nesses dois não há pandas nem matplotlib no ambiente de escrita). Só no Linux. As 27 consultas e as 14 sondas rodaram no PostgreSQL 16.15 uma vez (08/10/2026; roteiro em `tools/registro_postgresql_p1-07.sql`); a comparação com o SQLite foi feita por um script auxiliar que **não** está no repositório, e nenhum teste reexecuta o PostgreSQL. O erro de uma gravação recusada em `DataFrame.to_sql` foi visto como `pandas.errors.DatabaseError` só no pandas 3.0.5; o capítulo trata também `sqlite3.Error`. Não conferi desde qual versão do SQLite existem `string_agg`, `RIGHT JOIN` e `FULL JOIN`, nem a CONAMA 410/2009 e 430/2011. Lição da escrita: no Python, um `INSERT` ou `DELETE` recusado deixa uma transação aberta, e `Connection.backup()` de uma conexão com transação aberta **trava**; encerre com `rollback()` antes de copiar o banco.
* `pytest`, `coverage`, `pre-commit` e `act` são citados como caminho futuro e **não** foram executados.
