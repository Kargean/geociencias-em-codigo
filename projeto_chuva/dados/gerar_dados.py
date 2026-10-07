"""Regenera os CSVs de dados sintéticos desta pasta.

Uso (a partir da pasta projeto_chuva):  python dados/gerar_dados.py

Atenção: os CSVs versionados no Git são os DADOS OFICIAIS do projeto. Os testes conferem a soma de
verificação deles (dados/SHA256SUMS). Se você regenerar e os bytes mudarem, o teste vai avisar; é
proposital: dado não muda por acidente. Se a mudança for intencional, atualize o SHA256SUMS no mesmo commit
(python dados/gerar_dados.py --somas) e explique no CHANGELOG.
"""
import hashlib
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ))

from chuva import sintetico  # noqa: E402

ARQUIVOS = ["estacoes.csv", "chuva_diaria.csv"]


def somas(pasta: Path) -> str:
    linhas = []
    for nome in ARQUIVOS:
        h = hashlib.sha256((pasta / nome).read_bytes()).hexdigest()
        linhas.append(f"{h}  {nome}")
    return "\n".join(linhas) + "\n"


if __name__ == "__main__":
    pasta = RAIZ / "dados"
    if "--somas" in sys.argv:
        (pasta / "SHA256SUMS").write_text(somas(pasta), encoding="utf-8", newline="\n")
        print("SHA256SUMS atualizado.")
    else:
        s = sintetico.escrever(pasta)
        print(f"{len(s.linhas)} linhas escritas em {pasta}")
        print("Agora rode:  python dados/gerar_dados.py --somas   (se a mudança for intencional)")
