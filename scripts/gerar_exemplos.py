"""Regera os exemplos de execução em examples/ (texto + PNG).

    python scripts/gerar_exemplos.py

Para cada exemplo gera:
  <nome>.mundo.txt   mundo de entrada (pode ser carregado com `python main.py --arquivo ...`)
  <nome>.saida.txt   relatório da execução (plano ótimo ou "não existe solução")
  <nome>.png         imagem do mundo com a rota
"""
import os
import sys

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # sem monitor
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, RAIZ)

from entregador.busca import resolver  # noqa: E402
from entregador.cli import formatar_relatorio  # noqa: E402
from entregador.desenho import exportar_png  # noqa: E402
from entregador.mundo import EXEMPLO_PROVA_ASCII, Mundo  # noqa: E402

SAIDA = os.path.join(RAIZ, "examples")

# Mundo sem solução desenhado à mão: o pacote (P) está cercado por obstáculos.
SEM_SOLUCAO_MANUAL = """\
A.....#.
......#.
..~~..#.
..~~..##
......#P
.....###
........
.......X
"""


def gerar(nome: str, mundo: Mundo, descricao: str, comando: str) -> None:
    res = resolver(mundo)
    cabecalho = f"; {descricao}\n; Reproduzir: {comando}\n"
    with open(os.path.join(SAIDA, f"{nome}.mundo.txt"), "w", encoding="utf-8") as f:
        f.write(cabecalho + mundo.para_ascii() + "\n")
    with open(os.path.join(SAIDA, f"{nome}.saida.txt"), "w", encoding="utf-8") as f:
        f.write(formatar_relatorio(mundo, res) + "\n")
    trajeto = None
    if res.existe_solucao:
        sim = mundo.simular(res.plano)
        trajeto = [(e.agente, e.carregando) for e in sim.estados]
        titulo = f"Mundo {mundo.n}×{mundo.n} — custo ótimo {res.custo}"
        sub = f"{len(res.plano)} ações · {res.expandidos} nós expandidos ({res.algoritmo})"
    else:
        titulo = f"Mundo {mundo.n}×{mundo.n} — NÃO EXISTE SOLUÇÃO"
        sub = "Motivo: " + res.motivo_curto
    exportar_png(mundo, os.path.join(SAIDA, f"{nome}.png"), trajeto=trajeto, titulo=titulo, subtitulo=sub)
    estado = f"custo {res.custo}, {len(res.plano)} ações" if res.existe_solucao else "sem solução"
    print(f"{nome}: {estado}")


def screenshot_interface() -> None:
    """Captura a janela da GUI (mundo da prova, animação no passo 14) em docs/interface.png."""
    import pygame

    from entregador.interface import App

    app = App(10, 1)
    app.mundo = Mundo.de_ascii(EXEMPLO_PROVA_ASCII)
    app.resolver_atual()
    app.passo(14)
    app.desenhar()
    destino = os.path.join(RAIZ, "docs", "interface.png")
    pygame.image.save(app.tela, destino)
    print("docs/interface.png")


def main() -> None:
    os.makedirs(SAIDA, exist_ok=True)
    gerar("01_exemplo_da_prova_10x10", Mundo.de_ascii(EXEMPLO_PROVA_ASCII),
          "Mundo 10x10 da figura do enunciado da prova.",
          "python main.py --exemplo-prova --png saida.png")
    gerar("02_aleatorio_20x20_semente79", Mundo.aleatorio(20, 79),
          "Mundo aleatório 20x20 (semente 79).",
          "python main.py --cli -n 20 -s 79 --png saida.png")
    gerar("03_aleatorio_40x40_semente5", Mundo.aleatorio(40, 5),
          "Mundo aleatório 40x40 (semente 5).",
          "python main.py --cli -n 40 -s 5 --png saida.png")
    gerar("04_sem_solucao_manual_8x8", Mundo.de_ascii(SEM_SOLUCAO_MANUAL),
          "Mundo 8x8 sem solução: o pacote está cercado por obstáculos.",
          "python main.py --arquivo examples/04_sem_solucao_manual_8x8.mundo.txt --png saida.png")
    gerar("05_sem_solucao_aleatorio_12x12_semente10", Mundo.aleatorio(12, 10),
          "Mundo aleatório 12x12 (semente 10) que não tem solução.",
          "python main.py --cli -n 12 -s 10 --png saida.png")
    screenshot_interface()


if __name__ == "__main__":
    main()
