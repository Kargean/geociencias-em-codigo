# Histórico de mudanças

Formato inspirado em [Keep a Changelog](https://keepachangelog.com/pt-BR/). Enquanto o livro estiver em construção, as versões são `0.x`.

## [Não lançado]

### Adicionado
- Módulo **P0-00**: projeto de partida com Git/GitHub, Python, SQL e testes (`projeto_chuva/`, uma visão geral e quatro capítulos de semana).
- `tests/test_modulo_p0.py`: executa os cinco capítulos, confere os números citados, valida a configuração do GitHub, as referências cruzadas e as opções de `gh` citadas.
- Fluxo de testes no GitHub Actions (`.github/workflows/testes.yml`), modelos de issue e de pull request, Dependabot, `CITATION.cff`, `.gitattributes` e `CLAUDE.md`.
- Laboratório de Git descartável (`geocodigo/laboratorio_git.py`) para exibir saídas reais de comandos.

### Corrigido
- `projeto_chuva/sql/esquema.sql`: as colunas numéricas passam a exigir `typeof(...) IN ('real', 'integer')`; antes, o SQLite aceitava texto (`'abc'`) em `chuva_mm`, porque a afinidade `REAL` só converte quando consegue e `'abc' >= 0` é verdadeiro. Achado na revisão independente dos capítulos; coberto por dois testes novos em `test_banco.py`.
- Capítulos das Semanas 3 e 4: explicação do `python -B` (só impede gravar `.pyc`), ordem para lançar uma versão com a `main` protegida, tipos de seção do *Keep a Changelog*, descrição do squash, `ROWS` (linha atual mais quatro), desempenho de índice.
- Prévia estática (`tools/previa_html.py`): resolve referências entre capítulos, respeita `echo: false` e não repete a saída já impressa.

### Alterado
- Documentação dos limites (README e `CLAUDE.md`) atualizada com o que o primeiro `push` confirmou: testes verdes em Python 3.11, 3.12 e 3.13, renderização do Quarto e publicação no Pages concluídas. O passo de ativação do Pages agora diz que ele fica no *Settings do repositório*, não no do perfil (`github.com/settings/pages` mostra só domínios verificados).
- `publicar.yml` passa a rodar também os testes do projeto de chuva antes de publicar.
- Roteiro reorganizado em 12 partes (P0 a P11) com foco na pilha de ferramentas; estrutural e oceanografia viraram aplicações.

## Antes do primeiro lançamento

### Adicionado
- Estrutura do livro em Quarto e publicação automática no GitHub Pages (não testada no GitHub até o primeiro uso).
- Capítulo de exemplo: *Atitudes e projeção estereográfica* (módulo P9-06), com testes dos números citados no texto.
