"""Testes dos capítulos P1-06 (SQL essencial I) e P1-07 (SQL essencial II): o código executa e os números citados no texto conferem.

Execute:  python tests/test_modulo_p1.py        (leva poucos segundos; precisa de matplotlib, PyYAML e, para o P1-07, pandas)

O que este arquivo garante, para cada capítulo:
  1. todos os blocos de código do capítulo (e os gabaritos dos exercícios) executam em ordem, sem avisos de descontinuação;
  2. os números que o texto cita são os que o código calcula;
  3. as respostas do SQL batem com cálculos independentes em Python (e, no P1-07, com o pandas);
  4. o registro do PostgreSQL tem uma entrada para cada sonda de dialeto (o registro em si NÃO é reexecutado aqui);
  5. a estrutura do capítulo (seções, gabaritos recolhíveis, rótulos) e a ordem no _quarto.yml estão corretas.

O que ele NÃO garante: que o Quarto renderiza os capítulos, que o código roda no Windows ou em outras versões do SQLite,
nem que o registro do PostgreSQL continua valendo em outras versões.
"""
import contextlib
import io
import math
import re
import sqlite3
import sys
import tempfile
import unittest
import warnings
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
from executar_codigo_qmd import executar  # noqa: E402

CAPITULO = "p1-06-sql-essencial-i.qmd"
CAPITULO_107 = "p1-07-sql-essencial-ii.qmd"


def ler(caminho):
    return (RAIZ / caminho).read_text(encoding="utf-8")


def executar_celula(caminho, rotulo):
    """Executa só a célula de código com o rótulo dado (útil para pegar os dados de outro capítulo) e devolve o espaço de nomes."""
    m = re.search(r"#\| label: " + re.escape(rotulo) + r"\n(.*?)^```", ler(caminho), re.S | re.M)
    assert m, f"célula {rotulo} não encontrada em {caminho}"
    ns = {}
    exec(m.group(1), ns)
    return ns


class CapituloP106(unittest.TestCase):
    """Executa o capítulo uma vez e guarda o espaço de nomes e a saída."""

    @classmethod
    def setUpClass(cls):
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
                with warnings.catch_warnings():
                    # um aviso de descontinuação hoje vira erro numa versão futura do Python (foi o caso de `?1` no 3.12)
                    warnings.simplefilter("error", DeprecationWarning)
                    cls.ns = executar(RAIZ / CAPITULO, tempfile.mkdtemp(), incluir_gabaritos=True, verbose=False)
        except SystemExit:
            raise AssertionError(f"{CAPITULO}: um bloco de código falhou.\n{buffer.getvalue()[-3000:]}")
        cls.saida = buffer.getvalue()
        cls.texto = ler(CAPITULO)

    # -- os dados e a tabela ----------------------------------------------------------------------------------
    def test_dados_e_tabela(self):
        ns = self.ns
        self.assertEqual(len(ns["AMOSTRAS"]), 20)                                  # "20 amostras sintéticas"
        self.assertEqual(sum(1 for a in ns["AMOSTRAS"] if a[3] is None), 1)        # "uma amostra sem resultado"
        self.assertEqual((ns["total"], ns["com_valor"]), (20, 19))                  # "20 contra 19"
        self.assertEqual(
            (ns["OD_MINIMO_MG_L"], ns["PH_MINIMO"], ns["PH_MAXIMO"], ns["TURBIDEZ_MAXIMA_UNT"]),
            (5.0, 6.0, 9.0, 100.0),                                                   # CONAMA 357/2005, classe 2
        )
        self.assertEqual({a[0] for a in ns["AMOSTRAS"]}, {"P01", "P02", "P03"})
        self.assertEqual({a[2] for a in ns["AMOSTRAS"]}, {"OD", "pH", "turbidez"})
        self.assertEqual(sorted({a[1] for a in ns["AMOSTRAS"]}), ["2024-02-20", "2024-05-14", "2024-08-13"])

    def test_datas_iso_ordenam_e_o_formato_brasileiro_nao(self):
        ns = self.ns
        self.assertEqual(sorted(ns["iso"]), ["2024-02-20", "2024-05-14", "2024-08-13"])
        self.assertEqual(sorted(ns["brasileiro"]), ["13/08/2024", "14/05/2024", "20/02/2024"])   # agosto antes de maio
        self.assertIn("date() e o brasileiro: None", self.saida)                                    # date('20/02/2024') -> NULL

    def test_afinidade_de_tipos(self):
        ns = self.ns
        self.assertTrue(all(ns["regra_confere"].values()))
        self.assertEqual(len(ns["regra_confere"]), 16)
        self.assertEqual(ns["afinidade"]("POINT"), "INTEGER")           # "POINT contém INT"
        self.assertEqual(ns["afinidade"]("DATE"), "NUMERIC")            # "o SQLite não tem tipo de data"
        self.assertEqual(ns["afinidade"]("BOOLEAN"), "NUMERIC")
        self.assertEqual(ns["afinidade"](""), "BLOB")
        self.assertEqual(ns["decimal_guardado"], 12.345)                # "DECIMAL(5,2) guardou 12,345"

    def test_guarda_de_tipos(self):
        r = self.ns["resultados_guarda"]
        self.assertEqual(r[("solta", "abc")], "ENTROU")
        self.assertEqual(r[("solta", "12.4")], "ENTROU")
        self.assertTrue(r[("guardada", "abc")].startswith("RECUSADO"))
        self.assertEqual(r[("guardada", "12.4")], "ENTROU")
        if self.ns["tem_strict"]:
            self.assertTrue(r[("estrita", "abc")].startswith("RECUSADO"))
            self.assertEqual(r[("estrita", "12.4")], "ENTROU")
        else:
            self.assertNotIn(("estrita", "abc"), r)

    # -- SELECT --------------------------------------------------------------------------------------------------
    def test_select_numeros_citados(self):
        ns = self.ns
        self.assertEqual(len(ns["sem_parenteses"]), 3)       # "3 linhas" sem parênteses
        self.assertEqual(len(ns["com_parenteses"]), 2)       # "só 2 linhas passam"
        self.assertIn(("P02", "2024-02-20", 135.0), [(r[1], r[2], r[4]) for r in ns["sem_parenteses"]])   # a turbidez intrusa
        self.assertEqual(len(ns["em_p01_p03"]), 4)
        self.assertEqual(ns["extremos"], [(1, 1, 0)])        # BETWEEN inclui os extremos
        self.assertEqual(ns["com_like"], [(6,)])             # LIKE 'TUR%' acha 'turbidez'
        self.assertEqual([r[2] for r in ns["tres_menores"]], [3.9, 4.8, 6.1])
        self.assertEqual([r[2] for r in ns["tres_seguintes"]], [6.5, 7.1, 7.5])
        self.assertEqual(len(ns["por_ponto_data"]), 7)
        self.assertEqual(ns["parametros"], [("OD",), ("pH",), ("turbidez",)])
        self.assertEqual(len(ns["combinacoes"]), 7)          # "7 combinações de data e ponto"
        # "E se?" (sem resposta no texto): com NOT IN ('P01', 'P03') sobram as 3 linhas de OD de P02 (o banco já está fechado)
        sobram = [a for a in ns["AMOSTRAS"] if a[2] == "OD" and a[0] not in ("P01", "P03")]
        self.assertEqual(len(sobram), 3)

    # -- NULL e lógica de três valores ----------------------------------------------------------------------------
    def test_logica_de_tres_valores(self):
        ns = self.ns
        self.assertEqual(ns["divergencias"], [])
        self.assertEqual(ns["combinacoes_conferidas"], 21)   # 9 de AND + 9 de OR + 3 de NOT
        e3, ou3, nao3 = ns["e3"], ns["ou3"], ns["nao3"]
        self.assertEqual(e3(0, None), 0)                     # F E ? = F
        self.assertEqual(ou3(1, None), 1)                    # V OU ? = V
        self.assertIsNone(e3(1, None))                       # V E ? = ?
        self.assertIsNone(ou3(0, None))                      # F OU ? = ?
        self.assertIsNone(nao3(None))
        self.assertEqual((nao3(1), nao3(0)), (0, 1))

    def test_null_numeros_citados(self):
        ns = self.ns
        self.assertEqual(ns["igual_null"], [])                                            # "= NULL devolve zero linhas"
        self.assertEqual(ns["e_nulo"], [(18, "P02", "2024-08-13", "turbidez")])
        self.assertEqual((ns["acima"], ns["dentro"], ns["todas_de_turbidez"]), (1, 4, 6))  # 1 + 4 = 5, não 6
        self.assertEqual(ns["nao_acima"], 4)                                               # NOT (valor > 100) também perde o NULL
        self.assertEqual((ns["diferente"], ns["is_not"]), (4, 5))                          # <> perde o NULL, IS NOT não
        self.assertIsNone(ns["turbidez_asc"][0][2])                                        # ASC: NULL primeiro
        self.assertIsNone(ns["turbidez_desc"][-1][2])                                      # DESC: NULL por último
        self.assertEqual(ns["check_com_igual"], "ENTROU")                                  # CHECK aceita o desconhecido...
        self.assertTrue(ns["check_com_is"].startswith("RECUSADO"))                         # ...e o IS o transforma em falso
        self.assertEqual(ns["media_correta"], 46.8)                                        # 234 / 5
        self.assertEqual(ns["media_com_zero"], 39.0)                                       # 234 / 6
        self.assertEqual(sum(ns["medidos"]), 234.0)
        subestima = 1 - ns["media_com_zero"] / ns["media_correta"]
        self.assertTrue(0.16 < subestima < 0.18, subestima)                                # "cerca de 17%"

    # -- funções escalares ------------------------------------------------------------------------------------------
    def test_funcoes_numeros_citados(self):
        ns = self.ns
        self.assertEqual(ns["divisoes"], [(3, 3.5, 1, -3)])                                # 7/2 = 3; -7/2 = -3 no SQL
        self.assertEqual((-7 // 2, int(-7 / 2)), (-4, -3))                                 # o // do Python arredonda para baixo
        folgas = {(r[0], r[1]): r[3] for r in ns["folga"]}
        self.assertEqual(folgas[("P02", "2024-05-14")], -0.2)                              # "0,2 mg/L abaixo em maio"
        self.assertEqual(folgas[("P02", "2024-08-13")], -1.1)                              # "1,1 mg/L abaixo em agosto"
        self.assertEqual(ns["etiquetas"][0][1], "P02 · 135.0")
        self.assertIsNone(ns["etiquetas"][2][1])                                           # texto || NULL = NULL
        self.assertTrue(ns["datas_sql"] == ns["datas_py"])
        self.assertEqual([linha[4] for linha in ns["datas_sql"]], [0, 84, 175])            # "84 dias (12 semanas)", "175 dias (25 semanas)"
        self.assertEqual((84 // 7, 175 // 7, 84 % 7, 175 % 7), (12, 25, 0, 0))
        self.assertEqual([linha[2] for linha in ns["datas_sql"]], ["02", "05", "08"])      # strftime('%m') devolve TEXTO
        self.assertEqual(ns["tipos_guardados"], [("null",), ("real",)])
        self.assertEqual(ns["cast_exemplo"], [(12.4, 7)])                                  # CAST(7.9 AS INTEGER) corta

    # -- as cinco perguntas ----------------------------------------------------------------------------------------
    def test_pratica_conferencias(self):
        ns = self.ns
        esperadas = {"q1", "q2", "q3", "q3_menores", "q4", "q5"}
        if ns["sqlite3"].sqlite_version_info >= (3, 30, 0):             # NULLS LAST só existe a partir do SQLite 3.30.0
            esperadas.add("q3_nulls_last")
        self.assertEqual(set(ns["conferencias"]), esperadas)
        self.assertTrue(all(ns["conferencias"].values()), ns["conferencias"])
        self.assertEqual(ns["q1_sql"], [("P02", "2024-05-14", 4.8), ("P02", "2024-08-13", 3.9)])
        self.assertEqual(ns["q2_sql"], [("P02", "2024-08-13", 5.8)])                         # o 6,3 passa
        self.assertEqual([r[2] for r in ns["q3_sql"]], [135.0, 60.0, 18.0])
        self.assertIsNone(ns["q3_menores_ingenuo"][0][2])                                     # a armadilha do NULL no ASC
        self.assertEqual([r[2] for r in ns["q3_menores"]], [9.0, 12.0, 18.0])
        self.assertEqual(ns["contagem_q4"], {"acima do limite": 1, "dentro do limite": 4, "sem resultado": 1})
        self.assertEqual(sum(ns["contagem_q4"].values()), 6)
        self.assertEqual(ns["dentro_sem_ramo_nulo"], 5)                                       # o CASE sem o ramo do NULL erra por 1
        self.assertEqual([r[4] for r in ns["q5_sql"]], [2.8, 2.5, 2.1, 1.1, -0.2, -1.1, 1.5])
        self.assertEqual(ns["pontos_abaixo_no_grafico"], 2)
        self.assertEqual(len(ns["_figuras"]), 1)
        self.assertTrue(ns["_figuras"][0].is_file())

    # -- dialetos --------------------------------------------------------------------------------------------------
    def test_dialetos(self):
        ns = self.ns
        chaves = {c for c, _o_que, _sql in ns["SONDAS"]}
        self.assertEqual(set(ns["dialeto_sqlite"]), chaves)
        self.assertEqual(set(ns["POSTGRESQL_16_15"]), chaves)          # o registro cobre cada sonda
        sq = ns["dialeto_sqlite"]
        self.assertEqual((sq["div_inteira"], sq["div_real"]), ("3", "3.5"))
        self.assertEqual(sq["div_zero"], "NULL")                       # o SQLite devolve NULL; o PostgreSQL dá erro
        self.assertEqual((sq["cast_positivo"], sq["cast_negativo"]), ("7", "-7"))
        self.assertEqual(sq["like_caixa"], "verdadeiro")
        self.assertEqual(sq["null_igual"], "NULL")
        self.assertEqual((sq["ordem_asc"], sq["ordem_desc"]), ("NULL", "3.0"))
        self.assertEqual(sq["aspas_duplas"], "abc")
        self.assertEqual(sq["apelido_where"], "14.0")
        self.assertEqual(sq["mes_da_data"], "02")
        self.assertEqual(sq["dias_entre"], "84.0")
        self.assertEqual(sq["tipo_do_valor"], "integer")
        self.assertEqual(sq["data_impossivel"], "2024-03-01")          # o SQLite "corrige" a data impossível
        self.assertEqual(sq["round_flutuante"], "3.1")
        self.assertEqual(sq["abc_em_real"], "entrou")
        self.assertEqual(sq["id_automatico"], "id gerado: 1")
        pg = ns["POSTGRESQL_16_15"]                                    # REGISTRO: confere o que o texto afirma, não o servidor
        self.assertEqual((pg["cast_positivo"], pg["cast_negativo"]), ("8", "-8"))
        self.assertEqual((pg["ordem_asc"], pg["ordem_desc"]), ("1.0", "NULL"))
        self.assertEqual(pg["like_caixa"], "falso")
        for chave in ("div_zero", "aspas_duplas", "apelido_where", "mes_da_data", "tipo_do_valor", "data_impossivel", "round_flutuante", "id_automatico"):
            self.assertTrue(pg[chave].startswith("ERRO"), chave)
        self.assertTrue(pg["abc_em_real"].startswith("recusado"))

    # -- exercícios ------------------------------------------------------------------------------------------------
    def test_gabaritos_dos_exercicios(self):
        ns = self.ns
        self.assertEqual((ns["ex1_a"], ns["ex1_b"], ns["py_a"], ns["py_b"]), (8, 3, 8, 3))
        self.assertEqual(ns["ex3_sql"], [("P03", "2024-08-13", 7.4), ("P01", "2024-02-20", 7.2)])
        self.assertEqual((ns["ex4_sql"], ns["ex4_python"]), (["2", "2", "2"], [2, 2, 2]))
        self.assertEqual((ns["dias_ago_mai"], ns["dias_py"]), (91, 91))
        self.assertEqual(ns["previsao"], {"FLOATING POINT": "INTEGER", "CHARINT": "INTEGER", "DATETIME": "NUMERIC", "VARCHAR(10)": "TEXT"})
        ex6 = ns["ex6"]
        self.assertTrue(all(ex6[k].startswith("RECUSADO") for k in "abc"))
        self.assertEqual(ex6["d"], "ENTROU")
        self.assertEqual(ns["linhas_na_copia"], 21)                    # a cópia ganhou a linha (d); o banco do capítulo, não
        self.assertEqual(ns["contagem_desafio"], {"fora": 4, "conforme": 15, "sem resultado": 1})
        self.assertEqual(ns["desafio_sql"], ns["desafio_python"])
        fora = [i for i, situacao in ns["desafio_sql"] if situacao == "fora"]
        self.assertEqual(fora, [6, 10, 16, 17])                        # "os ids 6, 10, 16 e 17"
        self.assertEqual([i for i, situacao in ns["desafio_sql"] if situacao == "sem resultado"], [18])

    def test_o_banco_do_capitulo_foi_fechado_no_fim(self):
        with self.assertRaises(sqlite3.ProgrammingError):
            self.ns["banco"].execute("SELECT 1")

    # -- o texto cita o que o código calcula ---------------------------------------------------------------------------
    def test_o_texto_cita_os_numeros_certos(self):
        texto = self.texto
        for citacao in (
            "20 contra 19",              # COUNT(*) contra COUNT(valor)
            "46,8 UNT",                  # média correta
            "39,0",                      # média com zero
            "cerca de 17%",
            "84 dias (12 semanas)",
            "175 dias depois (25 semanas)",
            "91 dias",                   # exercício 4
            "As 21 combinações",
            "(1 + 4 + 1)",
            "1 + 4 = 5, não 6",
            "**4** amostras fora",
            "**15** conformes",
            "contando **5** amostras",   # o CASE ingênuo
            "versão 16.15",
        ):
            self.assertIn(citacao, texto, citacao)


class Estrutura(unittest.TestCase):
    def test_o_capitulo_tem_as_secoes_do_metodo(self):
        texto = ler(CAPITULO)
        for secao in ("Erros clássicos", "Exercícios", "Entregável", "Autoavaliação", "Para ir além", "O que foi testado e o que não foi"):
            self.assertIn(f"## {secao}", texto, f"falta a seção {secao}")
        self.assertGreaterEqual(texto.count('collapse="true"'), 3)
        for nivel in ("Reconheço", "Explico", "Executo", "Ensino"):
            self.assertIn(nivel, texto)
        self.assertIn("{#sec-p106}", texto)
        rotulos = re.findall(r"\{#(sec-[\w-]+)", texto)
        self.assertTrue(all(r.startswith("sec-p106") for r in rotulos), rotulos)
        self.assertEqual(len(rotulos), len(set(rotulos)))

    def test_o_capitulo_declara_a_fonte_dos_limites_e_o_que_nao_conferiu(self):
        texto = ler(CAPITULO)
        self.assertIn("CONAMA", texto)
        self.assertIn("08/10/2026", texto)
        self.assertIn("Não conferi", texto)

    def test_o_texto_nao_repete_afirmacoes_corrigidas_na_revisao(self):
        texto = ler(CAPITULO)
        # a ordem dos WHEN não muda o resultado quando há ramo IS NULL; o que importa é existir o ramo
        self.assertNotIn("Se você colocar o `IS NULL` por último", texto)
        self.assertNotIn("A ordem dos `WHEN` importa", texto)
        # `?1` com tupla é descontinuado no Python 3.12
        self.assertNotRegex(texto, r"\?\d")
        # "outros bancos não" generalizava demais
        self.assertNotIn("outros bancos não", texto)

    def test_nenhum_segredo_no_capitulo(self):
        texto = ler(CAPITULO).lower()
        for suspeito in ("password=", "senha=", "token=", "ghp_", "api_key"):
            self.assertNotIn(suspeito, texto)

    def test_quarto_lista_o_capitulo(self):
        config = yaml.safe_load(ler("_quarto.yml"))
        capitulos = []
        for item in config["book"]["chapters"]:
            capitulos += item["chapters"] if isinstance(item, dict) else [item]
        self.assertIn(CAPITULO, capitulos)
        self.assertTrue((RAIZ / CAPITULO).is_file())
        # o P1 vem depois do P0 e antes do P9
        partes = [item["part"] for item in config["book"]["chapters"] if isinstance(item, dict)]
        self.assertTrue(partes[0].startswith("P0") and partes[1].startswith("P1"), partes)

    def test_codigo_sem_barra_invertida_em_expressao_de_fstring(self):
        """Antes do Python 3.12, uma barra invertida dentro de {...} num f-string é erro de sintaxe (o CI roda a partir do 3.11)."""
        for m in re.finditer(r"^```\{python\}[ \t]*\n(.*?)^```", ler(CAPITULO), re.S | re.M):
            for g in re.findall(r"""f(?:"[^"\n]*"|'[^'\n]*')""", m.group(1)):
                for expressao in re.findall(r"\{([^{}]*)\}", g):
                    self.assertNotIn("\\", expressao, g)


# =====================================================================================================================
#  P1-07 · SQL essencial II: agregação e junções
# =====================================================================================================================
CONFERENCIAS_107 = {
    "agregados", "media_ingenua", "vazio", "campanhas", "por_parametro", "od_por_ponto", "coluna_solta", "grupo_null",
    "having", "having_contagem", "min_ou_media", "conformidade", "left_inner_fontes", "left_contagem", "where_ou_on",
    "anti_join", "fanout_contagem", "fanout_media", "fanout_por_ponto", "fanout_remendos", "fanout_correcao",
    "pandas_groupby", "pandas_dropna", "pandas_merge", "pandas_validate", "pandas_limites", "pandas_to_sql", "relatorio",
}


class CapituloP107(unittest.TestCase):
    """Executa o capítulo P1-07 uma vez e guarda o espaço de nomes e a saída."""

    @classmethod
    def setUpClass(cls):
        try:
            import pandas  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("o capítulo P1-07 usa o pandas (pip install pandas)")
        buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
                with warnings.catch_warnings():
                    warnings.simplefilter("error", DeprecationWarning)   # o mesmo rigor do P1-06
                    cls.ns = executar(RAIZ / CAPITULO_107, tempfile.mkdtemp(), incluir_gabaritos=True, verbose=False)
        except SystemExit:
            raise AssertionError(f"{CAPITULO_107}: um bloco de código falhou.\n{buffer.getvalue()[-3000:]}")
        cls.saida = buffer.getvalue()
        cls.texto = ler(CAPITULO_107)

    # -- as conferências do próprio capítulo ---------------------------------------------------------------------
    def test_todas_as_conferencias_do_capitulo_deram_verdadeiro(self):
        conf = self.ns["conferencias"]
        self.assertEqual(set(conf), CONFERENCIAS_107)       # nenhuma conferência foi removida ou esquecida
        self.assertEqual([k for k, v in conf.items() if v is not True], [])

    # -- dados, chaves e esquema --------------------------------------------------------------------------------
    def test_dados_e_tabelas(self):
        ns = self.ns
        self.assertEqual((len(ns["PONTOS"]), len(ns["PARAMETROS"]), len(ns["RESULTADOS"]), len(ns["FONTES"])), (4, 3, 20, 4))
        self.assertEqual((ns["OD_MINIMO_MG_L"], ns["PH_MINIMO"], ns["PH_MAXIMO"], ns["TURBIDEZ_MAXIMA_UNT"]), (5.0, 6.0, 9.0, 100.0))
        self.assertEqual(sum(1 for r in ns["RESULTADOS"] if r[3] is None), 1)
        self.assertEqual({r[0] for r in ns["RESULTADOS"]}, {"P01", "P02", "P03"})     # o P04 não tem coleta
        self.assertIn("P04", {p[0] for p in ns["PONTOS"]})
        # os 20 resultados são os mesmos do P1-06 (pontos, datas, parâmetros e valores)
        p106 = {tuple(a[:4]) for a in executar_celula(CAPITULO, "p106-dados")["AMOSTRAS"]}
        self.assertEqual({tuple(r) for r in ns["RESULTADOS"]}, p106)

    def test_chave_estrangeira_no_sqlite(self):
        ns = self.ns
        self.assertEqual(ns["fk_padrao"], 0)                                   # desligada numa conexão nova
        self.assertEqual(ns["orfao_sem_fk"], "ENTROU")
        self.assertEqual(ns["fk_ligada"], 1)
        self.assertTrue(ns["orfao_com_fk"].startswith("RECUSADO"))
        self.assertIn("FOREIGN KEY constraint failed", ns["orfao_com_fk"])
        self.assertEqual(ns["orfaos_antigos"], [("resultado", 1, "ponto", 0)])  # foreign_key_check acha o órfão antigo
        self.assertEqual(ns["fk_dentro_de_transacao"], 0)                      # o PRAGMA é ignorado numa transação
        self.assertEqual(ns["pk_nulo"]["sem NOT NULL"], "ENTROU")
        self.assertTrue(ns["pk_nulo"]["com NOT NULL"].startswith("RECUSADO"))
        self.assertTrue(ns["recusa_filho"].startswith("RECUSADO") and ns["recusa_pai"].startswith("RECUSADO"))

    # -- agregação ----------------------------------------------------------------------------------------------
    def test_agregados_numeros_citados(self):
        ns = self.ns
        self.assertEqual(tuple(ns["agregados_sql"]), (6, 5, 234.0, 46.8, 9.0, 135.0))   # "6 análises, 5 com resultado, 234,0, 46,8"
        self.assertAlmostEqual(ns["media_certa"], 46.8)
        self.assertAlmostEqual(ns["media_zero"], 39.0)
        self.assertAlmostEqual(ns["soma_sobre_linhas"], 39.0)
        self.assertAlmostEqual(ns["media_de_tudo"], 17.1105, places=4)
        self.assertEqual(ns["vazio_sql"], (0, 0, None, None, 0.0))
        self.assertEqual(ns["campanhas"], 3)

    def test_grupos_numeros_citados(self):
        ns = self.ns
        self.assertEqual([(r[0], r[1], r[2], r[3], r[4], r[5]) for r in ns["por_parametro_sql"]],
                         [("OD", 7, 7, 6.24, 3.9, 7.8), ("pH", 7, 7, 6.77, 5.8, 7.4), ("turbidez", 6, 5, 46.8, 9.0, 135.0)])
        self.assertEqual(ns["od_por_ponto_sql"], [("P01", 3, 7.47), ("P02", 3, 4.93), ("P03", 1, 6.5)])
        self.assertEqual(len(ns["solta"]), 3)
        self.assertEqual(len(ns["grupos_turbidez"]), 6)
        self.assertEqual(dict(ns["grupos_turbidez"])[None], 1)

    def test_having_numeros_citados(self):
        ns = self.ns
        self.assertEqual(ns["having_sql"], [("P02", 3, 4.93)])
        self.assertIn("misuse of aggregate", ns["erro_agregado_no_where"])
        self.assertEqual(ns["AMOSTRAS_MINIMAS"], 2)
        self.assertEqual(ns["minimo_sql"], [("P01", 3, 7.47), ("P02", 3, 4.93)])      # P03 (1 só resultado) fica de fora
        self.assertEqual(ns["alguma_sql"], [("P02", 3, 3.9)])

    # -- junções ------------------------------------------------------------------------------------------------
    def test_join_numeros_citados(self):
        ns = self.ns
        self.assertEqual(ns["conformidade_sql"], [
            ("P01", "OD", 3, 0), ("P01", "pH", 3, 0), ("P01", "turbidez", 3, 0),
            ("P02", "OD", 3, 2), ("P02", "pH", 3, 1), ("P02", "turbidez", 2, 1),
            ("P03", "OD", 1, 0), ("P03", "pH", 1, 0),
        ])
        self.assertEqual((len(ns["inner_pf"]), len(ns["left_pf"])), (4, 6))
        self.assertEqual(ns["contagem_sql"], [("P01", 9, 9), ("P02", 9, 9), ("P03", 2, 2), ("P04", 1, 0)])
        self.assertEqual(ns["com_where"], [("P01", 3), ("P02", 3), ("P03", 1)])        # o WHERE perde o P04
        self.assertEqual(ns["com_on"], [("P01", 3), ("P02", 3), ("P03", 1), ("P04", 0)])
        self.assertEqual(ns["sem_coleta_sql"], ["P04"])
        if not str(ns["n_right"]).startswith("ERRO"):      # RIGHT JOIN: 20 resultados + o P04 sem par
            self.assertEqual(ns["n_right"], 21)

    def test_multiplicacao_de_linhas_numeros_citados(self):
        ns = self.ns
        self.assertEqual(ns["previsto"], (20, 22, 31))
        self.assertEqual(ns["no_sql"], (20, 22, 31))
        self.assertEqual([round(ns[k], 4) for k in ("media_correta", "media_interna", "media_externa")], [6.2429, 5.3250, 5.9091])
        self.assertEqual(ns["fanout_por_ponto"], [("P01", 3, 3, 22.4, 7.47), ("P02", 6, 3, 29.6, 4.93), ("P03", 2, 1, 13.0, 6.5)])
        self.assertEqual(ns["soma_certa"], {"P01": 22.4, "P02": 14.8, "P03": 6.5})
        self.assertEqual(ns["n_distintos"], 20)
        self.assertAlmostEqual(ns["media_distinta"], 6.0)
        self.assertAlmostEqual(ns["media_certa_pequena"], 19 / 3)
        self.assertEqual(ns["corrigido_sql"], [("P01", 3, 7.47, 0), ("P02", 3, 4.93, 2), ("P03", 1, 6.5, 2)])
        self.assertEqual(ns["linhas_depois"], 20)
        self.assertAlmostEqual(ns["media_global_corrigida"], ns["media_correta"])
        # a função que prevê o tamanho de uma junção, nos casos simples
        f = ns["linhas_apos_join"]
        self.assertEqual(f(["a", "a", "b"], ["a", "a", "a"], "interno"), 6)
        self.assertEqual(f(["a", "b", "c"], ["a", "a"], "externo"), 4)
        self.assertEqual(f([], ["a"], "interno"), 0)

    def test_figura(self):
        figuras = self.ns["_figuras"]
        self.assertEqual(len(figuras), 1)
        self.assertTrue(figuras[0].is_file())
        self.assertIn("valores desenhados, painel (a): (20, 22, 31)", self.saida)
        self.assertIn("valores desenhados, painel (b): [6.24, 5.33, 5.91]", self.saida)

    # -- pandas -------------------------------------------------------------------------------------------------
    def test_pandas(self):
        ns = self.ns
        self.assertEqual(ns["df"].shape, (20, 4))
        self.assertEqual(int(ns["df"]["valor"].isna().sum()), 1)
        self.assertEqual((len(ns["m_interno"]), len(ns["m_externo"])), (22, 31))
        self.assertEqual((len(ns["grupos_padrao"]), len(ns["grupos_com_nan"])), (5, 6))
        self.assertTrue(ns["erro_validate"].startswith("Merge keys are not unique"))
        self.assertEqual(ns["n_orfaos"], 1)                          # validate="many_to_one" não acusa a chave órfã
        self.assertEqual((ns["n_linhas_pandas"], ns["n_linhas_sql"]), (2, 1))   # NaN casa com NaN no pandas; NULL não casa no SQL
        self.assertTrue(ns["perdeu_regras"])                         # o to_sql(replace) perde as regras da tabela
        self.assertEqual((ns["linhas_guardadas"], ns["linhas_depois_do_ruim"]), (20, 20))
        self.assertTrue(ns["recusou_dado_ruim"])

    # -- prática, dialetos e exercícios -------------------------------------------------------------------------------
    def test_relatorio_numeros_citados(self):
        self.assertEqual(self.ns["relatorio_sql"], [
            ("P01", 3, 9, 0, 100.0), ("P02", 3, 8, 4, 50.0), ("P03", 1, 2, 0, 100.0), ("P04", 0, 0, 0, None)])

    def test_dialetos(self):
        ns = self.ns
        chaves = {c for c, _o_que, _sql in ns["SONDAS"]}
        self.assertEqual(set(ns["dialeto_sqlite"]), chaves)
        self.assertEqual(set(ns["POSTGRESQL_16_15"]), chaves)                       # o registro cobre cada sonda
        sq, pg = ns["dialeto_sqlite"], ns["POSTGRESQL_16_15"]
        self.assertEqual(sq["coluna_solta"], "3")
        self.assertEqual(sq["having_coluna_solta"], "3")                            # o SQLite aceita a coluna solta no HAVING
        self.assertEqual(sq["round_media"], "6.2")
        self.assertEqual(sq["avg_inteiros"], "1.5")
        self.assertTrue(sq["agregado_where"].startswith("ERRO"))
        self.assertEqual(sq["conjunto_vazio"], "0 | NULL | NULL")
        self.assertEqual(sq["ordem_null"], "NULL")                                  # o SQLite põe o NULL primeiro
        self.assertEqual((sq["div_zero_pct"], sq["nullif_pct"]), ("NULL", "NULL"))
        self.assertEqual(sq["avg_distinct"], "6.0")
        self.assertEqual((sq["fk_padrao"], sq["pk_texto_nulo"]), ("ENTROU", "ENTROU"))
        self.assertEqual(pg["ordem_null"], "9")                                     # o PostgreSQL põe o NULL por último
        self.assertEqual(pg["conjunto_vazio"], sq["conjunto_vazio"])
        self.assertEqual(pg["avg_distinct"], "6.0000000000000000")
        for chave in ("coluna_solta", "having_coluna_solta", "apelido_having", "round_media", "agregado_where", "group_concat", "div_zero_pct", "fk_padrao", "pk_texto_nulo"):
            self.assertTrue(pg[chave].startswith("ERRO"), chave)

    def test_roteiro_do_postgresql_cobre_cada_sonda_e_nao_tem_segredo(self):
        roteiro = ler("tools/registro_postgresql_p1-07.sql")
        for chave in self.ns["POSTGRESQL_16_15"]:
            self.assertIn(f"@@ {chave}", roteiro, chave)
        self.assertEqual(roteiro.count("CREATE TEMP TABLE"), 5)    # 4 do capítulo + a da sonda da chave primária
        self.assertNotIn("CREATE TABLE", roteiro.replace("CREATE TEMP TABLE", ""))   # só tabelas temporárias
        self.assertNotIn("DROP", roteiro.upper())
        for suspeito in ("password", "senha", "token", "ghp_"):
            self.assertNotIn(suspeito, roteiro.lower())

    def test_gabaritos_dos_exercicios(self):
        ns = self.ns
        self.assertEqual({k: v[0] for k, v in ns["ex1"].items()}, {"a": 4, "b": 6, "c": 21, "d": 20})
        self.assertEqual((ns["por_media"], ns["por_minimo"]), (["P02"], ["P01", "P02"]))
        self.assertAlmostEqual(ns["media_p01"], 6.825)
        self.assertEqual((ns["media_p02_ignora"], ns["media_p02_zero"], ns["n_linhas_p02"], ns["n_medidos_p02"]), (97.5, 65.0, 3, 2))
        self.assertEqual(ns["certo"], [("P01", 3), ("P02", 3), ("P03", 1), ("P04", 0)])
        self.assertEqual(ns["errado"], [("P01", 3), ("P02", 3), ("P03", 1)])
        self.assertEqual((ns["n_interno"], ns["n_externo"]), (8, 11))
        self.assertAlmostEqual(ns["soma_interna"], 42.6)
        self.assertAlmostEqual(ns["soma_externa"], 65.0)
        self.assertEqual(ns["ex6_a"], [("P01", 7.8), ("P02", 6.1), ("P03", 6.5)])
        self.assertEqual(len(ns["ex6_b"]), 20)
        self.assertEqual(ns["largo_sql"], [("P01", 7.47, 7.03, 13.0), ("P02", 4.93, 6.3, 97.5), ("P03", 6.5, 7.4, None), ("P04", None, None, None)])
        self.assertEqual(ns["com_else_zero"], 2.49)

    def test_o_banco_do_capitulo_foi_fechado_no_fim(self):
        with self.assertRaises(sqlite3.ProgrammingError):
            self.ns["banco"].execute("SELECT 1")

    def test_o_texto_cita_os_numeros_certos(self):
        texto = self.texto
        for citacao in (
            "46,8", "234,0", "**39,0**", "17,1105", "6,24", "6,77", "4,93", "3,9 mg/L", "6,825", "97,5", "65,0", "32,5",
            "**6,2429**", "**5,3250**", "**5,9091**", "42,6", "65,0", "**22**", "**31**", "9 × 2 = 18", "2,49",
            "6,3333", "versão 16.15", "27 consultas", "**20 linhas**",
        ):
            self.assertIn(citacao, texto, citacao)

    def test_numeros_da_prosa_batem_com_os_valores_calculados_pelo_codigo(self):
        """Cada número abaixo aparece no texto e sai, formatado à brasileira, de um valor que o código do capítulo calculou."""
        ns, texto = self.ns, self.texto

        def br(x, casas):
            return f"{x:.{casas}f}".replace(".", ",")

        por_ponto = {linha[0]: linha for linha in ns["fanout_por_ponto"]}          # (ponto, linhas, distintas, soma, media)
        relatorio = {linha[0]: linha for linha in ns["relatorio_sql"]}             # (ponto, campanhas, medidos, fora, pct)
        largo = {linha[0]: linha for linha in ns["largo_sql"]}                     # (ponto, od, ph, turbidez)
        ligados = [
            (br(por_ponto["P02"][3], 1), "soma de P02 depois do LEFT JOIN"),                        # 29,6
            (br(ns["soma_certa"]["P02"], 1), "soma certa de P02"),                                  # 14,8
            (br(por_ponto["P03"][3], 1), "soma de P03 depois do LEFT JOIN"),                        # 13,0
            (br(ns["media_interna"], 2), "média depois do JOIN interno"),                           # 5,33
            (br(ns["media_externa"], 2), "média depois do LEFT JOIN"),                              # 5,91
            (br(relatorio["P02"][4], 0) + "% de conformidade", "conformidade de P02"),              # 50% de conformidade
            (br(largo["P01"][2], 2), "pH médio de P01"),                                            # 7,03
            (f"turbidez {br(largo['P01'][3], 1)}", "turbidez média de P01"),                        # turbidez 13,0
        ]
        for citado, o_que in ligados:
            self.assertIn(citado, texto, o_que)
        # o limiar do ROUND de 2 casas cobre o pior caso (ROUND(0.125, 2) = 0.13) e o capítulo não usa isclose sem tolerância
        self.assertTrue(math.isclose(0.13, 0.125, abs_tol=ns["TOL_DUAS_CASAS"]))
        for m in re.finditer(r"^```(?:\{python\}|python)[ \t]*\n(.*?)^```", texto, re.S | re.M):
            codigo = m.group(1)
            for achado in re.finditer(r"math\.isclose\(", codigo):
                nivel, fim = 0, achado.end() - 1
                for i in range(achado.end() - 1, len(codigo)):
                    nivel += {"(": 1, ")": -1}.get(codigo[i], 0)
                    if nivel == 0:
                        fim = i
                        break
                self.assertIn("abs_tol", codigo[achado.start():fim], codigo[achado.start():fim + 1])


class EstruturaP107(unittest.TestCase):
    def test_o_capitulo_tem_as_secoes_do_metodo(self):
        texto = ler(CAPITULO_107)
        for secao in ("Erros clássicos", "Exercícios", "Entregável", "Autoavaliação", "Para ir além", "O que foi testado e o que não foi"):
            self.assertIn(f"## {secao}", texto, f"falta a seção {secao}")
        self.assertGreaterEqual(texto.count('collapse="true"'), 7)       # seis exercícios e o desafio
        for nivel in ("Reconheço", "Explico", "Executo", "Ensino"):
            self.assertIn(nivel, texto)
        self.assertIn("{#sec-p107}", texto)
        rotulos = re.findall(r"\{#(sec-[\w-]+)", texto)
        self.assertTrue(all(r.startswith("sec-p107") for r in rotulos), rotulos)
        self.assertEqual(len(rotulos), len(set(rotulos)))

    def test_todo_cabecalho_tem_linha_em_branco_antes(self):
        """O Pandoc só reconhece '## Título' depois de uma linha em branco (ou logo após a abertura de um bloco ':::')."""
        for caminho in sorted(RAIZ.glob("*.qmd")):
            dentro, linhas = False, caminho.read_text(encoding="utf-8").split("\n")
            for i, linha in enumerate(linhas):
                if linha.startswith("```"):
                    dentro = not dentro
                elif not dentro and re.match(r"#{1,6} ", linha) and i > 0:
                    anterior = linhas[i - 1]
                    self.assertTrue(anterior.strip() == "" or re.match(r":{3,} *\{", anterior),
                                    f"{caminho.name}, linha {i + 1}: cabeçalho sem linha em branco antes: {linha}")

    def test_a_figura_tem_rotulo_legenda_texto_alternativo_e_referencia(self):
        texto = ler(CAPITULO_107)
        self.assertIn("#| label: fig-p107-fanout", texto)
        self.assertIn("#| fig-cap:", texto)
        self.assertIn("#| fig-alt:", texto)
        self.assertIn("@fig-p107-fanout", texto)

    def test_o_capitulo_declara_a_fonte_dos_limites_e_o_que_nao_conferiu(self):
        texto = ler(CAPITULO_107)
        for frase in ("CONAMA", "08/10/2026", "Não conferi", "não foi executado no Windows", "sintético"):
            self.assertIn(frase, texto, frase)

    def test_o_texto_nao_traz_erros_conhecidos(self):
        texto = ler(CAPITULO_107)
        self.assertNotRegex(texto, r"\?\d")                 # `?1` com tupla é descontinuado no Python 3.12
        for suspeito in ("password=", "senha=", "token=", "ghp_", "api_key"):
            self.assertNotIn(suspeito, texto.lower())

    def test_quarto_lista_o_capitulo_depois_do_p1_06(self):
        config = yaml.safe_load(ler("_quarto.yml"))
        parte_p1 = [item for item in config["book"]["chapters"] if isinstance(item, dict) and item["part"].startswith("P1")][0]
        self.assertEqual(parte_p1["chapters"], [CAPITULO, CAPITULO_107])
        self.assertTrue((RAIZ / CAPITULO_107).is_file())

    def test_codigo_sem_barra_invertida_em_expressao_de_fstring(self):
        """Antes do Python 3.12, uma barra invertida dentro de {...} num f-string é erro de sintaxe (o CI roda a partir do 3.11)."""
        for m in re.finditer(r"^```(?:\{python\}|python)[ \t]*\n(.*?)^```", ler(CAPITULO_107), re.S | re.M):
            for g in re.findall(r"""f(?:"[^"\n]*"|'[^'\n]*')""", m.group(1)):
                for expressao in re.findall(r"\{([^{}]*)\}", g):
                    self.assertNotIn("\\", expressao, g)

    def test_todo_bloco_python_compila(self):
        for i, m in enumerate(re.finditer(r"^```(?:\{python\}|python)[ \t]*\n(.*?)^```", ler(CAPITULO_107), re.S | re.M), 1):
            compile(m.group(1), f"{CAPITULO_107}, bloco {i}", "exec")


if __name__ == "__main__":
    unittest.main(verbosity=2)
