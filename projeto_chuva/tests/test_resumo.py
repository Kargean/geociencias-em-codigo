"""Testes dos cálculos em Python puro (chuva/resumo.py).

Duas famílias: (1) casos pequenos, resolvidos à mão, onde a resposta correta é óbvia;
(2) os dados oficiais, comparados com a VERDADE sintética.
"""
import unittest
from datetime import date, timedelta
from pathlib import Path

from chuva import qualidade as q
from chuva import resumo as r
from chuva import sintetico
from chuva.qualidade import Registro

RAIZ = Path(__file__).resolve().parents[1]
CSV = RAIZ / "dados" / "chuva_diaria.csv"
D0 = date(2024, 1, 1)


def serie_de(valores, inicio=D0):
    return {inicio + timedelta(days=i): v for i, v in enumerate(valores)}


class TotalMensal(unittest.TestCase):
    def test_mes_incompleto_soma_so_os_validos(self):
        regs = [Registro("A", date(2025, 2, d), v) for d, v in [(1, 10.0), (2, None), (3, 5.5)]]
        m = r.total_mensal(regs)[("A", "2025-02")]
        self.assertEqual((m.total_mm, m.n_validos, m.n_registrados, m.dias_no_mes, m.completo), (15.5, 2, 3, 28, False))

    def test_fevereiro_bissexto_tem_29_dias(self):
        regs = [Registro("A", date(2024, 2, 1), 1.0)]
        self.assertEqual(r.total_mensal(regs)[("A", "2024-02")].dias_no_mes, 29)

    def test_mes_completo(self):
        regs = [Registro("A", D0 + timedelta(days=i), 1.0) for i in range(31)]
        m = r.total_mensal(regs)[("A", "2024-01")]
        self.assertTrue(m.completo)
        self.assertEqual(m.total_mm, 31.0)

    def test_mes_sem_nenhum_dia_valido_tem_total_none_e_nao_zero(self):
        regs = [Registro("A", D0, None), Registro("A", D0 + timedelta(days=1), None)]
        self.assertIsNone(r.total_mensal(regs)[("A", "2024-01")].total_mm)

    def test_soma_de_decimais_nao_acumula_erro_de_ponto_flutuante(self):
        regs = [Registro("A", D0 + timedelta(days=i), 0.1) for i in range(30)]
        self.assertEqual(r.total_mensal(regs)[("A", "2024-01")].total_mm, 3.0)  # sem o round, a soma daria 3.0000000000000013


class DiasDeChuva(unittest.TestCase):
    def test_limiar_e_inclusivo_e_none_nao_conta(self):
        regs = [Registro("A", D0 + timedelta(days=i), v) for i, v in enumerate([0.9, 1.0, 1.1, None, 0.0])]
        self.assertEqual(r.dias_de_chuva(regs), {("A", "2024"): 2})

    def test_ano_sem_chuva_aparece_com_zero(self):
        regs = [Registro("A", D0, 0.0)]
        self.assertEqual(r.dias_de_chuva(regs), {("A", "2024"): 0})

    def test_outro_limiar(self):
        regs = [Registro("A", D0 + timedelta(days=i), v) for i, v in enumerate([5.0, 10.0, 20.0])]
        self.assertEqual(r.dias_de_chuva(regs, limiar=10.0), {("A", "2024"): 2})


class MaiorPeriodoSeco(unittest.TestCase):
    def test_serie_vazia(self):
        self.assertEqual(r.maior_periodo_seco({}), (0, None))

    def test_todos_chuvosos(self):
        self.assertEqual(r.maior_periodo_seco(serie_de([5.0, 6.0])), (0, None))

    def test_tudo_seco(self):
        self.assertEqual(r.maior_periodo_seco(serie_de([0.0, 0.5, 0.9])), (3, D0))

    def test_o_maior_de_varios(self):
        s = serie_de([0.0, 5.0, 0.0, 0.0, 0.0, 5.0, 0.0, 0.0])
        self.assertEqual(r.maior_periodo_seco(s), (3, D0 + timedelta(days=2)))

    def test_empate_vale_o_primeiro(self):
        s = serie_de([0.0, 0.0, 5.0, 0.0, 0.0])
        self.assertEqual(r.maior_periodo_seco(s), (2, D0))

    def test_none_quebra_o_periodo(self):
        s = serie_de([0.0, 0.0, None, 0.0, 0.0])
        self.assertEqual(r.maior_periodo_seco(s)[0], 2)

    def test_data_ausente_quebra_o_periodo(self):
        s = serie_de([0.0, 0.0, 0.0, 0.0])
        del s[D0 + timedelta(days=2)]  # some o terceiro dia (a linha não existe)
        self.assertEqual(r.maior_periodo_seco(s)[0], 2)

    def test_limiar_exato_conta_como_chuvoso(self):
        self.assertEqual(r.maior_periodo_seco(serie_de([0.0, 1.0, 0.0]))[0], 1)


class MaximoAcumulado(unittest.TestCase):
    def test_janela_basica(self):
        self.assertEqual(r.maximo_acumulado(serie_de([1.0, 2.0, 3.0, 4.0, 5.0, 6.0]), janela=3), (15.0, D0 + timedelta(days=5)))

    def test_serie_mais_curta_que_a_janela(self):
        self.assertEqual(r.maximo_acumulado(serie_de([1.0, 2.0]), janela=5), (None, None))

    def test_janela_com_none_e_ignorada(self):
        s = serie_de([50.0, 50.0, None, 1.0, 1.0, 1.0])
        self.assertEqual(r.maximo_acumulado(s, janela=3), (3.0, D0 + timedelta(days=5)))

    def test_data_ausente_nao_vira_zero(self):
        s = serie_de([50.0, 50.0, 0.0, 1.0, 1.0, 1.0])
        del s[D0 + timedelta(days=2)]  # sem o dia 3, nenhuma janela de 3 dias com 50+50 é completa
        self.assertEqual(r.maximo_acumulado(s, janela=3), (3.0, D0 + timedelta(days=5)))

    def test_empate_vale_a_primeira_janela(self):
        s = serie_de([2.0, 2.0, 0.0, 2.0, 2.0])
        self.assertEqual(r.maximo_acumulado(s, janela=2), (4.0, D0 + timedelta(days=1)))


class ContraAVerdadeSintetica(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.s = sintetico.gerar()
        cls.registros, _ = q.ler_chuva(CSV)
        d = cls.s.defeitos
        cls.com_buraco = set(d["ausente_codigo"]) | set(d["ausente_vazio"]) | set(d["negativo"]) | set(d["acima_do_limite"]) | set(d["linha_ausente"])
        cls.meses_incompletos = {(e, f"{dia:%Y-%m}") for e, dia in cls.com_buraco}

    def test_meses_incompletos_sao_exatamente_os_que_tem_defeito(self):
        achados = {chave for chave, m in r.total_mensal(self.registros).items() if not m.completo}
        self.assertEqual(achados, self.meses_incompletos)

    def test_meses_completos_batem_com_a_verdade(self):
        verdade_mes = {}
        for (e, dia), v in self.s.verdade.items():
            chave = (e, f"{dia:%Y-%m}")
            verdade_mes[chave] = verdade_mes.get(chave, 0.0) + v
        diferencas = []
        for chave, m in r.total_mensal(self.registros).items():
            if m.completo and abs(m.total_mm - verdade_mes[chave]) > 0.05:
                diferencas.append((chave, m.total_mm, verdade_mes[chave]))
        self.assertEqual(diferencas, [])

    def test_meses_incompletos_dao_piso_nunca_valor_maior(self):
        verdade_mes = {}
        for (e, dia), v in self.s.verdade.items():
            chave = (e, f"{dia:%Y-%m}")
            verdade_mes[chave] = verdade_mes.get(chave, 0.0) + v
        for chave in self.meses_incompletos:
            with self.subTest(mes=chave):
                self.assertLessEqual(r.total_mensal(self.registros)[chave].total_mm, verdade_mes[chave] + 0.05)

    def test_limpeza_nao_inventa_seca_nem_chuva(self):
        for est in r.estacoes_em(self.registros):
            limpa = r.serie(self.registros, est)
            real = {dia: v for (e, dia), v in self.s.verdade.items() if e == est}
            with self.subTest(estacao=est):
                self.assertLessEqual(r.maior_periodo_seco(limpa)[0], r.maior_periodo_seco(real)[0])
                self.assertLessEqual(r.maximo_acumulado(limpa)[0], r.maximo_acumulado(real)[0])

    def test_numeros_citados_no_livro(self):
        esperado = {
            "E01": (28, date(2025, 4, 7), 207.7, date(2024, 12, 10)),
            "E02": (19, date(2025, 5, 14), 114.1, date(2024, 12, 24)),
            "E03": (14, date(2024, 7, 15), 194.3, date(2025, 1, 16)),
            "E04": (21, date(2025, 8, 11), 105.3, date(2025, 11, 20)),
        }
        for est, (cdd, ini, rx5, fim) in esperado.items():
            s = r.serie(self.registros, est)
            with self.subTest(estacao=est):
                self.assertEqual(r.maior_periodo_seco(s), (cdd, ini))
                self.assertEqual(r.maximo_acumulado(s), (rx5, fim))


if __name__ == "__main__":
    unittest.main()
