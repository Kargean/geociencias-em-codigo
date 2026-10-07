# Projeto de partida: chuva diária em estações

Projeto pequeno, completo e testado, usado no módulo **P0-00** do livro *Geociências em Código* para aprender, ao mesmo tempo, **Git/GitHub**, **Python**, **SQL** e **testes automáticos**.

**Os dados são sintéticos e as quatro estações são fictícias.** Isso é de propósito: como os defeitos foram plantados em posições conhecidas, os testes conseguem dizer se a limpeza funciona.

## O que o projeto faz

1. Lê um CSV "sujo" de chuva diária (código `-999`, células vazias, vírgula decimal, linhas duplicadas, datas sem linha, valores impossíveis).
2. Aplica regras explícitas de limpeza e escreve um relatório do que encontrou.
3. Calcula índices em Python puro: total mensal, dias de chuva, maior período seco (CDD) e maior acumulado em 5 dias (Rx5day).
4. Carrega os dados limpos num banco SQLite e calcula os mesmos números em SQL.
5. Testa que Python e SQL concordam.

## Como rodar (só biblioteca padrão do Python 3.11 ou mais novo; não há nada para instalar)

Todos os comandos partem desta pasta (`projeto_chuva`).

```bash
python -m unittest discover -s tests -v     # todos os testes
python -m chuva qualidade                    # relatório de qualidade do CSV
python -m chuva resumo                       # CDD, Rx5day e dias de chuva por estação
python -m chuva sql 05_maior_periodo_seco    # uma consulta SQL
python -m chuva banco --saida chuva.db       # grava o banco em arquivo
```

## Mapa das pastas

```
chuva/       pacote Python (sintetico, qualidade, resumo, banco, cli)
dados/       CSVs oficiais, SHA256SUMS (impressão digital deles) e o gerador
sql/         esquema.sql e as consultas numeradas em sql/consultas/
tests/       testes (unittest, só biblioteca padrão)
```

## Os defeitos plantados

| Defeito | Quantidade | Como o projeto trata |
|:--|--:|:--|
| Ausente escrito como `-999`, `-999.0` | 6 | vira `None` (NULL no banco) |
| Ausente como célula vazia | 3 | vira `None` |
| Linha inteira ausente (dia sem linha) | 4 | detectada em `datas_ausentes`; interrompe períodos secos e janelas |
| Vírgula decimal (`"12,4"`) | 3 | convertida para ponto |
| Linha duplicada idêntica | 2 | uma é removida |
| Mesma chave, valores diferentes | 1 | vale a primeira linha; fica no relatório |
| Chuva negativa | 1 | vira `None` |
| Chuva acima de 300 mm em um dia | 1 | vira `None` |

## Decisões que o código registra (mude com consciência)

* Dia com chuva: `>= 1,0 mm`; dia seco: `< 1,0 mm` (convenção dos índices ETCCDI).
* Acima de 300 mm em um dia, o valor é tratado como erro até prova em contrário.
* Para chaves repetidas, vale a primeira linha.
* Total mensal soma só os dias válidos; o campo `completo` avisa quando o mês tem dia faltando.
