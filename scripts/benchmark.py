"""Compara A* e busca de custo uniforme (UCS) em mundos aleatórios de vários tamanhos.

    python scripts/benchmark.py

Só mundos *com solução* entram nas médias (os sem solução são contados à parte).
"""
import os
import statistics as st
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from entregador.busca import resolver  # noqa: E402
from entregador.mundo import Mundo  # noqa: E402

TAMANHOS = (10, 20, 30, 40, 50, 60)
SEMENTES = range(100)


def main() -> None:
    print("| N | mundos c/ solução | sem solução | A*: nós expandidos | UCS: nós expandidos | A*: tempo (ms) | UCS: tempo (ms) |")
    print("|---|---|---|---|---|---|---|")
    for n in TAMANHOS:
        ea, eu, ta, tu, sem = [], [], [], [], 0
        for s in SEMENTES:
            m = Mundo.aleatorio(n, s)
            a = resolver(m)
            if not a.existe_solucao:
                sem += 1
                continue
            u = resolver(m, algoritmo="ucs")
            assert a.custo == u.custo, (n, s)
            ea.append(a.expandidos); eu.append(u.expandidos)
            ta.append(a.tempo_s * 1000); tu.append(u.tempo_s * 1000)
        print(f"| {n} | {len(ea)} | {sem} | {st.mean(ea):.0f} | {st.mean(eu):.0f} | {st.mean(ta):.2f} | {st.mean(tu):.2f} |")


if __name__ == "__main__":
    main()
