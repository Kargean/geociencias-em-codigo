"""Projeto de partida: chuva diária em estações (dados sintéticos).

Este pacote é o fio condutor do módulo P0-00 do livro: um projeto pequeno, completo e testado,
que serve para aprender Git/GitHub, Python e SQL ao mesmo tempo.

Módulos:
    sintetico  gera os dados (com defeitos plantados em posições conhecidas)
    qualidade  lê o CSV, limpa, relata o que encontrou
    resumo     cálculos em Python puro (totais mensais, dias de chuva, CDD, Rx5day)
    banco      SQLite: esquema, carga e consultas
    cli        interface de linha de comando (python -m chuva ...)
"""

__version__ = "0.1.0"
