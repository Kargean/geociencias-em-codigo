"""Executa os blocos de código Python de um capítulo .qmd SEM precisar do Quarto.

É um verificador, não um substituto da renderização: confirma que o código roda de ponta a ponta,
na ordem, e guarda cada figura como PNG para você olhar.

Uso:  python tools/executar_codigo_qmd.py cap-estrutural-atitudes.qmd [pasta_de_saida] [--gabaritos]

--gabaritos  executa também os blocos ```python (sem chaves) dos gabaritos, que no livro só são exibidos.
"""
import os
import re
import sys
import tempfile
import time
import traceback
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402

BLOCO = re.compile(r"^```(\{python\}|python)[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)


def extrair(texto, incluir_gabaritos=False):
    """Lista (tipo, codigo, linha_inicial) na ordem do documento."""
    blocos = []
    for m in BLOCO.finditer(texto):
        executavel = m.group(1) == "{python}"
        if executavel or incluir_gabaritos:
            linha = texto[: m.start()].count("\n") + 2
            blocos.append(("livro" if executavel else "gabarito", m.group(2), linha))
    return blocos


def executar(qmd, saida=None, incluir_gabaritos=False, verbose=True):
    qmd = Path(qmd).resolve()
    raiz = qmd.parent
    saida = Path(saida) if saida else Path(tempfile.mkdtemp())
    saida.mkdir(parents=True, exist_ok=True)
    blocos = extrair(qmd.read_text(encoding="utf-8"), incluir_gabaritos)

    ns = {"__name__": "__main__"}
    antes = os.getcwd()
    os.chdir(raiz)
    sys.path.insert(0, str(raiz))
    figuras = []

    def salvar_e_fechar(*a, **k):
        for num in plt.get_fignums():
            caminho = saida / f"fig_{len(figuras) + 1:02d}.png"
            plt.figure(num).savefig(caminho, dpi=100, bbox_inches="tight")
            figuras.append(caminho)
        plt.close("all")

    show_original = plt.show
    plt.show = salvar_e_fechar
    t0 = time.time()
    try:
        for i, (tipo, codigo, linha) in enumerate(blocos, 1):
            try:
                exec(compile(codigo, f"{qmd.name}:linha{linha}", "exec"), ns)
                if verbose:
                    print(f"  ok  bloco {i:02d} ({tipo}, linha {linha})")
            except Exception:
                print(f"ERRO no bloco {i} ({tipo}, linha {linha} de {qmd.name}):")
                traceback.print_exc()
                raise SystemExit(1)
    finally:
        plt.show = show_original
        os.chdir(antes)
    if verbose:
        print(f"{len(blocos)} blocos, {len(figuras)} figuras, {time.time() - t0:.1f}s. PNGs em {saida}")
    ns["_figuras"] = figuras
    return ns


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    executar(args[0], args[1] if len(args) > 1 else None, "--gabaritos" in sys.argv)
