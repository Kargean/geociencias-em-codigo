"""Testes da linha de comando (chuva/cli.py): chamamos main() com uma lista de argumentos e olhamos a saída."""
import contextlib
import io
import tempfile
import unittest
from pathlib import Path

from chuva import cli


def rodar(*argv):
    saida, erro = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(saida), contextlib.redirect_stderr(erro):
        try:
            codigo = cli.main(list(argv))
        except SystemExit as e:  # o argparse sai com SystemExit quando o uso está errado
            codigo = e.code
    return codigo, saida.getvalue(), erro.getvalue()


class Comandos(unittest.TestCase):
    def test_qualidade(self):
        codigo, saida, _ = rodar("qualidade")
        self.assertEqual(codigo, 0)
        self.assertIn("linhas lidas", saida)
        self.assertIn("2923", saida)
        self.assertIn("E04: 3 dia(s) sem linha (2024-08-15, 2024-08-16, 2024-08-17)", saida)

    def test_resumo_todas_as_estacoes(self):
        codigo, saida, _ = rodar("resumo")
        self.assertEqual(codigo, 0)
        self.assertIn("E01      28   2025-04-07", saida)
        self.assertEqual(len(saida.strip().splitlines()), 2 + 4)  # cabeçalho, separador, 4 estações

    def test_resumo_uma_estacao(self):
        codigo, saida, _ = rodar("resumo", "--estacao", "E03")
        self.assertEqual(codigo, 0)
        self.assertIn("E03", saida)
        self.assertNotIn("E01", saida)

    def test_resumo_estacao_desconhecida(self):
        codigo, _, erro = rodar("resumo", "--estacao", "X9")
        self.assertEqual(codigo, 2)
        self.assertIn("X9", erro)

    def test_sql_em_memoria(self):
        codigo, saida, _ = rodar("sql", "05_maior_periodo_seco")
        self.assertEqual(codigo, 0)
        self.assertIn("2025-04-07", saida)

    def test_sql_com_limiar_maior_aumenta_o_periodo_seco(self):
        _, padrao, _ = rodar("sql", "05_maior_periodo_seco")
        _, largo, _ = rodar("sql", "05_maior_periodo_seco", "--limiar", "5")
        self.assertNotEqual(padrao, largo)

    def test_sql_consulta_inexistente(self):
        codigo, _, erro = rodar("sql", "nao_existe")
        self.assertEqual(codigo, 2)
        self.assertIn("não encontrada", erro)

    def test_banco_cria_e_recusa_sobrescrever(self):
        with tempfile.TemporaryDirectory() as pasta:
            destino = str(Path(pasta) / "chuva.db")
            codigo, saida, _ = rodar("banco", "--saida", destino)
            self.assertEqual(codigo, 0)
            self.assertIn("2920 registros", saida)
            codigo2, _, erro = rodar("banco", "--saida", destino)
            self.assertEqual(codigo2, 2)
            self.assertIn("já existe", erro)
            # e o banco criado funciona com o comando sql
            codigo3, saida3, _ = rodar("sql", "01_resumo_estacoes", "--banco", destino)
            self.assertEqual(codigo3, 0)
            self.assertIn("Planície", saida3)

    def test_arquivo_inexistente(self):
        codigo, _, erro = rodar("qualidade", "/nao/existe.csv")
        self.assertEqual(codigo, 1)
        self.assertIn("erro:", erro)

    def test_sem_comando_mostra_uso(self):
        codigo, _, erro = rodar()
        self.assertEqual(codigo, 2)
        self.assertIn("usage", erro.lower())


class Formatacao(unittest.TestCase):
    def test_tabela_alinhada_e_sem_espacos_no_fim(self):
        texto = cli.formatar_tabela(["a", "bb"], [(1, None), (22, "x")])
        self.assertEqual(texto, "a   bb\n--  --\n1\n22  x")


if __name__ == "__main__":
    unittest.main()
