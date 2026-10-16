#!/usr/bin/env python3
"""Ponto de entrada.

    python main.py                       # abre a interface gráfica
    python main.py --cli -n 12 -s 42     # linha de comando, mundo aleatório 12x12 (semente 42)
    python main.py --exemplo-prova       # mundo da figura da prova (10x10), na CLI
    python main.py --arquivo examples/sem_solucao_8x8.mundo.txt --png saida.png
"""
import argparse
import sys


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description="APS – Entregador em grid com obstáculos e pedágios")
    p.add_argument("-n", "--tamanho", type=int, default=10, help="dimensão N do grid N×N (padrão: 10)")
    p.add_argument("-s", "--semente", type=int, default=None, help="semente aleatória (reprodutibilidade)")
    p.add_argument("--cli", action="store_true", help="roda na linha de comando em vez de abrir a GUI")
    p.add_argument("--arquivo", help="carrega o mundo de um arquivo ASCII (implica --cli)")
    p.add_argument("--exemplo-prova", action="store_true", help="usa o mundo 10×10 da figura da prova (implica --cli)")
    p.add_argument("--algoritmo", choices=["astar", "ucs"], default="astar", help="astar (padrão) ou ucs")
    p.add_argument("--png", help="salva uma imagem PNG do mundo/rota (implica --cli)")
    a = p.parse_args(argv)

    if a.cli or a.arquivo or a.exemplo_prova or a.png:
        from entregador.cli import rodar

        return rodar(tamanho=a.tamanho, semente=a.semente, arquivo=a.arquivo,
                     exemplo_prova=a.exemplo_prova, algoritmo=a.algoritmo, png=a.png)

    from entregador.interface import executar

    executar(a.tamanho, a.semente, a.algoritmo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
