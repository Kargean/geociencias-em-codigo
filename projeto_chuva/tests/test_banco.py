"""Testes do banco SQLite (chuva/banco.py e sql/esquema.sql)."""
import sqlite3
import unittest
from pathlib import Path

from chuva import banco
from chuva import qualidade as q
from chuva.qualidade import Registro
from datetime import date

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "dados" / "chuva_diaria.csv"
CSV_ESTACOES = RAIZ / "dados" / "estacoes.csv"


class Ambiente(unittest.TestCase):
    def test_versao_do_sqlite_aceita_janelas_com_range(self):
        # RANGE com deslocamento exige SQLite >= 3.28. Se este teste falhar, atualize o Python/SQLite.
        self.assertTrue(banco.versao_sqlite_suficiente(), f"SQLite {sqlite3.sqlite_version} é antigo demais")


class Restricoes(unittest.TestCase):
    """O esquema recusa dado impossível. Cada teste tenta inserir um dado ruim e espera o erro."""

    def setUp(self):
        self.con = banco.conectar()
        banco.criar_esquema(self.con)
        self.con.execute("INSERT INTO estacao VALUES ('A', 'Teste', -21.0, -41.0, 10.0, 'Bacia X')")

    def tearDown(self):
        self.con.close()

    def inserir(self, estacao="A", data="2024-01-01", mm=1.0):
        self.con.execute("INSERT INTO chuva_diaria VALUES (?, ?, ?)", (estacao, data, mm))

    def test_dado_valido_entra_e_null_tambem(self):
        self.inserir(mm=1.0)
        self.inserir(data="2024-01-02", mm=None)
        n_null = self.con.execute("SELECT COUNT(*) FROM chuva_diaria WHERE chuva_mm IS NULL").fetchone()[0]
        self.assertEqual(n_null, 1)

    def test_chave_primaria_repetida(self):
        self.inserir()
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir()

    def test_chuva_negativa(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir(mm=-1.0)

    def test_datas_invalidas(self):
        for data in ["2024-02-30", "30/01/2024", "2024-13-01", "2024-1-5", "2024-01-01 10:00", "ontem"]:
            with self.subTest(data=data):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.inserir(data=data)

    def test_estacao_inexistente_com_chave_estrangeira_ligada(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.inserir(estacao="NAO_EXISTE")

    def test_chave_estrangeira_vem_desligada_numa_conexao_nova(self):
        # A armadilha do SQLite: sem o PRAGMA, o banco aceita estação que não existe.
        bruta = sqlite3.connect(":memory:")
        self.assertEqual(bruta.execute("PRAGMA foreign_keys").fetchone()[0], 0)
        bruta.executescript((banco.PASTA_SQL / "esquema.sql").read_text(encoding="utf-8"))
        bruta.execute("INSERT INTO chuva_diaria VALUES ('NAO_EXISTE', '2024-01-01', 1.0)")  # entra, e não deveria
        bruta.close()
        self.assertEqual(self.con.execute("PRAGMA foreign_keys").fetchone()[0], 1)  # nosso conectar() liga

    def test_texto_nao_entra_em_coluna_numerica(self):
        # Armadilha de tipos do SQLite: sem o typeof() no CHECK, 'abc' entraria na coluna REAL
        # ('abc' >= 0 é verdadeiro, pois texto compara maior que número).
        for valor in ["abc", "", "--5", b"x"]:
            with self.subTest(valor=valor):
                with self.assertRaises(sqlite3.IntegrityError):
                    self.inserir(mm=valor)
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO estacao VALUES ('B', 'Ruim', -21.0, -41.0, 'alto', 'X')")
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO estacao VALUES ('C', 'Ruim', 'norte', -41.0, 1.0, 'X')")

    def test_numero_escrito_como_texto_vira_numero(self):
        # '12.4' (texto que parece número) é convertido pela afinidade REAL: entra como 12.4, não como texto.
        self.inserir(mm="12.4")
        tipo, valor = self.con.execute("SELECT typeof(chuva_mm), chuva_mm FROM chuva_diaria").fetchone()
        self.assertEqual((tipo, valor), ("real", 12.4))

    def test_latitude_fora_do_intervalo(self):
        with self.assertRaises(sqlite3.IntegrityError):
            self.con.execute("INSERT INTO estacao VALUES ('B', 'Ruim', -91.0, -41.0, 0.0, 'X')")


class Transacao(unittest.TestCase):
    def test_carga_com_chave_repetida_nao_deixa_nada_pela_metade(self):
        con = banco.conectar()
        banco.criar_esquema(con)
        banco.carregar_estacoes(con, CSV_ESTACOES)
        regs = [Registro("E01", date(2024, 1, 1), 1.0), Registro("E01", date(2024, 1, 2), 2.0), Registro("E01", date(2024, 1, 1), 3.0)]
        with self.assertRaises(sqlite3.IntegrityError):
            banco.carregar_chuva(con, regs)
        self.assertEqual(con.execute("SELECT COUNT(*) FROM chuva_diaria").fetchone()[0], 0)
        con.close()


class Parametros(unittest.TestCase):
    def test_parametros_neutralizam_injecao_de_sql(self):
        con = banco.conectar()
        banco.criar_esquema(con)
        nome_malicioso = "Robert'); DROP TABLE estacao;--"
        con.execute("INSERT INTO estacao VALUES (?, ?, ?, ?, ?, ?)", ("X", nome_malicioso, -21.0, -41.0, 1.0, "B"))
        achou = con.execute("SELECT id FROM estacao WHERE nome = ?", (nome_malicioso,)).fetchall()
        self.assertEqual([tuple(l) for l in achou], [("X",)])
        self.assertEqual(con.execute("SELECT COUNT(*) FROM estacao").fetchone()[0], 1)  # a tabela continua lá
        con.close()


class CargaOficial(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registros, cls.rel = q.ler_chuva(CSV)
        cls.con = banco.construir_banco(CSV_ESTACOES, cls.registros)

    @classmethod
    def tearDownClass(cls):
        cls.con.close()

    def test_contagens(self):
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM estacao").fetchone()[0], 4)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM chuva_diaria").fetchone()[0], 2920)
        n_none = sum(r.chuva_mm is None for r in self.registros)
        self.assertEqual(self.con.execute("SELECT COUNT(*) FROM chuva_diaria WHERE chuva_mm IS NULL").fetchone()[0], n_none)
        self.assertEqual(n_none, 11)  # 6 códigos + 3 vazios + 1 negativo + 1 acima do limite

    def test_igual_a_null_nunca_acha_nada(self):
        # O erro clássico: "= NULL" nunca é verdadeiro. Só IS NULL funciona.
        errado = self.con.execute("SELECT COUNT(*) FROM chuva_diaria WHERE chuva_mm = NULL").fetchone()[0]
        certo = self.con.execute("SELECT COUNT(*) FROM chuva_diaria WHERE chuva_mm IS NULL").fetchone()[0]
        self.assertEqual((errado, certo), (0, 11))

    def test_null_nao_e_zero_na_media(self):
        # AVG ignora NULL. Se os ausentes virassem 0, a média cairia.
        media_com_null = self.con.execute("SELECT AVG(chuva_mm) FROM chuva_diaria WHERE estacao_id = 'E01'").fetchone()[0]
        media_se_zero = self.con.execute("SELECT AVG(COALESCE(chuva_mm, 0)) FROM chuva_diaria WHERE estacao_id = 'E01'").fetchone()[0]
        self.assertGreater(media_com_null, media_se_zero)

    def test_o_erro_do_menos_999_na_media(self):
        # Se -999 tivesse entrado como número, a média diária da E01 ficaria absurdamente baixa.
        certa = self.con.execute("SELECT AVG(chuva_mm) FROM chuva_diaria WHERE estacao_id = 'E01'").fetchone()[0]
        n_codigo_e01 = 5
        n_validos = self.con.execute("SELECT COUNT(chuva_mm) FROM chuva_diaria WHERE estacao_id = 'E01'").fetchone()[0]
        soma = certa * n_validos
        errada = (soma - 999 * n_codigo_e01) / (n_validos + n_codigo_e01)
        self.assertLess(errada, 0)
        self.assertGreater(certa, 3)

    def test_consulta_inexistente(self):
        with self.assertRaises(FileNotFoundError) as ctx:
            banco.executar_consulta(self.con, "nao_existe")
        self.assertIn("02_total_mensal", str(ctx.exception))

    def test_todas_as_consultas_rodam(self):
        nomes = banco.listar_consultas()
        self.assertEqual(len(nomes), 6)
        for nome in nomes:
            with self.subTest(consulta=nome):
                self.assertGreater(len(banco.executar_consulta(self.con, nome, limiar=1.0)), 0)

    def test_parametro_faltando_na_consulta_gera_erro(self):
        with self.assertRaises(sqlite3.ProgrammingError):
            banco.executar_consulta(self.con, "05_maior_periodo_seco")  # esqueceu o :limiar

    def test_indice_e_usado_em_filtro_por_data(self):
        plano = self.con.execute(
            "EXPLAIN QUERY PLAN SELECT COUNT(*) FROM chuva_diaria WHERE data BETWEEN '2024-03-01' AND '2024-03-31'"
        ).fetchall()
        self.assertIn("idx_chuva_data", " ".join(str(l["detail"]) for l in plano))


if __name__ == "__main__":
    unittest.main()
