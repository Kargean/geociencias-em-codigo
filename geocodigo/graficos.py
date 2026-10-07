"""Gráficos de geologia estrutural (matplotlib). A matemática vem de ``estrutural``."""
from __future__ import annotations

import numpy as np

from . import estrutural as est


def _proj(tipo):
    return est.schmidt if tipo == "schmidt" else est.wulff


def rede(ax, tipo="schmidt", cor="0.72", passo=10, rotulos=True):
    """Desenha a rede (grade) do hemisfério inferior: círculo primitivo, grandes círculos de
    planos N-S (meridianos) e pequenos círculos em torno do eixo N-S (paralelos).

    tipo: 'schmidt' (igual área) ou 'wulff' (igual ângulo).
    """
    p = _proj(tipo)
    t = np.linspace(0, 2 * np.pi, 361)
    ax.plot(np.cos(t), np.sin(t), color="0.15", lw=1.4, zorder=2)             # círculo primitivo
    # meridianos: planos de direção N-S com mergulho 'passo'...(90-passo) para E e para W
    for dip in np.arange(passo, 90, passo):
        for direcao in (0.0, 180.0):
            xy = p(est.grande_circulo(direcao, float(dip), 181))
            ax.plot(xy[:, 0], xy[:, 1], color=cor, lw=0.6, zorder=1)
    ax.plot([0, 0], [-1, 1], color=cor, lw=0.6, zorder=1)                      # plano vertical N-S
    # paralelos: linhas a ângulo constante 'alfa' do eixo horizontal Norte
    phi = np.linspace(0, np.pi, 181)
    for alfa in np.radians(np.arange(passo, 180, passo)):
        v = np.stack([np.full_like(phi, np.cos(alfa)),
                      np.sin(alfa) * np.cos(phi),
                      np.sin(alfa) * np.sin(phi)], axis=1)
        xy = p(v)
        ax.plot(xy[:, 0], xy[:, 1], color=cor, lw=0.6, zorder=1)
    ax.plot([-1, 1], [0, 0], color=cor, lw=0.6, zorder=1)
    ax.plot([0], [0], marker="+", color="0.15", ms=7, zorder=3)
    if rotulos:
        for txt, x, y in (("N", 0, 1.07), ("E", 1.07, 0), ("S", 0, -1.09), ("W", -1.09, 0)):
            ax.text(x, y, txt, ha="center", va="center", fontsize=10, color="0.15")
    ax.set_aspect("equal")
    ax.set_xlim(-1.15, 1.15)
    ax.set_ylim(-1.15, 1.15)
    ax.axis("off")
    return ax


def plano_e_polo(ax, direcao, mergulho, tipo="schmidt", cor="C3", rotulo=None):
    """Grande círculo do plano e seu polo (ponto)."""
    p = _proj(tipo)
    g = p(est.grande_circulo(direcao, mergulho, 181))
    ax.plot(g[:, 0], g[:, 1], color=cor, lw=1.8, zorder=4, label=rotulo)
    pol = p(est.normal_do_plano(direcao, mergulho))
    ax.plot(*pol, "o", color=cor, ms=6, mec="k", mew=0.6, zorder=5)
    return g, pol


def bloco_plano(ax, direcao, mergulho, lado=1.0):
    """Plano em 3D (x = Leste, y = Norte, z = para CIMA) com direção, linha de maior declive e polo."""
    s = np.radians(direcao)
    az = np.radians(direcao + 90.0)
    d = np.radians(mergulho)
    u_dir = np.array([np.sin(s), np.cos(s), 0.0])                              # (E, N, Up)
    u_mer = np.array([np.sin(az) * np.cos(d), np.cos(az) * np.cos(d), -np.sin(d)])
    a = np.linspace(-lado, lado, 2)
    b = np.linspace(0, 1.1 * lado, 2)
    A, B = np.meshgrid(a, b)
    X = A * u_dir[0] + B * u_mer[0]
    Y = A * u_dir[1] + B * u_mer[1]
    Z = A * u_dir[2] + B * u_mer[2]
    ax.plot_surface(X, Y, Z, color="tab:orange", alpha=0.35, edgecolor="none")
    # plano horizontal de referência na altura da linha de direção
    ax.plot_surface(np.array([[-lado, lado], [-lado, lado]]), np.array([[-lado, -lado], [lado, lado]]),
                    np.zeros((2, 2)), color="0.6", alpha=0.12, edgecolor="none")
    ax.plot(*zip(-lado * u_dir, lado * u_dir), color="k", lw=2, label="direção (strike)")
    ax.plot(*zip(np.zeros(3), 1.1 * lado * u_mer), color="tab:red", lw=2, label="linha de maior declive")
    n_up = np.cross(u_dir, u_mer)
    n_up *= np.sign(n_up[2]) if n_up[2] != 0 else 1
    ax.quiver(0, 0, 0, *(0.8 * lado * n_up), color="tab:blue", lw=2, arrow_length_ratio=0.15)
    ax.text(*(0.9 * lado * n_up), "normal", color="tab:blue")
    ax.set_xlim(-lado, lado); ax.set_ylim(-lado, lado); ax.set_zlim(-lado, lado)
    ax.set_xlabel("Leste (E)"); ax.set_ylabel("Norte (N)"); ax.set_zlabel("Cima")
    ax.set_xticks([-1, 0, 1]); ax.set_yticks([-1, 0, 1]); ax.set_zticks([-1, 0, 1])
    ax.set_box_aspect((1, 1, 1))
    ax.view_init(elev=24, azim=-58)
    return ax
