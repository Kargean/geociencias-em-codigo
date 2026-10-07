"""Interface de linha de comando: python -m chuva <comando> ...

Comandos:
    qualidade   lê o CSV e mostra o relatório de qualidade e os dias sem linha
    resumo      índices por estação (CDD, Rx5day, dias de chuva por ano)
    banco       cria um banco SQLite com os dados limpos
    sql         roda uma consulta da pasta sql/consultas

A função main recebe a lista de argumentos e devolve o código de saída. Assim os testes a chamam
direto, sem abrir outro processo.
"""
from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path

from . import banco, qualidade, resumo
from .banco import RAIZ

CSV_CHUVA = RAIZ / "dados" / "chuva_diaria.csv"
CSV_ESTACOES = RAIZ / "dados" / "estacoes.csv"


def formatar_tabela(colunas: list[str], linhas: list[tuple]) -> str:
    """Tabela de texto com colunas alinhadas."""
    texto = [[("" if v is None else str(v)) for v in linha] for linha in linhas]
    larguras = [max(len(c), *(len(l[i]) for l in texto)) if texto else len(c) for i, c in enumerate(colunas)]
    cab = "  ".join(c.ljust(w) for c, w in zip(colunas, larguras))
    sep = "  ".join("-" * w for w in larguras)
    corpo = ["  ".join(v.ljust(w) for v, w in zip(l, larguras)) for l in texto]
    return "\n".join(linha.rstrip() for linha in [cab, sep, *corpo])


def _cmd_qualidade(args) -> int:
    registros, rel = qualidade.ler_chuva(args.csv)
    print(rel.texto())
    print()
    for est in resumo.estacoes_em(registros):
        faltam = qualidade.datas_ausentes(registros, est)
        print(f"{est}: {len(faltam)} dia(s) sem linha" + (f" ({', '.join(d.isoformat() for d in faltam)})" if faltam else ""))
    return 0


def _cmd_resumo(args) -> int:
    registros, _ = qualidade.ler_chuva(args.csv)
    estacoes = [args.estacao] if args.estacao else resumo.estacoes_em(registros)
    if args.estacao and args.estacao not in resumo.estacoes_em(registros):
        print(f"estação desconhecida: {args.estacao}", file=sys.stderr)
        return 2
    dias = resumo.dias_de_chuva(registros)
    linhas = []
    for est in estacoes:
        s = resumo.serie(registros, est)
        cdd, inicio = resumo.maior_periodo_seco(s)
        rx5, fim = resumo.maximo_acumulado(s)
        anos = {ano: n for (e, ano), n in dias.items() if e == est}
        linhas.append((est, cdd, inicio, rx5, fim, " ".join(f"{a}:{n}" for a, n in sorted(anos.items()))))
    print(formatar_tabela(["estacao", "CDD", "inicio", "Rx5day_mm", "fim", "dias_de_chuva"], linhas))
    return 0


def _cmd_banco(args) -> int:
    registros, _ = qualidade.ler_chuva(args.csv)
    saida = Path(args.saida)
    if saida.exists():
        print(f"{saida} já existe; apague ou escolha outro nome.", file=sys.stderr)
        return 2
    con = banco.construir_banco(args.estacoes, registros, saida)
    try:
        n = con.execute("SELECT COUNT(*) FROM chuva_diaria").fetchone()[0]
    finally:
        con.close()  # no Windows, um arquivo de banco aberto não pode ser apagado nem movido
    print(f"banco criado em {saida} com {n} registros")
    return 0


def _cmd_sql(args) -> int:
    if not banco.versao_sqlite_suficiente():
        print(f"SQLite {sqlite3.sqlite_version} é antigo; as janelas precisam de 3.28 ou mais.", file=sys.stderr)
        return 2
    if args.banco:
        con = banco.conectar(args.banco)
    else:
        registros, _ = qualidade.ler_chuva(args.csv)
        con = banco.construir_banco(CSV_ESTACOES, registros)
    try:
        linhas = banco.executar_consulta(con, args.consulta, limiar=args.limiar)
    except FileNotFoundError as erro:
        print(erro, file=sys.stderr)
        return 2
    finally:
        con.close()  # em todos os caminhos, inclusive o de erro (veja test_cli.py)
    if not linhas:
        print("(sem linhas)")
        return 0
    print(formatar_tabela(list(linhas[0].keys()), [tuple(l) for l in linhas]))
    return 0


def construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m chuva", description="Chuva diária em estações (dados sintéticos).")
    sub = p.add_subparsers(dest="comando", required=True)

    q = sub.add_parser("qualidade", help="relatório de qualidade do CSV")
    q.add_argument("csv", nargs="?", default=CSV_CHUVA, type=Path)
    q.set_defaults(funcao=_cmd_qualidade)

    r = sub.add_parser("resumo", help="CDD, Rx5day e dias de chuva por estação")
    r.add_argument("csv", nargs="?", default=CSV_CHUVA, type=Path)
    r.add_argument("--estacao", help="limita a uma estação (ex.: E01)")
    r.set_defaults(funcao=_cmd_resumo)

    b = sub.add_parser("banco", help="cria um banco SQLite com os dados limpos")
    b.add_argument("--csv", default=CSV_CHUVA, type=Path)
    b.add_argument("--estacoes", default=CSV_ESTACOES, type=Path)
    b.add_argument("--saida", default="chuva.db")
    b.set_defaults(funcao=_cmd_banco)

    s = sub.add_parser("sql", help="roda uma consulta de sql/consultas")
    s.add_argument("consulta", help="nome sem extensão, ex.: 05_maior_periodo_seco")
    s.add_argument("--banco", help="arquivo .db criado pelo comando banco (padrão: banco temporário em memória)")
    s.add_argument("--csv", default=CSV_CHUVA, type=Path)
    s.add_argument("--limiar", type=float, default=resumo.LIMIAR_DIA_CHUVOSO_MM, help="mm que separa dia seco de chuvoso")
    s.set_defaults(funcao=_cmd_sql)
    return p


def main(argv: list[str] | None = None) -> int:
    args = construir_parser().parse_args(argv)
    try:
        return args.funcao(args)
    except (ValueError, FileNotFoundError, sqlite3.Error) as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
