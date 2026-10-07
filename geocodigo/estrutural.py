"""Geologia estrutural em código: atitudes, vetores, projeção estereográfica.

Convenções (valem para o livro inteiro; confira antes de usar dados de terceiros)
--------------------------------------------------------------------------------
* Ângulos de entrada e saída em GRAUS; azimutes de 0 a 360, no sentido horário a partir do Norte.
* Plano: ``direcao`` (strike) pela REGRA DA MÃO DIREITA, isto é, o plano mergulha
  para a direita de quem olha ao longo da direção. Logo ``dip_dir = direcao + 90``.
* Sistema de coordenadas dos vetores: (N, E, D) = (Norte, Leste, Baixo).
  D > 0 aponta para dentro da Terra. É o sistema de Allmendinger et al. (2012).
* Linha (lineação, eixo de dobra): ``trend`` (azimute) e ``plunge`` (caimento, 0 a 90).
* Projeção: hemisfério INFERIOR; Schmidt (igual área) com raio do círculo primitivo = 1.
"""
from __future__ import annotations

import numpy as np

__all__ = [
    "normal_do_plano", "plano_da_normal", "vetor_da_linha", "linha_do_vetor",
    "schmidt", "wulff", "grande_circulo", "tensor_orientacao", "eixo_dobra",
    "parametros_woodcock", "media_circular", "angulo_entre_eixos",
    "residuo_angular_ao_circulo", "simular_dobra", "para_baixo", "experimento_eixo",
]


# --------------------------------------------------------------------------- #
# 1. Do campo ao vetor
# --------------------------------------------------------------------------- #
def para_baixo(v):
    """Inverte os vetores com componente D < 0 (hemisfério superior -> inferior).

    Dados axiais (planos e eixos) não têm sentido: v e -v são o mesmo objeto.
    """
    v = np.asarray(v, dtype=float)
    return np.where(v[..., 2:3] < 0, -v, v)


def normal_do_plano(direcao, mergulho):
    """Normal unitária que aponta para BAIXO (o 'polo' do plano) em (N, E, D).

    n = (-sen(mergulho)·cos(dip_dir), -sen(mergulho)·sen(dip_dir), cos(mergulho))
    """
    az = np.radians(np.asarray(direcao, dtype=float) + 90.0)  # direção de mergulho
    dp = np.radians(np.asarray(mergulho, dtype=float))
    return np.stack([-np.sin(dp) * np.cos(az), -np.sin(dp) * np.sin(az), np.cos(dp)], axis=-1)


def plano_da_normal(n):
    """Inverso de :func:`normal_do_plano`. Devolve (direcao, mergulho, dip_dir).

    Para plano horizontal a direção é indeterminada; a função devolve dip_dir = 180
    por convenção numérica (atan2(0, 0) = 0), e isso é só um artefato.
    """
    n = para_baixo(n)
    dip_dir = (np.degrees(np.arctan2(n[..., 1], n[..., 0])) + 180.0) % 360.0
    mergulho = np.degrees(np.arccos(np.clip(n[..., 2], -1.0, 1.0)))
    direcao = (dip_dir - 90.0) % 360.0
    return direcao, mergulho, dip_dir


def vetor_da_linha(trend, plunge):
    """Vetor unitário (N, E, D) de uma linha com trend/plunge."""
    t = np.radians(np.asarray(trend, dtype=float))
    p = np.radians(np.asarray(plunge, dtype=float))
    return np.stack([np.cos(p) * np.cos(t), np.cos(p) * np.sin(t), np.sin(p)], axis=-1)


def linha_do_vetor(v):
    """Inverso de :func:`vetor_da_linha`. Devolve (trend, plunge)."""
    v = para_baixo(v)
    trend = np.degrees(np.arctan2(v[..., 1], v[..., 0])) % 360.0
    plunge = np.degrees(np.arcsin(np.clip(v[..., 2], -1.0, 1.0)))
    return trend, plunge


# --------------------------------------------------------------------------- #
# 2. Projeções (hemisfério inferior, círculo primitivo com raio 1)
# --------------------------------------------------------------------------- #
def schmidt(v):
    """Projeção de igual área (Schmidt/Lambert). x = Leste, y = Norte.

    Dedução: com θ = arccos(D) (ângulo a partir da vertical), a projeção de Lambert tem
    r = 2·sen(θ/2) e o círculo primitivo (θ = 90°) fica com raio sqrt(2). Dividindo por sqrt(2):
    r = sqrt(2)·sen(θ/2) = sqrt(1 - D). Como a parte horizontal do vetor é (E, N) com
    módulo sen(θ) = sqrt((1 - D)(1 + D)), obtém-se (x, y) = (E, N) / sqrt(1 + D).
    """
    v = para_baixo(v)
    k = 1.0 / np.sqrt(1.0 + v[..., 2])
    return np.stack([v[..., 1] * k, v[..., 0] * k], axis=-1)


def wulff(v):
    """Projeção de igual ângulo (Wulff/estereográfica). r = tan(θ/2)."""
    v = para_baixo(v)
    k = 1.0 / (1.0 + v[..., 2])
    return np.stack([v[..., 1] * k, v[..., 0] * k], axis=-1)


def grande_circulo(direcao, mergulho, n=181):
    """Vetores (N, E, D) do traço do plano no hemisfério inferior (de direção a direção+180)."""
    s = np.radians(direcao)
    az = np.radians(direcao + 90.0)
    d = np.radians(mergulho)
    v_dir = np.array([np.cos(s), np.sin(s), 0.0])  # horizontal, ao longo da direção
    v_mer = np.array([np.cos(d) * np.cos(az), np.cos(d) * np.sin(az), np.sin(d)])  # linha de maior declive
    phi = np.linspace(0.0, np.pi, n)[:, None]
    return np.cos(phi) * v_dir + np.sin(phi) * v_mer


# --------------------------------------------------------------------------- #
# 3. Estatística de orientações: tensor, eixo de dobra, forma
# --------------------------------------------------------------------------- #
def tensor_orientacao(normais):
    """T = (1/N)·Σ n nᵀ. Não depende do sentido de cada n (n e -n dão o mesmo n nᵀ)."""
    n = np.asarray(normais, dtype=float)
    return n.T @ n / n.shape[0]


def eixo_dobra(normais):
    """Eixo (π) de uma dobra cilíndrica a partir das normais ao acamamento.

    Os polos de uma dobra cilíndrica ficam sobre um grande círculo (guirlanda) cujo
    polo é o eixo da dobra. O eixo é o autovetor de MENOR autovalor do tensor.

    Devolve dict com: eixo (vetor), trend, plunge, autovalores (S1 >= S2 >= S3).
    """
    T = tensor_orientacao(normais)
    w, V = np.linalg.eigh(T)          # autovalores em ordem crescente
    eixo = para_baixo(V[:, 0])
    trend, plunge = linha_do_vetor(eixo)
    return {"eixo": eixo, "trend": float(trend), "plunge": float(plunge),
            "autovalores": w[::-1].copy(), "autovetores": V[:, ::-1].copy()}


def parametros_woodcock(autovalores):
    """K = ln(S1/S2)/ln(S2/S3) (forma) e C = ln(S1/S3) (força). K<1 guirlanda, K>1 aglomerado."""
    s1, s2, s3 = autovalores
    return float(np.log(s1 / s2) / np.log(s2 / s3)), float(np.log(s1 / s3))


def media_circular(azimutes):
    """Média circular de azimutes (graus). A média aritmética falha em torno de 0°/360°."""
    a = np.radians(np.asarray(azimutes, dtype=float))
    media = float(np.degrees(np.arctan2(np.sin(a).mean(), np.cos(a).mean())))
    return round(media, 9) % 360.0     # o round evita 359,9999999 no lugar de 0


def angulo_entre_eixos(v1, v2):
    """Ângulo agudo (graus) entre dois eixos (sem sentido)."""
    c = abs(float(np.dot(v1, v2)) / (np.linalg.norm(v1) * np.linalg.norm(v2)))
    return float(np.degrees(np.arccos(min(1.0, c))))


def residuo_angular_ao_circulo(normais, eixo):
    """Ângulo (graus) entre cada normal e o plano da guirlanda (plano normal ao eixo).

    Se o eixo é bom, os polos estão sobre o grande círculo e o resíduo é ~0.
    Valores grandes denunciam leitura errada, falha ou dobra não cilíndrica.
    """
    n = np.asarray(normais, dtype=float)
    e = np.asarray(eixo, dtype=float) / np.linalg.norm(eixo)
    return np.degrees(np.arcsin(np.clip(np.abs(n @ e), 0.0, 1.0)))


# --------------------------------------------------------------------------- #
# 4. Dobra sintética (a verdade é conhecida -> dá para medir o erro do método)
# --------------------------------------------------------------------------- #
def simular_dobra(eixo_trend, eixo_plunge, n, psi_max, sigma, rng):
    """Normais ao acamamento de uma dobra cilíndrica com eixo conhecido, mais ruído.

    psi ~ U(-psi_max, +psi_max) (graus): posição do polo na guirlanda.
    sigma (graus): desvio-padrão do ruído em cada um dos dois eixos tangentes.
    Devolve normais unitárias (n, 3) apontando para baixo.
    """
    a = vetor_da_linha(eixo_trend, eixo_plunge)
    baixo = np.array([0.0, 0.0, 1.0])
    u = baixo - np.dot(baixo, a) * a
    u /= np.linalg.norm(u)
    w = np.cross(a, u)
    psi = np.radians(rng.uniform(-psi_max, psi_max, n))
    base = np.cos(psi)[:, None] * u + np.sin(psi)[:, None] * w
    # ruído tangente: dois desvios perpendiculares a cada polo
    t1 = np.cross(base, a)
    t1 /= np.linalg.norm(t1, axis=1, keepdims=True)
    t2 = np.cross(base, t1)
    s = np.radians(sigma)
    out = base + (rng.normal(0, s, n)[:, None] * t1 + rng.normal(0, s, n)[:, None] * t2)
    out /= np.linalg.norm(out, axis=1, keepdims=True)
    return para_baixo(out)


def experimento_eixo(psi_max, sigma, n, reps=400, semente=0, eixo=(40.0, 20.0)):
    """Repete 'simular dobra -> estimar eixo' ``reps`` vezes.

    Devolve (erros, K): erro angular (graus) entre o eixo estimado e o verdadeiro, e o
    parâmetro K de Woodcock de cada repetição.
    """
    rng = np.random.default_rng(semente)
    verdadeiro = vetor_da_linha(*eixo)
    erros, ks = np.empty(reps), np.empty(reps)
    for i in range(reps):
        r = eixo_dobra(simular_dobra(eixo[0], eixo[1], n, psi_max, sigma, rng))
        erros[i] = angulo_entre_eixos(r["eixo"], verdadeiro)
        ks[i] = parametros_woodcock(r["autovalores"])[0]
    return erros, ks
