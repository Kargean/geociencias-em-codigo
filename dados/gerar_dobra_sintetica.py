"""Gera dados/dobra_sintetica.csv: 60 medidas de acamamento numa dobra cilíndrica SINTÉTICA.

Verdade (gabarito): eixo da dobra com trend 040° e plunge 20°.
Os dados são inventados para o ensino: a vantagem é que o resultado correto é conhecido
e o erro do método pode ser medido. Para usar dados reais, troque o CSV mantendo as colunas.

Uso:  python dados/gerar_dobra_sintetica.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd

raiz = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(raiz))
from geocodigo import estrutural as est  # noqa: E402

EIXO_TREND, EIXO_PLUNGE = 40.0, 20.0
N, PSI_MAX, SIGMA, SEMENTE = 60, 55.0, 4.0, 42

rng = np.random.default_rng(SEMENTE)
normais = est.simular_dobra(EIXO_TREND, EIXO_PLUNGE, N, PSI_MAX, SIGMA, rng)
direcao, mergulho, _ = est.plano_da_normal(normais)

# precisão de bússola: graus inteiros
df = pd.DataFrame({
    "id": [f"A{i:02d}" for i in range(1, N + 1)],
    "direcao": np.round(direcao).astype(int) % 360,      # strike, regra da mão direita
    "mergulho": np.clip(np.round(mergulho), 1, 89).astype(int),
})
df.to_csv(raiz / "dados" / "dobra_sintetica.csv", index=False)
print(df.head(8).to_string(index=False))
print(f"... {len(df)} linhas gravadas em dados/dobra_sintetica.csv")
