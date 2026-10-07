"""Leitura e limpeza do CSV de chuva diária.

Princípio: o arquivo do fornecedor nunca é alterado. Lemos, aplicamos regras EXPLÍCITAS e escrevemos
um relatório do que foi encontrado. Cada regra é uma decisão humana e fica registrada aqui, no código.
"""
from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

# Textos que o fornecedor usa para "sem medida". Regra de decisão: viram None (ausente), nunca número.
CODIGOS_AUSENTE = frozenset({"-999", "-999.0", "-9999"})

# Regra de decisão: acima disso, em um dia, tratamos como erro (a verificar), e não como medida.
LIMITE_MM_DIA = 300.0

_NUMERO = re.compile(r"\d+(\.\d+)?")  # só dígitos, com ponto decimal opcional (o sinal é tratado à parte)


@dataclass(frozen=True)
class Registro:
    """Uma medida: chuva (mm) numa estação em um dia. chuva_mm = None significa 'sem medida válida'."""

    estacao: str
    data: date
    chuva_mm: float | None


@dataclass
class Relatorio:
    """O que a leitura encontrou. Contagens por LINHA lida (duplicatas incluídas)."""

    linhas_lidas: int = 0
    ausentes_codigo: int = 0
    ausentes_vazio: int = 0
    virgula_decimal: int = 0
    negativos: int = 0
    acima_do_limite: int = 0
    duplicatas_exatas: int = 0
    duplicatas_conflitantes: int = 0
    registros_finais: int = 0

    def texto(self) -> str:
        itens = [
            ("linhas lidas", self.linhas_lidas),
            ("ausentes por código (-999...)", self.ausentes_codigo),
            ("ausentes por célula vazia", self.ausentes_vazio),
            ("valores com vírgula decimal", self.virgula_decimal),
            ("valores negativos (descartados)", self.negativos),
            (f"valores acima de {LIMITE_MM_DIA:g} mm (descartados)", self.acima_do_limite),
            ("duplicatas exatas (removidas)", self.duplicatas_exatas),
            ("duplicatas conflitantes (1ª mantida)", self.duplicatas_conflitantes),
            ("registros finais", self.registros_finais),
        ]
        largura = max(len(nome) for nome, _ in itens)
        return "\n".join(f"{nome:<{largura}}  {valor:>5}" for nome, valor in itens)


def interpretar_valor(texto: str) -> tuple[float | None, str]:
    """Converte o texto de uma célula em (valor, motivo).

    O motivo diz o que aconteceu: 'ok', 'vazio', 'codigo', 'virgula', 'negativo' ou 'acima_limite'.
    Texto que não é número levanta ValueError: melhor parar e olhar do que adivinhar.

    >>> interpretar_valor("12.4")
    (12.4, 'ok')
    >>> interpretar_valor("12,4")
    (12.4, 'virgula')
    >>> interpretar_valor("  7 ")
    (7.0, 'ok')
    >>> interpretar_valor("-999")
    (None, 'codigo')
    >>> interpretar_valor("")
    (None, 'vazio')
    >>> interpretar_valor("-3.2")
    (None, 'negativo')
    >>> interpretar_valor("412.0")
    (None, 'acima_limite')
    >>> interpretar_valor("1.234,5")
    Traceback (most recent call last):
        ...
    ValueError: formato numérico ambíguo: '1.234,5'
    """
    t = texto.strip()
    if t == "":
        return None, "vazio"
    if t in CODIGOS_AUSENTE:
        return None, "codigo"
    motivo = "ok"
    if "," in t:
        if "." in t:
            raise ValueError(f"formato numérico ambíguo: {texto!r}")
        t = t.replace(",", ".")
        motivo = "virgula"
    negativo = t.startswith("-")
    corpo = t[1:] if negativo else t
    if not _NUMERO.fullmatch(corpo):
        raise ValueError(f"não é um número: {texto!r}")
    valor = float(corpo)
    if negativo and valor != 0:
        return None, "negativo"
    if valor > LIMITE_MM_DIA:
        return None, "acima_limite"
    return valor, motivo


def ler_chuva(caminho: str | Path) -> tuple[list[Registro], Relatorio]:
    """Lê o CSV (colunas estacao, data, chuva_mm), aplica as regras e devolve (registros, relatório).

    Regra de decisão para chaves repetidas (mesma estação e data): vale a PRIMEIRA linha.
    Se a segunda linha diz outra coisa, isso conta como 'duplicata conflitante' no relatório.
    """
    rel = Relatorio()
    vistos: dict[tuple[str, date], Registro] = {}
    caminho = Path(caminho)
    with open(caminho, newline="", encoding="utf-8") as f:
        leitor = csv.DictReader(f)
        faltam = {"estacao", "data", "chuva_mm"} - set(leitor.fieldnames or [])
        if faltam:
            raise ValueError(f"{caminho.name}: faltam as colunas {sorted(faltam)}")
        for numero, linha in enumerate(leitor, start=2):  # a linha 1 é o cabeçalho
            rel.linhas_lidas += 1
            try:
                dia = date.fromisoformat(linha["data"].strip())
                valor, motivo = interpretar_valor(linha["chuva_mm"])
            except ValueError as erro:
                raise ValueError(f"{caminho.name}, linha {numero}: {erro}") from None
            if motivo == "codigo":
                rel.ausentes_codigo += 1
            elif motivo == "vazio":
                rel.ausentes_vazio += 1
            elif motivo == "virgula":
                rel.virgula_decimal += 1
            elif motivo == "negativo":
                rel.negativos += 1
            elif motivo == "acima_limite":
                rel.acima_do_limite += 1
            reg = Registro(linha["estacao"].strip(), dia, valor)
            chave = (reg.estacao, reg.data)
            if chave in vistos:
                if vistos[chave].chuva_mm == reg.chuva_mm:
                    rel.duplicatas_exatas += 1
                else:
                    rel.duplicatas_conflitantes += 1
                continue
            vistos[chave] = reg
    registros = sorted(vistos.values(), key=lambda r: (r.estacao, r.data))
    rel.registros_finais = len(registros)
    return registros, rel


def datas_ausentes(registros: list[Registro], estacao: str, inicio: date | None = None, fim: date | None = None) -> list[date]:
    """Dias sem LINHA nenhuma para a estação, entre `inicio` e `fim`.

    Sem `inicio`/`fim`, usa a primeira e a última data da própria estação (e então não vê buracos nas pontas).
    Não confundir com registro de valor None: ali a linha existe, mas sem medida.

    >>> r = [Registro("A", date(2024, 1, 1), 0.0), Registro("A", date(2024, 1, 4), 2.0)]
    >>> datas_ausentes(r, "A")
    [datetime.date(2024, 1, 2), datetime.date(2024, 1, 3)]
    """
    presentes = {r.data for r in registros if r.estacao == estacao}
    if not presentes:
        return []
    inicio = inicio or min(presentes)
    fim = fim or max(presentes)
    faltando = []
    d = inicio
    while d <= fim:
        if d not in presentes:
            faltando.append(d)
        d += timedelta(days=1)
    return faltando
