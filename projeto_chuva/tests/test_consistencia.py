"""O teste mais importante do módulo: o MESMO resultado por dois caminhos.

Python puro (chuva/resumo.py) e SQL (sql/consultas/) calculam as mesmas coisas de jeitos diferentes.
Se um dos dois tiver um erro, os dois deixam de concordar, e o teste acusa.
"""
import unittest
from datetime import date
from pathlib import Path

from chuva import banco
from chuva import qualidade as q
from chuva import resumo as r

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "dados" / "chuva_diaria.csv"
CSV_ESTACOES = RAIZ / "dados" / "estacoes.csv"


class PythonContraSQL(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registros, _ = q.ler_chuva(CSV)
        cls.con = banco.construir_banco(CSV_ESTACOES, cls.registros)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def sql(self, nome, **params):
        return banco.executar_consulta(self.con, nome, limiar=1.0, **params)

    def test_total_mensal(self):
        py = r.total_mensal(self.registros)
        linhas = self.sql("02_total_mensal")
        self.assertEqual(len(linhas), len(py))
        for l in linhas:
            m = py[(l["estacao"], l["mes"])]
            with self.subTest(estacao=l["estacao"], mes=l["mes"]):
                self.assertEqual(l["total_mm"], m.total_mm)
                self.assertEqual(
                    (l["n_validos"], l["n_registrados"], l["dias_no_mes"], bool(l["completo"])),
                    (m.n_validos, m.n_registrados, m.dias_no_mes, m.completo),
                )

    def test_dias_de_chuva(self):
        py = r.dias_de_chuva(self.registros)
        sql = {(l["estacao"], l["ano"]): l["dias_de_chuva"] for l in self.sql("04_dias_de_chuva")}
        self.assertEqual(sql, py)

    def test_maior_periodo_seco(self):
        linhas = {l["estacao"]: (l["dias"], date.fromisoformat(l["inicio"])) for l in self.sql("05_maior_periodo_seco")}
        for est in r.estacoes_em(self.registros):
            with self.subTest(estacao=est):
                self.assertEqual(linhas[est], r.maior_periodo_seco(r.serie(self.registros, est)))

    def test_maximo_acumulado_5_dias(self):
        linhas = {l["estacao"]: (l["acumulado_mm"], date.fromisoformat(l["fim"])) for l in self.sql("06_maximo_5_dias")}
        for est in r.estacoes_em(self.registros):
            with self.subTest(estacao=est):
                self.assertEqual(linhas[est], r.maximo_acumulado(r.serie(self.registros, est), janela=5))

    def test_resumo_por_estacao(self):
        for l in self.sql("01_resumo_estacoes"):
            s = r.serie(self.registros, l["estacao"])
            with self.subTest(estacao=l["estacao"]):
                self.assertEqual(l["linhas"], len(s))
                self.assertEqual(l["validos"], sum(v is not None for v in s.values()))
                self.assertEqual(l["ausentes"], sum(v is None for v in s.values()))
                self.assertEqual((l["primeira"], l["ultima"]), (min(s).isoformat(), max(s).isoformat()))

    def test_media_por_bacia_confere_com_a_mao(self):
        totais = {}
        for r_ in self.registros:
            if r_.chuva_mm is not None:
                chave = (r_.estacao, r_.data.year)
                totais[chave] = totais.get(chave, 0.0) + r_.chuva_mm
        bacia = {"E01": "Bacia Alfa", "E02": "Bacia Alfa", "E03": "Bacia Beta", "E04": "Bacia Beta"}
        for l in self.sql("03_chuva_por_bacia"):
            membros = [v for (e, ano), v in totais.items() if bacia[e] == l["bacia"] and str(ano) == l["ano"]]
            with self.subTest(bacia=l["bacia"], ano=l["ano"]):
                self.assertEqual(l["estacoes"], len(membros))
                self.assertAlmostEqual(l["media_dos_totais_mm"], sum(membros) / len(membros), delta=0.051)

    def test_numeros_citados_no_livro(self):
        bacias = {(l["bacia"], l["ano"]): l["media_dos_totais_mm"] for l in self.sql("03_chuva_por_bacia")}
        self.assertEqual(
            bacias,
            {("Bacia Alfa", "2024"): 1362.7, ("Bacia Alfa", "2025"): 1222.1, ("Bacia Beta", "2024"): 1509.1, ("Bacia Beta", "2025"): 1533.7},
        )


class ArmadilhaDaJanelaPorLinhas(unittest.TestCase):
    """Erro clássico: janela por NÚMERO DE LINHAS em vez de por DATA. Com data faltando, os dois divergem."""

    def test_rows_e_range_divergem_quando_falta_uma_data(self):
        con = banco.conectar()
        banco.criar_esquema(con)
        con.execute("INSERT INTO estacao VALUES ('A', 'T', -21, -41, 1, 'B')")
        # dias 1, 2, 4, 5, 6: o dia 3 não tem linha. Chuva forte nos dias 1 e 2.
        dados = [("2024-01-01", 50.0), ("2024-01-02", 50.0), ("2024-01-04", 1.0), ("2024-01-05", 1.0), ("2024-01-06", 1.0)]
        con.executemany("INSERT INTO chuva_diaria VALUES ('A', ?, ?)", dados)
        por_linhas = con.execute(
            "SELECT MAX(s) FROM (SELECT SUM(chuva_mm) OVER (ORDER BY data ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS s, "
            "COUNT(*) OVER (ORDER BY data ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS n FROM chuva_diaria) WHERE n = 3"
        ).fetchone()[0]
        por_data = con.execute(
            "SELECT MAX(s) FROM (SELECT SUM(chuva_mm) OVER w AS s, COUNT(chuva_mm) OVER w AS n FROM chuva_diaria "
            "WINDOW w AS (ORDER BY julianday(data) RANGE BETWEEN 2 PRECEDING AND CURRENT ROW)) WHERE n = 3"
        ).fetchone()[0]
        con.close()
        self.assertEqual(por_linhas, 101.0)  # 50 + 50 + 1: "3 linhas", mas são 4 dias de calendário
        self.assertEqual(por_data, 3.0)  # nenhuma janela de 3 DIAS seguidos pega os dois 50


class ConsultasEmCasosPequenos(unittest.TestCase):
    """Os dados oficiais podem não exercitar os casos de borda. Aqui montamos bancos minúsculos de propósito."""

    def banco_com(self, dados):
        """dados: lista de (AAAA-MM-DD, mm ou None) para a estação A."""
        con = banco.conectar()
        banco.criar_esquema(con)
        con.execute("INSERT INTO estacao VALUES ('A', 'T', -21, -41, 1, 'B')")
        con.executemany("INSERT INTO chuva_diaria VALUES ('A', ?, ?)", dados)
        return con

    def test_maximo_5_dias_nao_atravessa_buraco_de_datas(self):
        # dias 1 e 2 com 50 mm; o dia 3 NÃO TEM LINHA; dias 4 a 10 com 1 mm.
        dados = [("2024-01-01", 50.0), ("2024-01-02", 50.0)] + [(f"2024-01-{d:02d}", 1.0) for d in range(4, 11)]
        con = self.banco_com(dados)
        sql = [tuple(l) for l in banco.executar_consulta(con, "06_maximo_5_dias")]
        con.close()
        self.assertEqual(sql, [("A", 5.0, "2024-01-08")])
        serie = {date.fromisoformat(d): v for d, v in dados}
        self.assertEqual(r.maximo_acumulado(serie, janela=5), (5.0, date(2024, 1, 8)))

    def test_maximo_5_dias_ignora_janela_com_null(self):
        dados = [("2024-01-01", 9.0), ("2024-01-02", None), ("2024-01-03", 9.0), ("2024-01-04", 9.0), ("2024-01-05", 9.0)]
        con = self.banco_com(dados)
        sql = list(banco.executar_consulta(con, "06_maximo_5_dias"))
        con.close()
        self.assertEqual(sql, [])  # nenhuma janela completa; Python também devolve (None, None)
        self.assertEqual(r.maximo_acumulado({date.fromisoformat(d): v for d, v in dados}), (None, None))

    def test_periodo_seco_limiar_exato_conta_como_chuvoso(self):
        dados = [("2024-01-01", 0.0), ("2024-01-02", 1.0), ("2024-01-03", 0.0)]
        con = self.banco_com(dados)
        sql = [tuple(l) for l in banco.executar_consulta(con, "05_maior_periodo_seco", limiar=1.0)]
        con.close()
        self.assertEqual(sql, [("A", 1, "2024-01-01", "2024-01-01")])

    def test_periodo_seco_quebra_em_null_e_em_data_ausente(self):
        dados = [("2024-01-01", 0.0), ("2024-01-02", 0.0), ("2024-01-03", None), ("2024-01-04", 0.0),
                 ("2024-01-06", 0.0), ("2024-01-07", 0.0), ("2024-01-08", 0.0)]  # o dia 5 não tem linha
        con = self.banco_com(dados)
        sql = [tuple(l) for l in banco.executar_consulta(con, "05_maior_periodo_seco", limiar=1.0)]
        con.close()
        self.assertEqual(sql, [("A", 3, "2024-01-06", "2024-01-08")])
        serie = {date.fromisoformat(d): v for d, v in dados}
        self.assertEqual(r.maior_periodo_seco(serie), (3, date(2024, 1, 6)))

    def test_dias_de_chuva_limiar_exato_conta(self):
        dados = [("2024-01-01", 0.9), ("2024-01-02", 1.0), ("2024-01-03", None)]
        con = self.banco_com(dados)
        sql = [tuple(l) for l in banco.executar_consulta(con, "04_dias_de_chuva", limiar=1.0)]
        con.close()
        self.assertEqual(sql, [("A", "2024", 1)])

    def test_total_mensal_de_mes_so_com_null_e_null(self):
        con = self.banco_com([("2024-01-01", None), ("2024-01-02", None)])
        linha = banco.executar_consulta(con, "02_total_mensal")[0]
        con.close()
        self.assertIsNone(linha["total_mm"])
        self.assertEqual((linha["n_validos"], linha["n_registrados"], linha["completo"]), (0, 2, 0))


if __name__ == "__main__":
    unittest.main()
