"""Testes de geocodigo.estrutural. Execute:  python tests/test_estrutural.py
(não precisa de pytest; cada função test_* é chamada e um relatório é impresso)."""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from geocodigo import estrutural as est  # noqa: E402

rng = np.random.default_rng(1)


def test_casos_conhecidos():
    # horizontal -> polo vertical para baixo
    assert np.allclose(est.normal_do_plano(123, 0), [0, 0, 1])
    # direção 0, mergulho 90 (mergulha para Leste pela mão direita) -> polo aponta para Oeste
    assert np.allclose(est.normal_do_plano(0, 90), [0, -1, 0], atol=1e-12)
    # direção 90 (E-W), mergulho 30 para Sul (dip_dir = 180): polo aponta para Norte e para baixo
    n = est.normal_do_plano(90, 30)
    assert np.allclose(n, [np.sin(np.radians(30)), 0, np.cos(np.radians(30))], atol=1e-12)
    # polo de plano 120/40: trend = dip_dir + 180 = 210+180 = 30, plunge = 90-40 = 50
    trend, plunge = est.linha_do_vetor(est.normal_do_plano(120, 40))
    assert abs(trend - 30) < 1e-9 and abs(plunge - 50) < 1e-9


def test_ida_e_volta_e_ortogonalidade():
    strike = rng.uniform(0, 360, 5000)
    dip = rng.uniform(0.5, 89.5, 5000)
    n = est.normal_do_plano(strike, dip)
    assert np.allclose(np.linalg.norm(n, axis=1), 1)
    assert (n[:, 2] > 0).all()
    s2, d2, _ = est.plano_da_normal(n)
    assert np.allclose(((s2 - strike + 180) % 360) - 180, 0, atol=1e-8)
    assert np.allclose(d2, dip, atol=1e-8)
    # n é ortogonal à direção e à linha de maior declive
    s = np.radians(strike)
    az = np.radians(strike + 90)
    d = np.radians(dip)
    v_dir = np.stack([np.cos(s), np.sin(s), np.zeros_like(s)], axis=1)
    v_mer = np.stack([np.cos(d) * np.cos(az), np.cos(d) * np.sin(az), np.sin(d)], axis=1)
    assert np.allclose((n * v_dir).sum(1), 0, atol=1e-12)
    assert np.allclose((n * v_mer).sum(1), 0, atol=1e-12)


def test_schmidt_pontos_notaveis():
    assert np.allclose(est.schmidt([0, 0, 1]), [0, 0])           # vertical: centro
    assert np.allclose(est.schmidt([1, 0, 0]), [0, 1])           # horizontal para N: topo
    assert np.allclose(est.schmidt([0, 1, 0]), [1, 0])           # horizontal para E: direita
    assert np.allclose(est.schmidt([0, -1, 0]), [-1, 0])         # horizontal para W
    assert np.allclose(est.wulff([1, 0, 0]), [0, 1])
    # linha a 45° da vertical (plunge 45): Schmidt r = sqrt(2)·sen(22,5°); Wulff r = tan(22,5°)
    v = est.vetor_da_linha(90, 45)
    assert abs(np.hypot(*est.schmidt(v)) - np.sqrt(2) * np.sin(np.radians(22.5))) < 1e-12
    assert abs(np.hypot(*est.wulff(v)) - np.tan(np.radians(22.5))) < 1e-12


def _uniforme_no_hemisferio(n):
    v = rng.normal(size=(n, 3))
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    return est.para_baixo(v)


def test_schmidt_conserva_area():
    v = _uniforme_no_hemisferio(400_000)
    r2 = (est.schmidt(v) ** 2).sum(1)
    # Se a área é conservada, r² ~ Uniforme(0,1): média 1/2, variância 1/12
    assert abs(r2.mean() - 0.5) < 0.004
    assert abs(r2.var() - 1 / 12) < 0.004


def test_wulff_distorce_densidade():
    v = _uniforme_no_hemisferio(2_000_000)
    r = np.hypot(*est.wulff(v).T)
    n = len(r)
    dens = lambda a, b: ((r >= a) & (r < b)).sum() / (np.pi * (b**2 - a**2)) / (n / np.pi)
    # relativo à densidade uniforme de Schmidt: ~2x no centro, ~0,5x na borda
    assert abs(dens(0, 0.1) - 2) < 0.08
    assert abs(dens(0.95, 1.0) - 0.5) < 0.08


def test_grande_circulo():
    for strike, dip in [(0, 30), (120, 40), (250, 75), (45, 5), (310, 89)]:
        g = est.grande_circulo(strike, dip, 91)
        n = est.normal_do_plano(strike, dip)
        assert np.allclose(g @ n, 0, atol=1e-12)
        assert (g[:, 2] >= -1e-12).all()
        assert np.allclose(np.linalg.norm(g, axis=1), 1)
        xy = est.schmidt(g)
        assert np.allclose(np.hypot(xy[0, 0], xy[0, 1]), 1) and np.allclose(np.hypot(xy[-1, 0], xy[-1, 1]), 1)
        assert np.hypot(*est.schmidt(n)) <= 1 + 1e-12


def test_eixo_sem_ruido_e_invariancia_de_sinal():
    for trend, plunge in [(40, 20), (200, 5), (310, 60), (0, 0)]:
        n = est.simular_dobra(trend, plunge, 200, 70, 0.0, rng)
        r = est.eixo_dobra(n)
        assert est.angulo_entre_eixos(r["eixo"], est.vetor_da_linha(trend, plunge)) < 1e-6
        # inverter o sentido de metade das normais não muda o resultado (tensor é axial)
        n2 = n.copy()
        n2[::2] *= -1
        r2 = est.eixo_dobra(n2)
        assert est.angulo_entre_eixos(r2["eixo"], r["eixo"]) < 1e-9
        assert r["autovalores"][0] >= r["autovalores"][1] >= r["autovalores"][2] >= -1e-12
        assert abs(r["autovalores"].sum() - 1) < 1e-12


def test_media_circular():
    assert abs(est.media_circular([350, 10]) - 0) < 1e-9 or abs(est.media_circular([350, 10]) - 360) < 1e-9
    assert abs(np.mean([350, 10]) - 180) < 1e-9  # a armadilha
    assert abs(est.media_circular([80, 100]) - 90) < 1e-9


def test_woodcock_guirlanda_vs_aglomerado():
    guir = est.simular_dobra(40, 20, 300, 80, 2.0, rng)
    Kg, Cg = est.parametros_woodcock(est.eixo_dobra(guir)["autovalores"])
    aglo = est.simular_dobra(40, 20, 300, 5, 2.0, rng)
    Ka, Ca = est.parametros_woodcock(est.eixo_dobra(aglo)["autovalores"])
    assert Kg < 1 < Ka  # guirlanda tem K<1; aglomerado tem K>1


if __name__ == "__main__":
    falhas = 0
    for nome, fn in sorted(globals().items()):
        if nome.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"OK    {nome}")
            except AssertionError as e:
                falhas += 1
                print(f"FALHA {nome}: {e!r}")
    print("\nTudo certo." if falhas == 0 else f"\n{falhas} teste(s) falharam.")
    sys.exit(1 if falhas else 0)
