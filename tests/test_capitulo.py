"""Confere se os NÚMEROS CITADOS NO TEXTO do capítulo batem com o que o código calcula.

Roda todos os blocos do capítulo (e dos gabaritos) e compara. Execute:  python tests/test_capitulo.py
Se você mudar a semente, os dados ou o gerador, este teste mostra quais frases do texto ficaram desatualizadas.
"""
import sys
import tempfile
from pathlib import Path

import numpy as np

raiz = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(raiz))
sys.path.insert(0, str(raiz / "tools"))
from executar_codigo_qmd import executar  # noqa: E402
from geocodigo import estrutural as est  # noqa: E402

ns = executar(raiz / "cap-estrutural-atitudes.qmd", tempfile.mkdtemp(), incluir_gabaritos=True, verbose=False)
falhas = []


def confere(descricao, valor, esperado, tol):
    ok = abs(valor - esperado) <= tol
    print(("OK    " if ok else "FALHA ") + f"{descricao}: obtido {valor:.4g}, texto {esperado} (±{tol})")
    if not ok:
        falhas.append(descricao)


def verdade(descricao, cond):
    print(("OK    " if cond else "FALHA ") + descricao)
    if not cond:
        falhas.append(descricao)


# seção 2
confere("convenção trocada: ângulo entre planos (°)", ns["angulo"], 54.1, 0.05)
# seção 4
dens = {nome: (c, b) for nome, c, b in ns["linhas"]}
confere("Schmidt densidade no centro", dens["Schmidt"][0], 1.0, 0.1)
confere("Schmidt densidade na borda", dens["Schmidt"][1], 1.0, 0.1)
confere("Wulff densidade no centro (≈ o dobro)", dens["Wulff"][0], 2.0, 0.15)
confere("Wulff densidade na borda (≈ metade)", dens["Wulff"][1], 0.5, 0.1)
# seção 5
res, resid, n = ns["res"], ns["resid"], ns["n"]
confere("eixo estimado: trend (°)", res["trend"], 40.0, 0.05)
confere("eixo estimado: plunge (°)", res["plunge"], 19.9, 0.05)
for i, v in enumerate((0.7457, 0.2492, 0.0052)):
    confere(f"autovalor S{i + 1}", res["autovalores"][i], v, 0.00006)
confere("erro angular do eixo (°)", est.angulo_entre_eixos(res["eixo"], ns["verdadeiro"]), 0.07, 0.005)
confere("resíduo rms (°)", float(np.sqrt((resid**2).mean())), 4.1, 0.05)
confere("resíduo máximo (°)", float(resid.max()), 11.9, 0.05)
confere("K de Woodcock", ns["K"], 0.28, 0.005)
confere("C de Woodcock", ns["C"], 4.97, 0.005)
confere("comprimento do vetor médio", float(np.linalg.norm(ns["media"])), 0.86, 0.005)
confere("ângulo vetor médio × eixo (°)", est.angulo_entre_eixos(ns["media"] / np.linalg.norm(ns["media"]), res["eixo"]), 90, 0.5)
confere("vetor médio com sentidos misturados", float(np.linalg.norm(ns["n_misto"].mean(axis=0))), 0.04, 0.005)
confere("eixo com sentidos misturados muda (°)", est.angulo_entre_eixos(ns["res_misto"]["eixo"], res["eixo"]), 0.0, 0.005)
# seção 6
psi, K = ns["por_psi"][:, 0], ns["por_psi"][:, 4]
i5, i55 = list(psi).index(5), list(psi).index(55)
confere("ψmax=5: erro mediano (°)", ns["por_psi"][i5, 1], 12, 0.7)
verdade("ψmax=5: percentil 90 do erro passa de 37°", ns["por_psi"][i5, 3] > 37)
confere("ψmax=55: erro mediano (°)", ns["por_psi"][i55, 1], 0.9, 0.1)
verdade("K mediano > 1 para ψmax ≤ 20 e < 1 para ψmax ≥ 30 (alarme em ≈ 25°)",
        all(K[psi <= 20] > 1) and all(K[psi >= 30] < 1))
n_, e_ = ns["por_n"][:, 0], ns["por_n"][:, 1]
confere("N: erro(N=10)/erro(N=40) ≈ 2 (quadruplicar → metade)", e_[list(n_).index(10)] / e_[list(n_).index(40)], 2.0, 0.4)
verdade("σ: erro proporcional ao ruído (σ=8 ≈ 2× σ=4)",
        abs(ns["por_sigma"][list(ns["por_sigma"][:, 0]).index(8), 1] / ns["por_sigma"][list(ns["por_sigma"][:, 0]).index(4), 1] - 2) < 0.2)
# exercício 1
tabela = {"a": ((300, 50), (-0.419, 0.242)), "b": ((210, 55), (-0.213, -0.368)), "c": ((100, 20), (0.799, -0.141))}
for nome, (dd, mm) in ns["planos"].items():
    nn = est.normal_do_plano(dd, mm)
    (tr, pl), xy = tabela[nome]
    t_, p_ = est.linha_do_vetor(nn)
    verdade(f"ex.1 plano {nome}: polo {tr}/{pl} e Schmidt {xy}",
            abs(t_ - tr) < 1e-6 and abs(p_ - pl) < 1e-6 and np.allclose(est.schmidt(nn), xy, atol=5e-4))
# exercício 2
confere("ex.2: erro com 3 outliers (°)", ns["erro_com"], 2.9, 0.05)
confere("ex.2: K com outliers", est.parametros_woodcock(ns["r2"]["autovalores"])[0], 0.41, 0.005)
verdade("ex.2: regra remove exatamente X1, X2, X3", ns["df2"].id[~ns["mantidos"]].tolist() == ["X1", "X2", "X3"])
confere("ex.2: erro depois da remoção (°)", ns["erro_depois"], 0.07, 0.005)
# exercício 3
e3, k3 = ns["erros"], ns["ks"]
confere("ex.3: erro mediano (°)", float(np.median(e3)), 4.4, 0.05)
confere("ex.3: percentil 10 (°)", float(np.percentile(e3, 10)), 1.2, 0.05)
confere("ex.3: percentil 90 (°)", float(np.percentile(e3, 90)), 10.8, 0.05)
confere("ex.3: K mediano", float(np.median(k3)), 3.7, 0.05)
verdade("ex.3: K > 1 em 100% das repetições", bool((k3 > 1).all()))
# exercício 4
confere("ex.4: Schmidt fração r<0,5", float((np.hypot(*est.schmidt(ns["V"]).T) < 0.5).mean()), 0.25, 0.003)
confere("ex.4: Wulff fração r<0,5", float((np.hypot(*est.wulff(ns["V"]).T) < 0.5).mean()), 0.40, 0.003)
# desafio
ep, ang = ns["erros_par"], ns["angulos"]
confere("desafio: nº de pares", len(ep), 1770, 0)
confere("desafio: erro mediano (°)", float(np.median(ep)), 8.4, 0.05)
confere("desafio: p10 (°)", float(np.percentile(ep, 10)), 2.8, 0.05)
confere("desafio: p90 (°)", float(np.percentile(ep, 90)), 41, 0.5)
confere("desafio: nº de pares com ângulo < 10°", int((ang < 10).sum()), 251, 0)
confere("desafio: nº de pares com ângulo ≥ 30°", int((ang >= 30).sum()), 932, 0)
confere("desafio: mediana (<10°)", float(np.median(ep[ang < 10])), 35, 0.5)
confere("desafio: mediana (≥30°)", float(np.median(ep[ang >= 30])), 5.4, 0.05)

print("\nTodos os números do texto conferem." if not falhas else f"\n{len(falhas)} número(s) do texto não conferem: {falhas}")
sys.exit(1 if falhas else 0)
