"""Testes da leitura e limpeza (chuva/qualidade.py).

Como ler este arquivo: cada método que começa com `test_` é um teste. O unittest roda todos e
mostra um ponto (.) para cada um que passou e um F para cada um que falhou, com a explicação.
"""
import tempfile
import unittest
from datetime import date
from pathlib import Path

from chuva import qualidade as q
from chuva import sintetico

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "dados" / "chuva_diaria.csv"


class InterpretarValor(unittest.TestCase):
    def test_casos_validos(self):
        casos = [
            ("12.4", (12.4, "ok")),
            ("12,4", (12.4, "virgula")),
            ("0", (0.0, "ok")),
            ("0.0", (0.0, "ok")),
            ("-0.0", (0.0, "ok")),
            (" 7 ", (7.0, "ok")),
            ("300", (300.0, "ok")),  # o limite é inclusivo
        ]
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.assertEqual(q.interpretar_valor(texto), esperado)

    def test_ausentes_e_descartados(self):
        casos = [
            ("-999", (None, "codigo")),
            ("-999.0", (None, "codigo")),
            ("-9999", (None, "codigo")),
            ("", (None, "vazio")),
            ("   ", (None, "vazio")),
            ("-3.2", (None, "negativo")),
            ("300.1", (None, "acima_limite")),
            ("412.0", (None, "acima_limite")),
        ]
        for texto, esperado in casos:
            with self.subTest(texto=texto):
                self.assertEqual(q.interpretar_valor(texto), esperado)

    def test_texto_que_nao_e_numero_levanta_erro(self):
        for texto in ["abc", "1.234,5", "1,2,3", "nan", "inf", "1e3", "1_0", "--5", "5.", ".5"]:
            with self.subTest(texto=texto):
                with self.assertRaises(ValueError):
                    q.interpretar_valor(texto)

    def test_menos_999_nunca_vira_numero(self):
        # O erro clássico: tratar -999 como medida. Aqui ele vira "ausente", nunca float.
        valor, _ = q.interpretar_valor("-999")
        self.assertIsNone(valor)


class LerChuvaEmArquivoPequeno(unittest.TestCase):
    def escrever(self, pasta, texto):
        caminho = Path(pasta) / "teste.csv"
        caminho.write_text(texto, encoding="utf-8", newline="\n")
        return caminho

    def test_leitura_ordenacao_e_duplicatas(self):
        texto = (
            "estacao,data,chuva_mm\n"
            "B,2024-01-02,3.0\n"
            "A,2024-01-02,0.0\n"
            "A,2024-01-01,\"1,5\"\n"
            "A,2024-01-01,\"1,5\"\n"  # duplicata exata
            "B,2024-01-02,9.9\n"  # duplicata conflitante: vale a primeira
            "A,2024-01-03,-999\n"
        )
        with tempfile.TemporaryDirectory() as pasta:
            regs, rel = q.ler_chuva(self.escrever(pasta, texto))
        self.assertEqual(
            [(r.estacao, r.data.isoformat(), r.chuva_mm) for r in regs],
            [("A", "2024-01-01", 1.5), ("A", "2024-01-02", 0.0), ("A", "2024-01-03", None), ("B", "2024-01-02", 3.0)],
        )
        self.assertEqual(rel.linhas_lidas, 6)
        self.assertEqual(rel.duplicatas_exatas, 1)
        self.assertEqual(rel.duplicatas_conflitantes, 1)
        self.assertEqual(rel.virgula_decimal, 2)
        self.assertEqual(rel.ausentes_codigo, 1)
        self.assertEqual(rel.registros_finais, 4)

    def test_erro_informa_a_linha(self):
        texto = "estacao,data,chuva_mm\nA,2024-01-01,1.0\nA,2024-01-02,muito\n"
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(ValueError) as ctx:
                q.ler_chuva(self.escrever(pasta, texto))
        self.assertIn("linha 3", str(ctx.exception))

    def test_data_invalida_levanta_erro(self):
        texto = "estacao,data,chuva_mm\nA,01/02/2024,1.0\n"
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(ValueError):
                q.ler_chuva(self.escrever(pasta, texto))

    def test_coluna_faltando(self):
        with tempfile.TemporaryDirectory() as pasta:
            with self.assertRaises(ValueError) as ctx:
                q.ler_chuva(self.escrever(pasta, "estacao,data\nA,2024-01-01\n"))
        self.assertIn("chuva_mm", str(ctx.exception))


class LerChuvaDadosOficiais(unittest.TestCase):
    """Os dados são sintéticos: sabemos a verdade e onde cada defeito foi plantado."""

    @classmethod
    def setUpClass(cls):
        cls.s = sintetico.gerar()
        cls.registros, cls.rel = q.ler_chuva(CSV)
        cls.achados = {(r.estacao, r.data): r.chuva_mm for r in cls.registros}

    def test_relatorio_bate_com_os_defeitos_plantados(self):
        d, r = self.s.defeitos, self.rel
        self.assertEqual(r.linhas_lidas, len(self.s.linhas))
        self.assertEqual(r.ausentes_codigo, len(d["ausente_codigo"]))
        self.assertEqual(r.ausentes_vazio, len(d["ausente_vazio"]))
        self.assertEqual(r.virgula_decimal, len(d["virgula"]))
        self.assertEqual(r.negativos, len(d["negativo"]))
        self.assertEqual(r.acima_do_limite, len(d["acima_do_limite"]))
        self.assertEqual(r.duplicatas_exatas, len(d["duplicata_exata"]))
        self.assertEqual(r.duplicatas_conflitantes, len(d["duplicata_conflitante"]))
        self.assertEqual(r.registros_finais, len(self.s.verdade) - len(d["linha_ausente"]))

    def test_numeros_citados_no_livro(self):
        # Se algum destes mudar, o texto do capítulo (semana 2) precisa ser revisto.
        r = self.rel
        self.assertEqual(
            (r.linhas_lidas, r.ausentes_codigo, r.ausentes_vazio, r.virgula_decimal, r.negativos),
            (2923, 6, 3, 3, 1),
        )
        self.assertEqual((r.acima_do_limite, r.duplicatas_exatas, r.duplicatas_conflitantes, r.registros_finais), (1, 2, 1, 2920))

    def test_so_existem_registros_nas_datas_esperadas(self):
        sem_linha = set(self.s.defeitos["linha_ausente"])
        self.assertEqual(set(self.achados), set(self.s.verdade) - sem_linha)

    def test_limpeza_recupera_a_verdade_onde_ha_informacao(self):
        d = self.s.defeitos
        sem_medida = set(d["ausente_codigo"]) | set(d["ausente_vazio"]) | set(d["negativo"]) | set(d["acima_do_limite"])
        erradas = [(k, v, self.s.verdade[k]) for k, v in self.achados.items() if k not in sem_medida and v != self.s.verdade[k]]
        self.assertEqual(erradas, [])
        self.assertTrue(all(self.achados[k] is None for k in sem_medida))
        self.assertEqual(sum(v is None for v in self.achados.values()), len(sem_medida))

    def test_duplicata_conflitante_mantem_a_primeira(self):
        chave = self.s.defeitos["duplicata_conflitante"][0]
        self.assertEqual(self.achados[chave], self.s.verdade[chave])
        self.assertGreater(self.s.verdade[chave], 0.0)  # a 2ª linha dizia 0.0; se valesse, o valor mudaria

    def test_datas_ausentes(self):
        for est in ("E01", "E02", "E03", "E04"):
            esperado = sorted(dia for e, dia in self.s.defeitos["linha_ausente"] if e == est)
            with self.subTest(estacao=est):
                self.assertEqual(q.datas_ausentes(self.registros, est), esperado)

    def test_datas_ausentes_com_periodo_explicito_ve_as_pontas(self):
        faltam = q.datas_ausentes(self.registros, "E02", date(2023, 12, 30), date(2024, 1, 2))
        self.assertEqual(faltam, [date(2023, 12, 30), date(2023, 12, 31)])

    def test_estacao_inexistente(self):
        self.assertEqual(q.datas_ausentes(self.registros, "ZZZ"), [])

    def test_o_arquivo_original_nao_foi_alterado_pela_leitura(self):
        antes = CSV.read_bytes()
        q.ler_chuva(CSV)
        self.assertEqual(CSV.read_bytes(), antes)


if __name__ == "__main__":
    unittest.main()
