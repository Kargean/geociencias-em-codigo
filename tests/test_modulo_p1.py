"""Testes do capítulo P1-06 (SQL essencial I): o código executa e os números citados no texto conferem.

Execute:  python tests/test_modulo_p1.py        (leva poucos segundos; precisa de matplotlib e PyYAML)

O que este arquivo garante:
  1. todos os blocos de código do capítulo (e os gabaritos dos exercícios) executam em ordem, sem avisos de descontinuação;
  2. os números que o texto cita são os que o código calcula (contagens, médias, datas, resultados das cinco perguntas);
  3. a lógica de três valores e as regras de afinidade de tipos escritas em Python batem com o SQLite;
  4. as respostas do SQL batem com cálculos independentes em Python;
  5. o registro do PostgreSQL tem uma entrada para cada sonda de dialeto (o registro em si NÃO é reexecutado aqui);
  6. a estrutura do capítulo (seções, gabaritos recolhíveis, rótulos) e a ordem no _quarto.yml estão corretas.

O que ele NÃO garante: que o Quarto renderiza o capítulo, que o código roda no Windows ou em outras versões do SQLite,
nem que o registro do PostgreSQL continua valendo em outras versões.
"""
import contextlib
import io
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


def ler(caminho):
    return (RAIZ / caminho).read_text(encoding="utf-8")


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


if __name__ == "__main__":
    unittest.main(verbosity=2)
