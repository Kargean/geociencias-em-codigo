"""Gerador de dados SINTÉTICOS de chuva diária, com defeitos plantados.

Por que sintético? Porque então a verdade é conhecida: sabemos quais dias estão ausentes, quais linhas
estão duplicadas e qual era o valor correto. Assim dá para medir se a limpeza funciona (ver tests/).

As quatro estações são FICTÍCIAS. Os números não representam nenhum local real.

Só usa a biblioteca padrão. Dos sorteios, só `random.Random.random()` é usado, porque é o único cuja
sequência o Python garante entre versões; o resto (exponencial) é calculado à mão.
"""
from __future__ import annotations

import csv
import math
import random
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

SEMENTE = 2024
INICIO = date(2024, 1, 1)
FIM = date(2025, 12, 31)

# id, nome, latitude, longitude, altitude (m), bacia, fator de chuva (oculto: não vai para o CSV)
ESTACOES = [
    ("E01", "Planície", -21.75, -41.30, 12.0, "Bacia Alfa", 1.00),
    ("E02", "Colina", -21.70, -41.40, 85.0, "Bacia Alfa", 1.10),
    ("E03", "Serra", -21.60, -41.80, 640.0, "Bacia Beta", 1.50),
    ("E04", "Litoral", -21.85, -41.05, 3.0, "Bacia Beta", 0.90),
]

CABECALHO_ESTACOES = ["id", "nome", "lat", "lon", "altitude_m", "bacia"]
CABECALHO_CHUVA = ["estacao", "data", "chuva_mm"]


@dataclass
class Sintetico:
    """Resultado da geração.

    verdade   (estação, data) -> chuva correta em mm, para TODOS os dias do período
    linhas    o que vai para o CSV "sujo": lista de (estação, data ISO, texto da célula)
    defeitos  tipo de defeito -> lista de (estação, data) onde foi plantado
    """

    verdade: dict[tuple[str, date], float]
    linhas: list[tuple[str, str, str]]
    defeitos: dict[str, list[tuple[str, date]]]


def _sazonal(d: date) -> float:
    """1 no verão (pico em 5 de janeiro) e 0 no inverno (início de julho)."""
    dia_do_ano = d.timetuple().tm_yday
    return 0.5 + 0.5 * math.cos(2 * math.pi * (dia_do_ano - 5) / 365.25)


def gerar_verdade(semente: int = SEMENTE) -> dict[tuple[str, date], float]:
    """Chuva diária correta, com estação chuvosa no verão.

    Cada dia: um sorteio regional (compartilhado, 70% das vezes) e um local decidem se chove;
    se chove, o volume segue uma exponencial cuja média cresce no verão e com o fator da estação.
    """
    rng = random.Random(semente)
    verdade: dict[tuple[str, date], float] = {}
    d = INICIO
    while d <= FIM:
        s = _sazonal(d)
        p_chuva = 0.15 + 0.35 * s
        media_mm = 4.0 + 10.0 * s
        u_regional = rng.random()
        for est_id, *_, fator in ESTACOES:
            mistura, u_local, v = rng.random(), rng.random(), rng.random()
            u = u_regional if mistura < 0.7 else u_local
            if u < p_chuva:
                verdade[(est_id, d)] = round(-media_mm * fator * math.log(1.0 - v), 1)
            else:
                verdade[(est_id, d)] = 0.0
        d += timedelta(days=1)
    return verdade


def _dias_molhados(verdade, est_id: str, a_partir_de: date, quantos: int, minimo: float = 5.0) -> list[date]:
    """Os `quantos` primeiros dias da estação, a partir de uma data, com chuva >= minimo (mm)."""
    achados: list[date] = []
    d = a_partir_de
    while len(achados) < quantos and d <= FIM:
        if verdade[(est_id, d)] >= minimo:
            achados.append(d)
        d += timedelta(days=1)
    return achados


def _intervalo(est_id: str, inicio: date, n: int) -> list[tuple[str, date]]:
    return [(est_id, inicio + timedelta(days=i)) for i in range(n)]


def gerar(semente: int = SEMENTE) -> Sintetico:
    """Gera a verdade e planta os defeitos, sempre nas mesmas posições (para os testes saberem onde estão)."""
    verdade = gerar_verdade(semente)

    defeitos: dict[str, list[tuple[str, date]]] = {
        # instrumento parado: o fornecedor escreveu -999 (E01) ou -999.0 (E02)
        "ausente_codigo": _intervalo("E01", date(2024, 3, 10), 5) + [("E02", date(2025, 7, 1))],
        # outro fornecedor deixa a célula em branco (E03)
        "ausente_vazio": _intervalo("E03", date(2024, 11, 20), 3),
        # a linha nem existe no arquivo
        "linha_ausente": _intervalo("E04", date(2024, 8, 15), 3) + [("E01", date(2025, 2, 10))],
        # vírgula decimal (padrão brasileiro) em um arquivo que usa ponto
        "virgula": [("E02", d) for d in _dias_molhados(verdade, "E02", date(2024, 12, 1), 2)]
        + [("E03", _dias_molhados(verdade, "E03", date(2025, 1, 10), 1)[0])],
        # a mesma linha repetida
        "duplicata_exata": [("E01", date(2024, 6, 1)), ("E04", date(2025, 3, 3))],
        # a mesma chave com valores diferentes
        "duplicata_conflitante": [("E02", _dias_molhados(verdade, "E02", date(2024, 10, 10), 1)[0])],
        # valor impossível (chuva negativa)
        "negativo": [("E03", date(2025, 5, 5))],
        # valor absurdo (412 mm em um dia): erro de digitação
        "acima_do_limite": [("E01", date(2025, 1, 20))],
    }

    texto: dict[tuple[str, date], str] = {k: f"{v:.1f}" for k, v in verdade.items()}
    for chave in defeitos["ausente_codigo"]:
        texto[chave] = "-999.0" if chave[0] == "E01" else "-999"
    for chave in defeitos["ausente_vazio"]:
        texto[chave] = ""
    for chave in defeitos["virgula"]:
        texto[chave] = texto[chave].replace(".", ",")
    texto[defeitos["negativo"][0]] = "-3.2"
    texto[defeitos["acima_do_limite"][0]] = "412.0"
    ausentes = set(defeitos["linha_ausente"])

    linhas: list[tuple[str, str, str]] = []
    for est_id, *_ in ESTACOES:
        d = INICIO
        while d <= FIM:
            chave = (est_id, d)
            if chave not in ausentes:
                linha = (est_id, d.isoformat(), texto[chave])
                linhas.append(linha)
                if chave in defeitos["duplicata_exata"]:
                    linhas.append(linha)
                if chave in defeitos["duplicata_conflitante"]:
                    linhas.append((est_id, d.isoformat(), "0.0"))
            d += timedelta(days=1)
    return Sintetico(verdade=verdade, linhas=linhas, defeitos=defeitos)


def escrever(pasta: str | Path, semente: int = SEMENTE) -> Sintetico:
    """Escreve dados/estacoes.csv e dados/chuva_diaria.csv (terminações de linha LF, UTF-8)."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    s = gerar(semente)
    with open(pasta / "estacoes.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(CABECALHO_ESTACOES)
        for est_id, nome, lat, lon, alt, bacia, _ in ESTACOES:
            w.writerow([est_id, nome, lat, lon, alt, bacia])
    with open(pasta / "chuva_diaria.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(CABECALHO_CHUVA)
        w.writerows(s.linhas)
    return s
