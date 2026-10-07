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
* `p0-00-*.qmd`: os cinco capítulos do módulo de partida P0-00 (visão geral e Semanas 1 a 4). `projeto_chuva/`: o projeto de referência do módulo (só biblioteca padrão do Python).
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

## Como rodar os testes

```bash
python tests/test_estrutural.py            # matemática do capítulo de exemplo (precisa de numpy)
python tests/test_capitulo.py              # números citados no capítulo de exemplo
python tests/test_modulo_p0.py             # capítulos do módulo P0-00 e configuração do GitHub
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

* Renderização pelo Quarto e publicação no GitHub Pages (a primeira execução do fluxo é o teste real).
* Execução do `testes.yml` no GitHub Actions (os mesmos comandos foram executados localmente em Python 3.13; 3.11 e 3.12 só no GitHub).
* A interface do GitHub muda com o tempo: passos de clique nos capítulos (issues, pull requests, rulesets, Insights) devem ser conferidos na tela atual. Os comandos `gh` tiveram as opções conferidas na ajuda da versão 2.89.0, mas não foram executados contra o GitHub.
* O `Saida._ipython_display_` do laboratório de Git (`geocodigo/laboratorio_git.py`) deve impedir que o Quarto repita, como texto entre aspas, a saída dos comandos quando ela é a última linha de um bloco. Foi conferido só na prévia estática; se a renderização real mostrar linhas duplicadas entre aspas, é isso.
* `pytest`, `coverage`, `pre-commit` e `act` são citados como caminho futuro e **não** foram executados.
