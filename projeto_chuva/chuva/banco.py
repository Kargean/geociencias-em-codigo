"""SQLite: criar o esquema, carregar os dados e rodar as consultas da pasta sql/.

Duas regras de ouro para falar com um banco a partir do Python:
  1. NUNCA monte SQL juntando texto (f"... '{nome}'"). Use parâmetros (? ou :nome). Isso evita erro
     de aspas e o ataque conhecido como injeção de SQL.
  2. Mude dados dentro de uma transação: ou tudo entra, ou nada entra.
"""
from __future__ import annotations

import csv
import sqlite3
from pathlib import Path

from .qualidade import Registro

RAIZ = Path(__file__).resolve().parent.parent
PASTA_SQL = RAIZ / "sql"
PASTA_CONSULTAS = PASTA_SQL / "consultas"

# Janelas com RANGE e deslocamento só existem a partir do SQLite 3.28 (abril de 2019).
VERSAO_MINIMA_SQLITE = (3, 28, 0)


def versao_sqlite_suficiente() -> bool:
    return sqlite3.sqlite_version_info >= VERSAO_MINIMA_SQLITE


def conectar(caminho: str | Path = ":memory:") -> sqlite3.Connection:
    """Abre (ou cria) o banco. ':memory:' cria um banco temporário, que some ao fechar."""
    con = sqlite3.connect(str(caminho))
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")  # desligado por padrão em cada conexão nova!
    return con


def criar_esquema(con: sqlite3.Connection) -> None:
    con.executescript((PASTA_SQL / "esquema.sql").read_text(encoding="utf-8"))


def carregar_estacoes(con: sqlite3.Connection, caminho_csv: str | Path) -> int:
    with open(caminho_csv, newline="", encoding="utf-8") as f:
        linhas = [
            (r["id"], r["nome"], float(r["lat"]), float(r["lon"]), float(r["altitude_m"]), r["bacia"])
            for r in csv.DictReader(f)
        ]
    with con:  # 'with con' = uma transação: confirma ao sair, desfaz se der erro
        con.executemany(
            "INSERT INTO estacao (id, nome, lat, lon, altitude_m, bacia) VALUES (?, ?, ?, ?, ?, ?)", linhas
        )
    return len(linhas)


def carregar_chuva(con: sqlite3.Connection, registros: list[Registro]) -> int:
    """Insere os registros já limpos (None vira NULL). Falha inteira se a chave se repetir."""
    linhas = [(r.estacao, r.data.isoformat(), r.chuva_mm) for r in registros]
    with con:
        con.executemany("INSERT INTO chuva_diaria (estacao_id, data, chuva_mm) VALUES (?, ?, ?)", linhas)
    return len(linhas)


def listar_consultas() -> list[str]:
    return sorted(p.stem for p in PASTA_CONSULTAS.glob("*.sql"))


def executar_consulta(con: sqlite3.Connection, nome: str, **parametros) -> list[sqlite3.Row]:
    """Roda sql/consultas/<nome>.sql. Parâmetros nomeados (:limiar) vêm de `parametros`.

    Parâmetros que a consulta não usa são ignorados; os que ela pede e faltam geram erro.
    """
    arquivo = PASTA_CONSULTAS / f"{nome}.sql"
    if not arquivo.is_file():
        raise FileNotFoundError(f"consulta não encontrada: {nome} (disponíveis: {', '.join(listar_consultas())})")
    return con.execute(arquivo.read_text(encoding="utf-8"), parametros).fetchall()


def construir_banco(caminho_estacoes: str | Path, registros: list[Registro], caminho_banco: str | Path = ":memory:") -> sqlite3.Connection:
    """Atalho: conecta, cria o esquema e carrega estações e chuva."""
    con = conectar(caminho_banco)
    criar_esquema(con)
    carregar_estacoes(con, caminho_estacoes)
    carregar_chuva(con, registros)
    return con
