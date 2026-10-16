"""Interface de linha de comando (não depende de pygame, exceto para --png)."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import List, Optional

from .busca import Resultado, resolver, resumir_plano, trajeto_do_plano
from .mundo import EXEMPLO_PROVA_ASCII, Mundo


def formatar_relatorio(mundo: Mundo, res: Resultado) -> str:
    """Relatório textual completo de uma execução (usado na CLI e em examples/)."""
    L: List[str] = []
    cab = f"Mundo {mundo.n}x{mundo.n}"
    if mundo.semente is not None:
        cab += f" (semente {mundo.semente})"
    L.append(cab)
    L.append(f"Obstáculos: {len(mundo.obstaculos)} | Pedágios: {len(mundo.pedagios)}")
    L.append("")
    L.append("Legenda: A agente | P pacote | X destino | # obstáculo | ~ pedágio | * rota | + rota em pedágio")
    L.append("")
    L.append("Mundo inicial:")
    L.append(mundo.para_ascii())
    L.append("")
    if res.existe_solucao:
        L.append(f"RESULTADO: {res.motivo}")
        L.append(f"Custo total: {res.custo} | Ações: {len(res.plano)} | "
                 f"Nós expandidos: {res.expandidos} | Nós gerados: {res.gerados} | "
                 f"Tempo: {res.tempo_s * 1000:.2f} ms")
        L.append("")
        L.append("Plano (→ direita, ← esquerda, ↑ cima, ↓ baixo; ×k = repetido k vezes):")
        L.append(resumir_plano(res.plano))
        L.append("")
        L.append("Sequência completa de ações:")
        L.append(", ".join(res.plano) if res.plano else "(vazia)")
        L.append("")
        L.append("Rota sobre o mundo:")
        L.append(mundo.para_ascii(trajeto_do_plano(mundo, res.plano)))
    else:
        L.append("RESULTADO: NÃO EXISTE SOLUÇÃO para este mundo.")
        L.append(f"Motivo: {res.motivo}")
        L.append(f"(nós expandidos: {res.expandidos} | tempo: {res.tempo_s * 1000:.2f} ms)")
    return "\n".join(L)


def rodar(
    *,
    tamanho: int = 10,
    semente: Optional[int] = None,
    arquivo: Optional[str] = None,
    exemplo_prova: bool = False,
    algoritmo: str = "astar",
    png: Optional[str] = None,
) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    try:
        if arquivo:
            mundo = Mundo.de_ascii(Path(arquivo).read_text(encoding="utf-8"))
        elif exemplo_prova:
            mundo = Mundo.de_ascii(EXEMPLO_PROVA_ASCII)
        else:
            mundo = Mundo.aleatorio(tamanho, semente)
    except (OSError, ValueError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 2

    res = resolver(mundo, algoritmo=algoritmo)
    print(formatar_relatorio(mundo, res))

    if png:
        from .desenho import exportar_png

        trajeto = None
        if res.existe_solucao:
            sim = mundo.simular(res.plano)
            trajeto = [(e.agente, e.carregando) for e in sim.estados]
            titulo = f"Mundo {mundo.n}×{mundo.n} — custo ótimo {res.custo}"
            sub = f"{len(res.plano)} ações · {res.expandidos} nós expandidos ({res.algoritmo})"
        else:
            titulo = f"Mundo {mundo.n}×{mundo.n} — NÃO EXISTE SOLUÇÃO"
            sub = "Motivo: " + res.motivo_curto
        exportar_png(mundo, png, trajeto=trajeto, titulo=titulo, subtitulo=sub)
        print(f"\nImagem salva em {png}")
    return 0
