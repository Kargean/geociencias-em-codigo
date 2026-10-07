"""Testes do módulo P0-00: os capítulos executam, os números citados no texto conferem e a configuração do GitHub é válida.

Execute:  python tests/test_modulo_p0.py        (leva cerca de 30 s: roda os cinco capítulos de ponta a ponta)

O que este arquivo garante:
  1. todos os blocos de código dos cinco capítulos (e os gabaritos) executam sem erro;
  2. os números que o texto cita são os que o código calcula;
  3. os arquivos de configuração do GitHub (workflows, formulários de issue, Dependabot, CITATION) são válidos;
  4. as cópias do workflow mostradas no livro são lidas dos arquivos reais (e a versão de treino é derivada deles);
  5. todas as referências cruzadas (@sec-..., @fig-...) apontam para algo que existe;
  6. os comandos `gh` e as opções citadas nos capítulos existem na versão instalada (se `gh` estiver instalado);
  7. as afirmações sobre "mutações que sobrevivem" são verdadeiras.
"""
import contextlib
import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))
sys.path.insert(0, str(RAIZ / "tools"))
from executar_codigo_qmd import executar  # noqa: E402

CAPITULOS = [
    "p0-00-visao-geral.qmd",
    "p0-00-semana1-git-local.qmd",
    "p0-00-semana2-python-testes.qmd",
    "p0-00-semana3-github.qmd",
    "p0-00-semana4-sql-ciclo.qmd",
]
TODOS_OS_QMD = sorted(RAIZ.glob("*.qmd"))


def ler(caminho):
    return (RAIZ / caminho).read_text(encoding="utf-8")


def yaml_de(caminho):
    return yaml.safe_load(ler(caminho))


class Capitulos(unittest.TestCase):
    """Executa os cinco capítulos uma vez e guarda o espaço de nomes e a saída de cada um."""

    @classmethod
    def setUpClass(cls):
        cls.ns, cls.saida = {}, {}
        for nome in CAPITULOS:
            buffer = io.StringIO()
            try:
                with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(io.StringIO()):
                    cls.ns[nome] = executar(RAIZ / nome, tempfile.mkdtemp(), incluir_gabaritos=True, verbose=False)
            except SystemExit:
                raise AssertionError(f"{nome}: um bloco de código falhou.\n{buffer.getvalue()[-3000:]}")
            cls.saida[nome] = buffer.getvalue()

    # -- Semana 2 ---------------------------------------------------------------------------------------------
    def test_semana2_numeros_citados(self):
        ns, saida = self.ns["p0-00-semana2-python-testes.qmd"], self.saida["p0-00-semana2-python-testes.qmd"]
        self.assertGreater(ns["n_testes"], 100)  # "Há mais de cem testes"
        self.assertEqual(ns["codigo"], 0)
        self.assertIn("4 de 4 defeitos plantados foram pegos", saida)
        self.assertIn("(None, 'negativo') != (None, 'codigo')", saida)
        self.assertIn("AttributeError: module 'chuva.resumo' has no attribute 'fracao_validos'", saida)
        self.assertEqual((ns["codigo_g"], ns["codigo_v"]), (0, 1))
        self.assertEqual(len(ns["registros"]), 2920)
        self.assertEqual(ns["relatorio"].registros_finais, 2920)

    # -- Semana 3 ---------------------------------------------------------------------------------------------
    def test_semana3_numeros_citados(self):
        ns = self.ns["p0-00-semana3-github.qmd"]
        self.assertEqual(ns["n_pais_merge"], 2)
        self.assertEqual((ns["n_merge"], ns["n_squash"], ns["n_rebase"]), (6, 3, 5))
        self.assertEqual(ns["saida_bisect"].count("running"), 3)           # "Foram três testes para seis commits"
        self.assertIn("is the first bad commit", ns["saida_bisect"])
        self.assertIn("Simplifica a média", ns["saida_bisect"])

    def test_semana3_workflow_embutido_vem_do_arquivo_real(self):
        ns = self.ns["p0-00-semana3-github.qmd"]
        real = ler(".github/workflows/testes.yml")
        self.assertEqual(ns["texto_workflow"], real)
        self.assertIn(ns["bloco_defaults"], real)
        treino = yaml.safe_load(ns["workflow_de_treino"])
        original = yaml.safe_load(real)
        job_t, job_o = treino["jobs"]["testes"], original["jobs"]["testes"]
        self.assertNotIn("defaults", job_t)
        self.assertIn("defaults", job_o)
        self.assertEqual(job_t["steps"], job_o["steps"])
        self.assertEqual(job_t["strategy"], job_o["strategy"])

    # -- Semana 4 ---------------------------------------------------------------------------------------------
    def test_semana4_numeros_citados(self):
        ns = self.ns["p0-00-semana4-sql-ciclo.qmd"]
        self.assertEqual(ns["linhas_banco"], [(2920, 2909, 11)])        # "2 920 linhas ..., 11 delas sem medida"
        self.assertEqual(ns["mensal_e03"], [("E03", "2025-01", 534.2, 31, 31, 31, 1)])
        self.assertEqual(ns["sql_rx5"]["E01"], (207.7, "2024-12-10"))   # "207,7 mm ... 10/12/2024"
        self.assertEqual(ns["sql_rx5"]["E03"], (194.3, "2025-01-16"))   # "194,3 mm até 16/01/2025"
        py_cdd = {est: (v[0], v[1].isoformat()) for est, v in ns["py_cdd"].items()}
        self.assertEqual(ns["sql_cdd"], py_cdd)
        self.assertEqual([l[0] for l in ns["por_texto"]], ["E01", "E02", "E03", "E04"])
        self.assertEqual(ns["por_parametro"], [])


class ConfiguracaoDoGitHub(unittest.TestCase):
    def test_workflow_de_testes(self):
        fluxo = yaml_de(".github/workflows/testes.yml")
        eventos = fluxo.get("on", fluxo.get(True))   # no YAML 1.1, a chave `on` vira o booleano True
        self.assertEqual(set(eventos), {"push", "pull_request", "workflow_dispatch"})
        self.assertEqual(fluxo["permissions"], {"contents": "read"})
        job = fluxo["jobs"]["testes"]
        versoes = job["strategy"]["matrix"]["python"]
        self.assertTrue(all(isinstance(v, str) for v in versoes), "versões do Python precisam estar entre aspas")
        self.assertEqual(versoes, ["3.11", "3.12", "3.13"])
        self.assertEqual(job["defaults"]["run"]["working-directory"], "projeto_chuva")
        comandos = [p["run"] for p in job["steps"] if "run" in p]
        self.assertIn("python -m unittest discover -s tests -v", [c.strip() for c in comandos])
        for passo in job["steps"]:
            if "uses" in passo:
                self.assertRegex(passo["uses"], r"^actions/[\w-]+@v\d+$")
        self.assertTrue((RAIZ / "projeto_chuva" / "tests").is_dir())

    def test_workflow_de_publicacao(self):
        fluxo = yaml_de(".github/workflows/publicar.yml")
        self.assertIn("build", fluxo["jobs"])
        self.assertIn("deploy", fluxo["jobs"])
        comandos = " ".join(p.get("run", "") for p in fluxo["jobs"]["build"]["steps"])
        self.assertIn("quarto render", comandos)
        self.assertIn("unittest discover", comandos)

    def test_formularios_de_issue(self):
        tipos_validos = {"markdown", "input", "textarea", "dropdown", "checkboxes"}
        rotulos = set()
        for arquivo in (RAIZ / ".github" / "ISSUE_TEMPLATE").glob("*.yml"):
            dados = yaml.safe_load(arquivo.read_text(encoding="utf-8"))
            if arquivo.name == "config.yml":
                self.assertIsInstance(dados["blank_issues_enabled"], bool)
                continue
            self.assertTrue({"name", "description", "body"} <= set(dados), arquivo.name)
            ids = [item["id"] for item in dados["body"] if "id" in item]
            self.assertEqual(len(ids), len(set(ids)), f"ids repetidos em {arquivo.name}")
            for item in dados["body"]:
                self.assertIn(item["type"], tipos_validos, arquivo.name)
                if item["type"] != "markdown":
                    self.assertTrue(item["attributes"]["label"], arquivo.name)
                if item["type"] == "dropdown":
                    self.assertTrue(item["attributes"]["options"])
            rotulos |= set(dados.get("labels", []))
        # os rótulos usados pelos formulários são os criados pelos comandos `gh label create` do capítulo
        criados = set(re.findall(r"gh label create (\S+)", ler("p0-00-semana3-github.qmd")))
        self.assertEqual(rotulos, criados)

    def test_dependabot(self):
        dados = yaml_de(".github/dependabot.yml")
        self.assertEqual(dados["version"], 2)
        atualizacao = dados["updates"][0]
        self.assertEqual(atualizacao["package-ecosystem"], "github-actions")
        self.assertIn(atualizacao["schedule"]["interval"], {"daily", "weekly", "monthly"})

    def test_citation(self):
        dados = yaml_de("CITATION.cff")
        for chave in ("cff-version", "message", "title", "authors"):
            self.assertIn(chave, dados)
        self.assertTrue(dados["authors"])
        for autor in dados["authors"]:
            self.assertTrue({"family-names", "given-names"} <= set(autor))

    def test_arquivos_de_apoio(self):
        self.assertIn("Closes #", ler(".github/pull_request_template.md"))
        self.assertIn("* text=auto", ler(".gitattributes"))
        gitignore = ler(".gitignore")
        for padrao in ("__pycache__/", "*.db"):
            self.assertIn(padrao, gitignore)
        self.assertIn("tests/test_modulo_p0.py", ler("CLAUDE.md"))
        self.assertIn("## [Não lançado]", ler("CHANGELOG.md"))


class Estrutura(unittest.TestCase):
    def test_quarto_lista_os_capitulos_na_ordem(self):
        config = yaml_de("_quarto.yml")
        capitulos = []
        for item in config["book"]["chapters"]:
            capitulos += item["chapters"] if isinstance(item, dict) else [item]
        listados = [c for c in capitulos if c.startswith("p0-00-")]
        self.assertEqual(listados, CAPITULOS)
        for c in capitulos:
            self.assertTrue((RAIZ / c).is_file(), c)
        em_disco = sorted(p.name for p in RAIZ.glob("p0-00-*.qmd"))
        self.assertEqual(em_disco, sorted(CAPITULOS))

    def test_referencias_cruzadas(self):
        rotulos, referencias = set(), {}
        for qmd in TODOS_OS_QMD:
            texto = qmd.read_text(encoding="utf-8")
            rotulos |= set(re.findall(r"\{#((?:sec|fig|tbl|eq)-[\w-]+)", texto))
            rotulos |= set(re.findall(r"#\| label: ((?:fig|tbl)-[\w-]+)", texto))
            for ref in re.findall(r"@((?:sec|fig|tbl|eq)-[\w-]+)", texto):
                referencias.setdefault(ref, []).append(qmd.name)
        faltando = {r: arquivos for r, arquivos in referencias.items() if r not in rotulos}
        self.assertEqual(faltando, {})

    def test_rotulos_sem_repeticao(self):
        vistos = {}
        for qmd in TODOS_OS_QMD:
            for r in re.findall(r"\{#((?:sec|fig|tbl|eq)-[\w-]+)", qmd.read_text(encoding="utf-8")):
                self.assertNotIn(r, vistos, f"{r} aparece em {qmd.name} e em {vistos.get(r)}")
                vistos[r] = qmd.name

    def test_gabaritos_existem_nos_capitulos_de_exercicios(self):
        for nome in CAPITULOS[1:]:
            texto = ler(nome)
            for secao in ("Erros clássicos", "Exercícios", "Entregável da semana", "Autoavaliação", "Para ir além"):
                self.assertIn(f"## {secao}", texto, f"{nome}: falta a seção {secao}")
            self.assertGreaterEqual(texto.count("collapse=\"true\""), 3, nome)


@unittest.skipUnless(shutil.which("gh"), "a CLI `gh` não está instalada; os comandos citados não foram conferidos")
class ComandosGh(unittest.TestCase):
    """Cada opção de `gh` escrita num bloco ```bash dos capítulos precisa existir na ajuda do comando."""

    def comandos_citados(self):
        achados = []
        for nome in CAPITULOS:
            for bloco in re.findall(r"```bash\n(.*?)```", ler(nome), re.S):
                junto = re.sub(r"\\\n\s*", " ", bloco)
                for linha in junto.splitlines():
                    linha = re.sub(r"\s+#\s.*$", "", linha).strip()      # tira o comentário (um # seguido de espaço)
                    if linha.startswith("gh "):
                        achados.append(linha)
        return achados

    def test_opcoes_existem(self):
        comandos = self.comandos_citados()
        self.assertGreater(len(comandos), 10)
        for linha in comandos:
            partes = [p for p in re.split(r"\s+", linha) if p]
            grupo = [p for p in partes[1:3] if not p.startswith("-")]
            ajuda = subprocess.run(["gh", *grupo, "--help"], capture_output=True, text=True)
            self.assertEqual(ajuda.returncode, 0, f"comando inexistente: {' '.join(grupo)}  (em: {linha})")
            opcoes = re.findall(r"(?<!\S)(--[a-z][a-z-]*)", " ".join(re.sub(r'"[^"]*"', "", linha).split()))
            for opcao in opcoes:
                self.assertIn(opcao, ajuda.stdout, f"{opcao} não existe em `gh {' '.join(grupo)}`  (em: {linha})")


class MutacoesQueSobrevivem(unittest.TestCase):
    """O texto da Semana 4 afirma que duas mutações em SQL passam pelos testes com os dados oficiais e são pegas pelos casos pequenos."""

    MUTACOES = [
        ("sql/consultas/06_maximo_5_dias.sql", "ORDER BY julianday(data) RANGE BETWEEN 4 PRECEDING", "ORDER BY data ROWS BETWEEN 4 PRECEDING"),
        ("sql/consultas/05_maior_periodo_seco.sql", "WHERE chuva_mm < :limiar", "WHERE chuva_mm <= :limiar"),
    ]

    def rodar(self, arquivo, de, para, alvos):
        pasta = Path(tempfile.mkdtemp(prefix="mutacao-")) / "projeto_chuva"
        shutil.copytree(RAIZ / "projeto_chuva", pasta, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.db"))
        try:
            alvo = pasta / arquivo
            texto = alvo.read_text(encoding="utf-8")
            self.assertIn(de, texto)
            alvo.write_text(texto.replace(de, para), encoding="utf-8")
            return subprocess.run([sys.executable, "-m", "unittest", *alvos], cwd=pasta, capture_output=True, text=True).returncode
        finally:
            shutil.rmtree(pasta.parent, ignore_errors=True)

    def test_sobrevivem_aos_dados_oficiais_e_morrem_na_suite_inteira(self):
        for arquivo, de, para in self.MUTACOES:
            with self.subTest(arquivo=arquivo):
                self.assertEqual(self.rodar(arquivo, de, para, ["tests.test_consistencia.PythonContraSQL"]), 0)
                self.assertNotEqual(self.rodar(arquivo, de, para, ["discover", "-s", "tests"]), 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
