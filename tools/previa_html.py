"""Gera uma PRÉVIA estática de um capítulo .qmd (HTML único), sem Quarto.

Executa os blocos Python, embute as figuras e as saídas, converte callouts, referências
cruzadas e equações, e usa o pandoc para produzir o HTML (matemática em MathML, bibliografia
via citeproc). A figura interativa funciona dentro da prévia.

Não é a renderização oficial: a aparência final, a navegação do livro e a numeração vêm do
Quarto (no GitHub). A prévia serve para você VER o capítulo antes de publicar.

Uso:  python tools/previa_html.py cap-estrutural-atitudes.qmd previa.html
Requer: pandoc instalado.
"""
import ast
import base64
import contextlib
import html
import io
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("MPLBACKEND", "Agg")
import matplotlib.pyplot as plt  # noqa: E402

CSS = """
body{font-family:system-ui,-apple-system,"Segoe UI",Roboto,sans-serif;line-height:1.6;max-width:880px;margin:0 auto;padding:1rem 16px 4rem;color:#1d2330;background:#fff}
@media (prefers-color-scheme:dark){body{background:#12151c;color:#e4e7ee}a{color:#8ab4ff}.callout{background:#1b2030!important}code,pre{background:#1b2030!important}}
h1,h2,h3{line-height:1.25;margin-top:2rem}
pre{background:#f5f6f8;padding:.7rem .9rem;border-radius:6px;overflow-x:auto;font-size:.88rem}
code{background:#f0f1f4;padding:.05rem .25rem;border-radius:3px;font-size:.9em}pre code{background:none;padding:0}
div.saida pre{border-left:4px solid #8aa;background:#f9fbfc;margin-top:-.4rem}
figure{margin:1.2rem 0;text-align:center}figure img{max-width:100%;height:auto}figcaption{font-size:.9rem;opacity:.85;text-align:left;margin-top:.4rem}
table{border-collapse:collapse;margin:1rem 0;max-width:100%;display:block;overflow-x:auto}
th,td{border-bottom:1px solid #ccd;padding:.3rem .6rem;text-align:left;vertical-align:top}
.callout,details.callout{border-left:5px solid #4a7bd0;background:#f3f6fc;padding:.6rem 1rem;margin:1.2rem 0;border-radius:4px}
.callout-tip{border-color:#2a9d6f;background:#f1faf6}.callout-warning{border-color:#d08a1c;background:#fdf7ec}
.callout-title,summary{font-weight:700;cursor:default}details summary{cursor:pointer}
.nota-previa{border:1px dashed #999;padding:.5rem .8rem;border-radius:6px;font-size:.88rem;margin-bottom:1.5rem}
header#title-block-header h1.title{margin-top:.5rem}
math{font-size:1.05em}
"""


def _numeracao(texto):
    """Rótulos -> 'Seção 1.2', 'Figura 1.1', ... (o capítulo é o nº 1 nesta prévia)."""
    r, em_cerca, h2, h3, nf, nt, ne, prev_callout = {}, False, 0, 0, 0, 0, 0, False
    linhas = texto.split("\n")
    for i, ln in enumerate(linhas):
        if ln.startswith("```"):
            em_cerca = not em_cerca
            continue
        if em_cerca:
            continue
        m = re.match(r"^(#{2,3}) .*?\{#(sec-[\w-]+)\}\s*$", ln)
        if ln.startswith("## ") and not prev_callout:
            h2 += 1; h3 = 0
            if m: r[m.group(2)] = f"Seção 1.{h2}"
        elif ln.startswith("### "):
            h3 += 1
            if m: r[m.group(2)] = f"Seção 1.{h2}.{h3}"
        if ln.strip():
            prev_callout = ln.startswith("::: {.callout")
        for m in re.finditer(r"\{#(tbl-[\w-]+)\}", ln):
            nt += 1; r[m.group(1)] = f"Tabela 1.{nt}"
        for m in re.finditer(r"\$\$ *\{#(eq-[\w-]+)\}", ln):
            ne += 1; r[m.group(1)] = f"Equação 1.{ne}"
    for m in re.finditer(r"^#\| label: (fig-[\w-]+)", texto, flags=re.M):
        nf += 1; r[m.group(1)] = f"Figura 1.{nf}"
    return r


def _rotulos_externos(raiz, atual):
    """Rótulos de seção definidos em OUTROS capítulos da pasta -> texto 'seção «T» do capítulo «C»'.

    No livro de verdade o Quarto resolve essas referências com links e números; na prévia de um capítulo
    isolado só dá para dizer onde elas apontam.
    """
    externos = {}
    for outro in sorted(raiz.glob("*.qmd")):
        if outro.resolve() == atual.resolve():
            continue
        capitulo, em_cerca = outro.stem, False
        for ln in outro.read_text(encoding="utf-8").split("\n"):
            if ln.startswith("```"):
                em_cerca = not em_cerca
            if em_cerca:
                continue
            m = re.match(r"^(#{1,3}) (.*?)\s*\{#(sec-[\w-]+)\}\s*$", ln)
            if not m:
                continue
            titulo = m.group(2).strip()
            if len(m.group(1)) == 1:
                capitulo = titulo
                externos[m.group(3)] = f"o capítulo «{titulo}»"
            else:
                externos[m.group(3)] = f"a seção «{titulo}» do capítulo «{capitulo}»"
    return externos


def _executar(texto, raiz, rot):
    """Substitui cada bloco ```{python} por código + saída + figuras (HTML bruto)."""
    ns = {"__name__": "__main__"}
    blocos = re.compile(r"^```\{python\}[ \t]*\n(.*?)^```[ \t]*$", re.S | re.M)

    def trata(m):
        bruto = m.group(1)
        opts = dict(re.findall(r"^#\| ([\w-]+): *(.*)$", bruto, flags=re.M))
        codigo = "\n".join(l for l in bruto.split("\n") if not l.startswith("#|")).strip("\n")
        saida = io.StringIO()
        antes = os.getcwd(); os.chdir(raiz)
        try:
            with contextlib.redirect_stdout(saida):
                arv = ast.parse(codigo)
                ultima = None
                if arv.body and isinstance(arv.body[-1], ast.Expr):
                    ultima = ast.Expression(arv.body.pop().value)
                exec(compile(arv, "<bloco>", "exec"), ns)
                valor = eval(compile(ultima, "<bloco>", "eval"), ns) if ultima else None
        finally:
            os.chdir(antes)
        if valor is not None and hasattr(valor, "_ipython_display_"):
            valor = None  # o objeto pede para não ser exibido de novo (ex.: saída já impressa pelo laboratório de Git)
        partes = [] if opts.get("echo", "").strip() == "false" else ["```python\n" + codigo + "\n```", ""]   # echo: false esconde o código, como no Quarto
        txt = saida.getvalue().rstrip("\n")
        if txt:
            partes += ["```{=html}", f'<div class="saida"><pre>{html.escape(txt)}</pre></div>', "```", ""]
        if valor is not None:
            h = valor._repr_html_() if hasattr(valor, "_repr_html_") else f"<pre>{html.escape(repr(valor))}</pre>"
            partes += ["```{=html}", f'<div class="saida">{h}</div>', "```", ""]
        for num in plt.get_fignums():
            buf = io.BytesIO()
            plt.figure(num).savefig(buf, format="png", dpi=110, bbox_inches="tight")
            b64 = base64.b64encode(buf.getvalue()).decode()
            rotulo = opts.get("label", "")
            legenda = opts.get("fig-cap", "").strip().strip('"')
            ref = rot.get(rotulo, "Figura")
            partes += ["```{=html}", f'<figure id="{rotulo}"><img src="data:image/png;base64,{b64}" alt="{html.escape(legenda)}">'
                       f"<figcaption><b>{ref}.</b> {html.escape(legenda)}</figcaption></figure>", "```", ""]
        plt.close("all")
        return "\n".join(partes)

    sys.path.insert(0, str(raiz))
    return blocos.sub(trata, texto)


def _callouts(texto):
    out, em_cerca, aberto = [], False, False
    linhas = texto.split("\n")
    i = 0
    while i < len(linhas):
        ln = linhas[i]
        if ln.startswith("```"):
            em_cerca = not em_cerca
        m = re.match(r"^::: \{\.callout-(\w+)(.*)\}\s*$", ln)
        if m and not em_cerca:
            tipo, attrs = m.group(1), m.group(2)
            titulo = ""
            if i + 1 < len(linhas) and linhas[i + 1].startswith("## "):
                titulo = linhas[i + 1][3:].strip(); i += 1
            if 'collapse="true"' in attrs:
                out += [f'<details class="callout callout-{tipo}">', f"<summary>{html.escape(titulo)}</summary>", ""]
                aberto = "details"
            else:
                out += [f'<div class="callout callout-{tipo}">', f'<p class="callout-title">{html.escape(titulo)}</p>' if titulo else "", ""]
                aberto = "div"
        elif ln.strip() == ":::" and aberto and not em_cerca:
            out += ["", "</details>" if aberto == "details" else "</div>", ""]
            aberto = False
        else:
            out.append(ln)
        i += 1
    return "\n".join(out)


def _por_fora_das_cercas(texto, f):
    partes, em, atual = [], False, []
    for ln in texto.split("\n"):
        if ln.startswith("```"):
            if not em:
                partes.append(("txt", "\n".join(atual))); atual = [ln]; em = True
            else:
                atual.append(ln); partes.append(("cod", "\n".join(atual))); atual = []; em = False
            continue
        atual.append(ln)
    partes.append(("cod" if em else "txt", "\n".join(atual)))
    return "\n".join(f(t) if k == "txt" else t for k, t in partes)


def construir(qmd, destino, bib=None):
    qmd = Path(qmd).resolve()
    raiz = qmd.parent
    texto = qmd.read_text(encoding="utf-8")
    rot = _numeracao(texto)
    texto = _executar(texto, raiz, rot)
    texto = _callouts(texto)

    externos = _rotulos_externos(raiz, qmd)

    def resolver(m):
        chave = m.group(1)
        if chave in rot:
            return f"[{rot[chave]}](#{chave})"
        if chave in externos:
            return externos[chave]
        raise KeyError(f"referência sem rótulo em nenhum capítulo: @{chave}")

    def refs(t):
        t = re.sub(r"\n: (.*?) *\{#(tbl-[\w-]+)\}", lambda m: f"\n: **{rot[m.group(2)]}.** {m.group(1)}", t)
        t = re.sub(r"\$\$ *\{#(eq-[\w-]+)\}", lambda m: f"\\qquad\\text{{({rot[m.group(1)].split()[-1]})}} $$", t)
        t = re.sub(r"\s*\{#sec-[\w-]+\}", "", t)
        t = re.sub(r"@((?:fig|tbl|eq|sec)-[\w-]+)", resolver, t)
        return t
    texto = _por_fora_das_cercas(texto, refs)

    tmp = Path(tempfile.mkdtemp())
    (tmp / "entrada.md").write_text(texto, encoding="utf-8")
    (tmp / "estilo.css").write_text(CSS, encoding="utf-8")
    (tmp / "topo.html").write_text(
        '<div class="nota-previa"><b>Prévia estática.</b> Gerada fora do Quarto: código executado de verdade, '
        "figuras e saídas reais, figura interativa funcionando. A aparência final do livro, a busca e a numeração "
        "de capítulos vêm da renderização do Quarto no GitHub.</div>", encoding="utf-8")
    bib = bib or raiz / "references.bib"
    cmd = ["pandoc", str(tmp / "entrada.md"), "-f", "markdown+tex_math_dollars+fenced_divs+raw_html+pipe_tables+smart",
           "-t", "html5", "--standalone", "--embed-resources", "--mathml", "--number-sections", "--toc", "--toc-depth=3",
           "--citeproc", f"--bibliography={bib}", "--metadata", "lang=pt-BR", "--metadata", "pagetitle=Prévia: capítulo",
           "--metadata", "reference-section-title=Referências", "-c", str(tmp / "estilo.css"),
           "-B", str(tmp / "topo.html"), "-o", str(destino)]
    r = subprocess.run(cmd, capture_output=True, text=True, cwd=raiz)
    if r.returncode != 0 or r.stderr.strip():
        print("pandoc:", r.stderr.strip() or "(sem mensagens)")
    if r.returncode != 0:
        raise SystemExit(r.returncode)
    print(f"Prévia gravada em {destino} ({Path(destino).stat().st_size / 1e6:.1f} MB)")


if __name__ == "__main__":
    construir(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "previa.html")
