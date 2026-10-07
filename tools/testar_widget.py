"""Testa a figura interativa do capítulo no Chromium (Playwright), sem precisar do Quarto.

1. Extrai o bloco ```{=html} do .qmd e o coloca numa página mínima.
2. Confere se não há erros de JavaScript.
3. Compara a matemática do JavaScript com geocodigo.estrutural em 200 planos aleatórios.
4. Move os controles e confere o texto de leitura; salva capturas de tela.

Uso:  python tools/testar_widget.py [capitulo.qmd] [pasta_de_saida]
"""
import re
import sys
import tempfile
from pathlib import Path

import numpy as np
from playwright.sync_api import sync_playwright

raiz = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(raiz))
from geocodigo import estrutural as est  # noqa: E402

qmd = Path(sys.argv[1]) if len(sys.argv) > 1 else raiz / "cap-estrutural-atitudes.qmd"
saida = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(tempfile.mkdtemp())
saida.mkdir(parents=True, exist_ok=True)

texto = qmd.read_text(encoding="utf-8")
blocos = re.findall(r"```\{=html\}\n(.*?)\n```", texto, flags=re.S)
assert len(blocos) == 1, f"esperava 1 bloco html, achei {len(blocos)}"
html = f"<!doctype html><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'><body style='font-family:sans-serif;max-width:900px;margin:auto'>{blocos[0]}</body>"
pag = saida / "widget_teste.html"
pag.write_text(html, encoding="utf-8")

erros = []
rng = np.random.default_rng(7)
with sync_playwright() as p:
    nav = p.chromium.launch()
    for largura, nome in ((1000, "desktop"), (390, "celular")):
        ctx = nav.new_context(viewport={"width": largura, "height": 900})
        page = ctx.new_page()
        page.on("pageerror", lambda e: erros.append(str(e)))
        page.on("console", lambda m: erros.append(m.text) if m.type == "error" else None)
        page.goto(pag.as_uri())
        page.wait_for_function("window.estereoWidget !== undefined")
        if nome == "desktop":
            casos = [(float(rng.uniform(0, 360)), float(rng.uniform(1, 89))) for _ in range(200)]
            res = page.evaluate(
                """(casos) => casos.map(([s, d]) => {
                    const W = window.estereoWidget;
                    return {n: W.normal(s, d), a: W.proj(W.normal(s, d), 'schmidt'), w: W.proj(W.normal(s, d), 'wulff'),
                            c: W.circulo(s, d, 31).map(v => W.proj(v, 'schmidt'))};
                })""", casos)
            maxd = 0.0
            for (s, d), r in zip(casos, res):
                n = est.normal_do_plano(s, d)
                maxd = max(maxd, np.abs(np.array(r["n"]) - n).max(),
                           np.abs(np.array(r["a"]) - est.schmidt(n)).max(),
                           np.abs(np.array(r["w"]) - est.wulff(n)).max(),
                           np.abs(np.array(r["c"]) - est.schmidt(est.grande_circulo(s, d, 31))).max())
            print(f"JS x Python, 200 planos: diferença máxima = {maxd:.2e}")
            assert maxd < 1e-12, "a matemática do JavaScript diverge da do Python"
            # interação: slider, projeção, fixar
            page.fill("#est-dir", "300") if False else page.evaluate(
                "() => {const e=document.getElementById('est-dir'); e.value=300; e.dispatchEvent(new Event('input'));}")
            page.evaluate(
                "() => {const e=document.getElementById('est-mer'); e.value=65; e.dispatchEvent(new Event('input'));}")
            leitura = {k: page.inner_text(f"#est-r-{k}") for k in ("att", "dd", "polo", "xy")}
            print("leitura (300/65):", leitura)
            n = est.normal_do_plano(300, 65)
            xy = est.schmidt(n)
            assert leitura["att"] == "300/65"
            assert leitura["dd"] == "30° (NE)", leitura["dd"]
            assert leitura["polo"] == "210° / 25°", leitura["polo"]
            assert leitura["xy"] == f"({xy[0]:.3f}, {xy[1]:.3f})", (leitura["xy"], xy)
            page.click("#est-fixar")
            page.select_option("#est-tipo", "wulff")
            assert page.evaluate("window.estereoWidget.estado.fixos.length") == 1
            xyw = est.wulff(n)
            assert page.inner_text("#est-r-xy") == f"({xyw[0]:.3f}, {xyw[1]:.3f})"
            page.click("#est-limpar")
            assert page.evaluate("window.estereoWidget.estado.fixos.length") == 0
            page.select_option("#est-tipo", "schmidt")
            page.click("#est-fixar")
            page.evaluate("() => {const e=document.getElementById('est-dir'); e.value=120; e.dispatchEvent(new Event('input'));}")
        # pixels: o canvas não está em branco
        nao_vazio = page.evaluate("""() => {const c=document.getElementById('est-canvas'); const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
            let n=0; for(let i=3;i<d.length;i+=4) if(d[i]>0) n++; return n;}""")
        assert nao_vazio > 5000, "canvas parece vazio"
        # sem rolagem horizontal no celular
        sobra = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        print(f"{nome}: pixels desenhados={nao_vazio}, rolagem horizontal={sobra}px")
        assert sobra <= 0, "há rolagem horizontal"
        page.screenshot(path=str(saida / f"widget_{nome}.png"), full_page=True)
        ctx.close()
    nav.close()

assert not erros, f"erros no navegador: {erros}"
print("Widget OK. Capturas em", saida)
