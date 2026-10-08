"""Laboratório de Git para os capítulos do módulo P0-00.

Cria repositórios DESCARTÁVEIS numa pasta temporária, roda comandos Git de verdade e mostra o resultado
como se fosse o terminal. Assim o livro exibe saídas reais (não coladas à mão) e você pode repetir tudo
sem risco para os seus próprios repositórios.

Isolamento: o laboratório usa um arquivo de configuração global PRÓPRIO (dentro da pasta temporária),
então `git config --global ...` aqui NÃO mexe no seu ~/.gitconfig. As datas dos commits são fixas e
crescentes, o que torna os identificadores (hashes) repetíveis.

A saída do Git é forçada para inglês (LC_ALL=C) para ficar igual em qualquer máquina. No seu computador,
se o Git estiver traduzido, as mensagens virão em português; os comandos são os mesmos.
"""
from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

FUSO = timezone(timedelta(hours=-3))
INICIO = datetime(2025, 1, 6, 9, 0, 0, tzinfo=FUSO)


class ErroDeComando(RuntimeError):
    pass


class Saida(str):
    """Texto devolvido pelos comandos do laboratório.

    Quando o comando é exibido (mostrar=True), a saída já foi impressa na tela. Num notebook ou no Quarto, o
    valor da ÚLTIMA linha de um bloco é exibido de novo; este texto avisa que não precisa (método abaixo).
    Fora do notebook, `Saida` é um `str` comum: dá para usar `.split()`, `in`, `int(...)`, `==` etc.
    """

    def _ipython_display_(self) -> None:
        return None


class Laboratorio:
    """Uma pasta temporária com um 'terminal' que roda git e imprime comando + saída."""

    def __init__(self, identidade: bool = False) -> None:
        """identidade=True já configura nome, e-mail e a ramificação inicial 'main' (em silêncio)."""
        self.base = Path(tempfile.mkdtemp(prefix="lab-git-"))
        self.home = self.base / "home"
        self.home.mkdir()
        self.cwd = self.base
        self._passo = 0
        if identidade:
            self.git('config --global user.name "Seu Nome"', mostrar=False)
            self.git('config --global user.email "seu.email@exemplo.com"', mostrar=False)
            self.git("config --global init.defaultBranch main", mostrar=False)

    # -- ambiente ---------------------------------------------------------------------------------
    def _env(self) -> dict[str, str]:
        quando = (INICIO + timedelta(minutes=7 * self._passo)).strftime("%Y-%m-%dT%H:%M:%S%z")
        env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.home),
            "GIT_CONFIG_GLOBAL": str(self.home / ".gitconfig"),
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_PAGER": "cat",
            "GIT_EDITOR": "true",
            "GIT_AUTHOR_DATE": quando,
            "GIT_COMMITTER_DATE": quando,
            "LC_ALL": "C",
            "LANG": "C",
        }
        # No Windows, um `env` próprio precisa incluir SystemRoot (documentação do `subprocess`); TEMP, TMP,
        # COMSPEC e PATHEXT evitam falhas em programas do Git. Em Linux e macOS essas variáveis não existem
        # (ou são inofensivas). Nunca copiamos HOME, USERPROFILE nem APPDATA: o laboratório fica isolado.
        for chave in ("SYSTEMROOT", "TEMP", "TMP", "COMSPEC", "PATHEXT"):
            if chave in os.environ:
                env[chave] = os.environ[chave]
        return env

    def cd(self, pasta: str = "") -> Path:
        """Muda a 'pasta atual' do laboratório (relativa à base). Cria a pasta se não existir."""
        destino = (self.base / pasta).resolve()
        destino.mkdir(parents=True, exist_ok=True)
        self.cwd = destino
        return destino

    # -- execução ---------------------------------------------------------------------------------
    def rodar(self, comando: str, mostrar: bool = True, ok: bool = True) -> Saida:
        """Executa um comando (sem pipes nem redirecionamentos). Imprime '$ comando' e a saída.

        ok=False aceita que o comando falhe (ex.: um merge com conflito) e mostra a saída mesmo assim.
        Devolve a saída (stdout + stderr juntos, na ordem em que o Git os emitiu).
        """
        self._passo += 1
        proc = subprocess.run(
            shlex.split(comando),
            cwd=self.cwd,
            env=self._env(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )
        saida = proc.stdout.decode("utf-8", errors="replace").replace("\r\n", "\n")
        if "\r" in saida:  # barras de progresso do Git reescrevem a linha com \r; no papel, cada passo vira uma linha
            saida = "\n".join(parte.rstrip() for parte in saida.split("\r") if parte.strip())
        saida = saida.rstrip("\n").replace(f"{self.base}/github/", "https://github.com/")
        saida = saida.replace(str(self.base), "/home/voce")
        if mostrar:
            print(f"$ {comando}")
            if saida:
                print(saida)
        if ok and proc.returncode != 0:
            raise ErroDeComando(f"comando falhou ({proc.returncode}): {comando}\n{saida}")
        return Saida(saida)

    def git(self, argumentos: str, mostrar: bool = True, ok: bool = True) -> Saida:
        return self.rodar(f"git {argumentos}", mostrar=mostrar, ok=ok)

    def criar_github(self, usuario: str, repositorio: str) -> str:
        """Cria um 'GitHub de mentirinha': um repositório 'bare' numa pasta local.

        Um repositório bare é só a história, sem pasta de trabalho (é o que um servidor guarda).
        O Git é configurado para trocar o prefixo https://github.com/ por essa pasta, então você digita
        (e o livro mostra) exatamente os endereços reais. A única mudança na saída é o contrário: o
        endereço local que o Git imprime é trocado de volta por https://github.com/ ao exibir.
        """
        pasta = self.base / "github" / usuario
        pasta.mkdir(parents=True, exist_ok=True)
        antes = self.cwd
        self.cwd = pasta
        self.git(f"init --bare -b main {repositorio}.git", mostrar=False)
        self.git(f'config --global url."{self.base}/github/".insteadOf https://github.com/', mostrar=False)
        self.cwd = antes
        return f"https://github.com/{usuario}/{repositorio}.git"

    # -- arquivos (no lugar do editor de texto) -----------------------------------------------------
    def escrever(self, caminho: str, texto: str, mostrar: bool = True) -> None:
        """Grava um arquivo (o papel do editor de texto). Com mostrar=True, imprime o que foi gravado."""
        arquivo = self.cwd / caminho
        arquivo.parent.mkdir(parents=True, exist_ok=True)
        arquivo.write_text(texto, encoding="utf-8", newline="\n")
        if mostrar:
            print(f"# (no editor) {caminho}")
            print(texto.rstrip("\n"))

    def ler(self, caminho: str) -> str:
        return (self.cwd / caminho).read_text(encoding="utf-8")

    def mostrar_arquivo(self, caminho: str) -> None:
        print(f"$ cat {caminho}")
        print(self.ler(caminho).rstrip("\n"))

    def limpar(self) -> None:
        shutil.rmtree(self.base, ignore_errors=True)


def git_disponivel() -> bool:
    return shutil.which("git") is not None


def figura_fluxo_git():
    """Desenha as quatro 'áreas' do Git e os comandos que levam as mudanças de uma para outra."""
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

    fig, ax = plt.subplots(figsize=(10.4, 4.2))
    ax.set_xlim(0, 14.8)
    ax.set_ylim(-0.7, 5.4)
    ax.axis("off")
    largura, xs = 2.4, [0.2, 4.2, 8.2, 12.2]
    caixas = [
        ("Pasta de trabalho", "os arquivos que\nvocê edita", "#fdf2d9"),
        ("Área de preparação", "(stage) o que entra\nno próximo commit", "#e3f0fb"),
        ("Repositório local", "a história (pasta .git)\nno seu computador", "#e5f5e8"),
        ("Remoto", "a cópia no GitHub\n(chamada origin)", "#f1e6f7"),
    ]
    for x, (titulo, sub, cor) in zip(xs, caixas):
        ax.add_patch(FancyBboxPatch((x, 2.0), largura, 1.7, boxstyle="round,pad=0.05,rounding_size=0.15", fc=cor, ec="#556", lw=1.2))
        ax.text(x + largura / 2, 3.2, titulo, ha="center", va="center", fontsize=10, fontweight="bold")
        ax.text(x + largura / 2, 2.55, sub, ha="center", va="center", fontsize=8.4, color="#333")

    azul, vermelho = "#1b5e9e", "#a33"
    frente = ["git add", "git commit", "git push"]
    volta = ["git restore", "git restore\n--staged", "git fetch"]
    for k in range(3):
        x0, x1 = xs[k] + largura + 0.08, xs[k + 1] - 0.08
        ax.add_patch(FancyArrowPatch((x0, 3.25), (x1, 3.25), arrowstyle="-|>", mutation_scale=15, color=azul, lw=1.8))
        ax.text((x0 + x1) / 2, 3.42, frente[k], ha="center", va="bottom", fontsize=8.6, family="monospace", color=azul)
        ax.add_patch(FancyArrowPatch((x1, 2.45), (x0, 2.45), arrowstyle="-|>", mutation_scale=15, color=vermelho, lw=1.8))
        ax.text((x0 + x1) / 2, 2.28, volta[k], ha="center", va="top", fontsize=8.2, family="monospace", color=vermelho)

    # git pull: do remoto até a pasta de trabalho, por baixo
    ax.add_patch(FancyArrowPatch((xs[3] + largura / 2, 1.85), (xs[0] + largura / 2, 1.85), arrowstyle="-|>", mutation_scale=15,
                                 color=vermelho, lw=1.8, connectionstyle="arc3,rad=-0.28"))
    ax.text(7.5, -0.45, "git pull  =  git fetch  +  git merge   (traz do remoto e junta no que você tem)", ha="center", fontsize=9, family="monospace", color=vermelho)
    ax.text(7.5, 5.05, "azul: guardar para a frente      vermelho: trazer ou desfazer, para trás", ha="center", fontsize=9, color="#333", style="italic")
    ax.set_title("As quatro áreas do Git e os comandos que levam mudanças de uma para outra", fontsize=10.5, pad=2)
    fig.tight_layout()
    return fig
