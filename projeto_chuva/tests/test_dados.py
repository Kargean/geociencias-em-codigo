"""Testes dos dados versionados: eles não podem mudar por acidente."""
import hashlib
import unittest
from pathlib import Path

from chuva import sintetico

RAIZ = Path(__file__).resolve().parents[1]
DADOS = RAIZ / "dados"


class IntegridadeDosArquivos(unittest.TestCase):
    def test_soma_de_verificacao(self):
        # SHA256SUMS guarda a "impressão digital" de cada CSV. Se um byte mudar, a impressão muda.
        # Se a mudança foi intencional: python dados/gerar_dados.py --somas, no MESMO commit, e registre no CHANGELOG.
        for linha in (DADOS / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            esperado, nome = linha.split("  ")
            real = hashlib.sha256((DADOS / nome).read_bytes()).hexdigest()
            with self.subTest(arquivo=nome):
                self.assertEqual(real, esperado, f"{nome} mudou. Foi de propósito? Veja a mensagem no topo deste teste.")

    def test_terminacoes_de_linha_sao_lf(self):
        for nome in ("estacoes.csv", "chuva_diaria.csv"):
            with self.subTest(arquivo=nome):
                self.assertNotIn(b"\r", (DADOS / nome).read_bytes(), "CRLF encontrado; veja o .gitattributes")

    def test_csv_oficial_e_o_que_o_gerador_produz(self):
        s = sintetico.gerar()
        texto = (DADOS / "chuva_diaria.csv").read_text(encoding="utf-8").splitlines()
        self.assertEqual(texto[0], "estacao,data,chuva_mm")
        self.assertEqual(len(texto) - 1, len(s.linhas))


class Gerador(unittest.TestCase):
    def test_mesma_semente_mesmos_dados(self):
        a, b = sintetico.gerar(), sintetico.gerar()
        self.assertEqual(a.verdade, b.verdade)
        self.assertEqual(a.linhas, b.linhas)

    def test_semente_diferente_dados_diferentes(self):
        self.assertNotEqual(sintetico.gerar_verdade(1), sintetico.gerar_verdade(2))

    def test_cobre_todos_os_dias_de_todas_as_estacoes(self):
        v = sintetico.gerar_verdade()
        self.assertEqual(len(v), 4 * 731)  # 2024 é bissexto: 366 + 365 dias

    def test_chuva_plausivel(self):
        v = sintetico.gerar_verdade()
        self.assertTrue(all(0.0 <= x < 300.0 for x in v.values()))
        dias_chuvosos = sum(x >= 1.0 for x in v.values()) / len(v)
        self.assertTrue(0.2 < dias_chuvosos < 0.45, dias_chuvosos)

    def test_verao_mais_chuvoso_que_inverno(self):
        v = sintetico.gerar_verdade()
        verao = sum(x for (e, d), x in v.items() if d.month in (12, 1, 2))
        inverno = sum(x for (e, d), x in v.items() if d.month in (6, 7, 8))
        self.assertGreater(verao, 2 * inverno)

    def test_serra_mais_chuvosa_que_litoral(self):
        v = sintetico.gerar_verdade()
        total = lambda est: sum(x for (e, d), x in v.items() if e == est)
        self.assertGreater(total("E03"), total("E04"))

    def test_defeitos_plantados_nas_quantidades_esperadas(self):
        d = sintetico.gerar().defeitos
        quantidades = {k: len(v) for k, v in d.items()}
        self.assertEqual(
            quantidades,
            {"ausente_codigo": 6, "ausente_vazio": 3, "linha_ausente": 4, "virgula": 3,
             "duplicata_exata": 2, "duplicata_conflitante": 1, "negativo": 1, "acima_do_limite": 1},
        )


if __name__ == "__main__":
    unittest.main()
