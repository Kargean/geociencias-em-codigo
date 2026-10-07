"""Cálculos em Python puro sobre a chuva diária.

Os nomes seguem os índices climáticos do ETCCDI (CDD, Rx5day, número de dias com chuva >= nn mm).
Cada função aqui tem uma irmã em SQL (pasta sql/consultas/) e os testes exigem que as duas concordem.
"""
from __future__ import annotations

import calendar
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta

from .qualidade import Registro

LIMIAR_DIA_CHUVOSO_MM = 1.0  # um dia "com chuva" tem >= 1 mm; um dia "seco" tem < 1 mm (convenção do ETCCDI)


@dataclass(frozen=True)
class Mensal:
    """Resumo de um mês numa estação."""

    total_mm: float | None  # soma dos dias válidos (None se não houve nenhum dia válido)
    n_validos: int
    n_registrados: int
    dias_no_mes: int

    @property
    def completo(self) -> bool:
        return self.n_validos == self.dias_no_mes


def serie(registros: list[Registro], estacao: str) -> dict[date, float | None]:
    """A série de uma estação como dicionário data -> mm (ou None)."""
    return {r.data: r.chuva_mm for r in registros if r.estacao == estacao}


def estacoes_em(registros: list[Registro]) -> list[str]:
    return sorted({r.estacao for r in registros})


def total_mensal(registros: list[Registro]) -> dict[tuple[str, str], Mensal]:
    """Total de chuva por estação e mês, indicando se o mês está completo.

    A chave é (estação, 'AAAA-MM'). Dias sem medida (None) NÃO entram na soma; por isso o total de um mês
    incompleto é um piso, não o valor verdadeiro. O campo `completo` avisa.

    >>> regs = [Registro("A", date(2024, 2, 1), 10.0), Registro("A", date(2024, 2, 2), None)]
    >>> m = total_mensal(regs)[("A", "2024-02")]
    >>> (m.total_mm, m.n_validos, m.n_registrados, m.dias_no_mes, m.completo)
    (10.0, 1, 2, 29, False)
    """
    soma: dict[tuple[str, str], float] = defaultdict(float)
    validos: dict[tuple[str, str], int] = defaultdict(int)
    registrados: dict[tuple[str, str], int] = defaultdict(int)
    for r in registros:
        chave = (r.estacao, f"{r.data:%Y-%m}")
        registrados[chave] += 1
        if r.chuva_mm is not None:
            soma[chave] += r.chuva_mm
            validos[chave] += 1
    resultado = {}
    for chave, n_reg in registrados.items():
        ano, mes = int(chave[1][:4]), int(chave[1][5:])
        total = round(soma[chave], 1) if validos[chave] > 0 else None
        resultado[chave] = Mensal(total, validos[chave], n_reg, calendar.monthrange(ano, mes)[1])
    return dict(sorted(resultado.items()))


def dias_de_chuva(registros: list[Registro], limiar: float = LIMIAR_DIA_CHUVOSO_MM) -> dict[tuple[str, str], int]:
    """Número de dias com chuva >= limiar, por (estação, 'AAAA'). Dias sem medida não contam.

    >>> regs = [Registro("A", date(2024, 1, 1), 0.9), Registro("A", date(2024, 1, 2), 1.0), Registro("A", date(2024, 1, 3), None)]
    >>> dias_de_chuva(regs)
    {('A', '2024'): 1}
    """
    contagem: dict[tuple[str, str], int] = defaultdict(int)
    for r in registros:
        chave = (r.estacao, f"{r.data:%Y}")
        contagem[chave] += 0  # garante a chave, mesmo com zero dias de chuva
        if r.chuva_mm is not None and r.chuva_mm >= limiar:
            contagem[chave] += 1
    return dict(sorted(contagem.items()))


def maior_periodo_seco(s: dict[date, float | None], limiar: float = LIMIAR_DIA_CHUVOSO_MM) -> tuple[int, date | None]:
    """CDD: o maior número de dias CONSECUTIVOS com chuva < limiar, e a data em que começou.

    Um dia sem medida (None) ou sem linha interrompe o período: não sabemos se foi seco.
    Em caso de empate, vale o período que começou primeiro.

    >>> d = date(2024, 1, 1)
    >>> s = {d: 0.0, d + timedelta(1): 0.2, d + timedelta(2): 5.0, d + timedelta(3): 0.0}
    >>> maior_periodo_seco(s)
    (2, datetime.date(2024, 1, 1))
    >>> s[d + timedelta(1)] = None   # um dia sem medida quebra o período
    >>> maior_periodo_seco(s)
    (1, datetime.date(2024, 1, 1))
    """
    melhor, melhor_inicio = 0, None
    atual, inicio, anterior = 0, None, None
    for d in sorted(s):
        v = s[d]
        seco = v is not None and v < limiar
        if not seco:
            atual = 0
        elif atual > 0 and anterior is not None and (d - anterior).days == 1:
            atual += 1
        else:
            atual, inicio = 1, d
        if atual > melhor:
            melhor, melhor_inicio = atual, inicio
        anterior = d
    return melhor, melhor_inicio


def maximo_acumulado(s: dict[date, float | None], janela: int = 5) -> tuple[float | None, date | None]:
    """Rx5day (para janela=5): maior chuva acumulada em `janela` dias consecutivos, e o dia em que a janela termina.

    Só vale janela COMPLETA: todos os dias da janela precisam ter medida válida.
    Em caso de empate, vale a janela que terminou primeiro.

    >>> d = date(2024, 1, 1)
    >>> s = {d + timedelta(i): v for i, v in enumerate([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])}
    >>> maximo_acumulado(s, janela=3)
    (15.0, datetime.date(2024, 1, 6))
    """
    melhor, melhor_fim = None, None
    for fim in sorted(s):
        dias = [fim - timedelta(days=k) for k in range(janela)]
        valores = [s.get(x) for x in dias]
        if any(v is None for v in valores):
            continue
        total = round(sum(valores), 1)
        if melhor is None or total > melhor:
            melhor, melhor_fim = total, fim
    return melhor, melhor_fim
