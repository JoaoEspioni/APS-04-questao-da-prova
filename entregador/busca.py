"""Busca do plano ótimo: A* sobre o espaço de estados reduzido (r, c, carregando).

Resumo da modelagem (detalhes e provas em ``docs/modelagem.md``):

* Estado:  (linha, coluna, carregando)  — o pacote está parado na célula
  inicial até ser pego e, depois de entregue, o problema acaba. Por isso a
  posição do pacote não precisa fazer parte do estado: são só 2·n² estados.
* Ações:   4 movimentos (bloqueados = não geram estado novo), PEGAR (só na
  célula do pacote) e ENTREGAR (só na célula de destino; leva ao estado FIM).
* Custo:   1 por ação, +2 se a ação é executada numa célula de pedágio.
* h(s):    distância de Manhattan até o que falta fazer + ações obrigatórias
  (PEGAR e ENTREGAR). Admissível e consistente ⇒ A* devolve plano ótimo.
* Sem solução: detectado por BFS (agente→pacote→destino) antes da busca; a
  própria busca também o detecta, ao esgotar a fronteira.
"""
from __future__ import annotations

import heapq
import itertools
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Optional, Set, Tuple

from .mundo import (
    BAIXO, CIMA, DIREITA, ENTREGAR, ESQUERDA, MOVIMENTOS, PEGAR,
    CUSTO_BASE, SOBRETAXA_PEDAGIO, Estado, Mundo, Pos,
)

FIM = (-1, -1, False)  # estado terminal: pacote entregue no destino


@dataclass
class Resultado:
    existe_solucao: bool
    plano: List[str] = field(default_factory=list)
    custo: Optional[int] = None
    expandidos: int = 0
    gerados: int = 0
    tempo_s: float = 0.0
    algoritmo: str = "astar"
    motivo: str = ""
    motivo_curto: str = ""  # versão curta, para títulos/legendas


# ----------------------------------------------------------------- alcançabilidade
def alcancaveis(mundo: Mundo, origem: Pos) -> Set[Pos]:
    """Células alcançáveis a partir de ``origem`` (BFS, 4-vizinhança, sem obstáculos)."""
    if not mundo.livre(origem):
        return set()
    visto = {origem}
    fila = deque([origem])
    while fila:
        r, c = fila.popleft()
        for dr, dc in MOVIMENTOS.values():
            q = (r + dr, c + dc)
            if q not in visto and mundo.livre(q):
                visto.add(q)
                fila.append(q)
    return visto


def _motivo_inviavel(mundo: Mundo) -> Optional[Tuple[str, str]]:
    """Se o problema é inviável por alcançabilidade, devolve (motivo, motivo curto)."""
    if mundo.pacote not in alcancaveis(mundo, mundo.agente):
        return ("O pacote está isolado do agente: os obstáculos bloqueiam todo "
                "caminho entre a posição inicial do agente e a célula do pacote.",
                "pacote isolado do agente pelos obstáculos")
    if mundo.destino not in alcancaveis(mundo, mundo.pacote):
        return ("O destino é inalcançável a partir do pacote: os obstáculos "
                "bloqueiam todo caminho entre a célula do pacote e o destino.",
                "destino inalcançável a partir do pacote")
    return None


# ----------------------------------------------------------------------- A* / UCS
def _buscar(mundo: Mundo, usar_heuristica: bool):
    n = mundo.n
    obst, ped = mundo.obstaculos, mundo.pedagios
    pac, dst = mundo.pacote, mundo.destino
    d_pac_dst = abs(pac[0] - dst[0]) + abs(pac[1] - dst[1])

    def h(s) -> int:
        if not usar_heuristica or s == FIM:
            return 0
        r, c, carregando = s
        if carregando:  # falta: andar até o destino + ENTREGAR
            return abs(r - dst[0]) + abs(c - dst[1]) + CUSTO_BASE
        # falta: andar até o pacote + PEGAR + andar até o destino + ENTREGAR
        return abs(r - pac[0]) + abs(c - pac[1]) + CUSTO_BASE + d_pac_dst + CUSTO_BASE

    inicio = (mundo.agente[0], mundo.agente[1], False)
    g = {inicio: 0}
    pai = {inicio: (None, None)}
    cont = itertools.count()
    h0 = h(inicio)
    fronteira = [(h0, h0, next(cont), inicio)]  # (f, h, desempate, estado)
    fechados = set()
    expandidos, gerados = 0, 1

    while fronteira:
        _, _, _, s = heapq.heappop(fronteira)
        if s in fechados:
            continue
        if s == FIM:
            plano = []
            atual = FIM
            while atual != inicio:
                anterior, acao = pai[atual]
                plano.append(acao)
                atual = anterior
            plano.reverse()
            return plano, g[FIM], expandidos, gerados
        fechados.add(s)
        expandidos += 1

        r, c, carregando = s
        gs = g[s]
        custo = CUSTO_BASE + (SOBRETAXA_PEDAGIO if (r, c) in ped else 0)

        sucessores = []
        for acao, (dr, dc) in MOVIMENTOS.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < n and 0 <= nc < n and (nr, nc) not in obst:
                sucessores.append(((nr, nc, carregando), acao))
        if not carregando and (r, c) == pac:
            sucessores.append(((r, c, True), PEGAR))
        # Largar o pacote fora do destino nunca ajuda (ver docs/modelagem.md),
        # então ENTREGAR só é considerada no destino, onde leva ao estado FIM.
        if carregando and (r, c) == dst:
            sucessores.append((FIM, ENTREGAR))

        for t, acao in sucessores:
            ng = gs + custo
            if ng < g.get(t, float("inf")):
                g[t] = ng
                pai[t] = (s, acao)
                ht = h(t)
                heapq.heappush(fronteira, (ng + ht, ht, next(cont), t))
                gerados += 1

    return None, None, expandidos, gerados


def resolver(mundo: Mundo, *, algoritmo: str = "astar", verificar_alcancabilidade: bool = True) -> Resultado:
    """Calcula o plano de menor custo, ou informa que não existe solução.

    ``algoritmo``: ``"astar"`` (padrão) ou ``"ucs"`` (custo uniforme, h = 0,
    usado como referência/comparação).
    """
    if algoritmo not in ("astar", "ucs"):
        raise ValueError("algoritmo deve ser 'astar' ou 'ucs'")
    nome = "A*" if algoritmo == "astar" else "custo uniforme"
    t0 = time.perf_counter()

    if mundo.eh_objetivo(mundo.estado_inicial()):
        return Resultado(True, [], 0, 0, 1, time.perf_counter() - t0, algoritmo,
                         "O pacote já está no destino; o plano ótimo é vazio.")

    if verificar_alcancabilidade:
        inviavel = _motivo_inviavel(mundo)
        if inviavel:
            return Resultado(False, [], None, 0, 0, time.perf_counter() - t0, algoritmo, *inviavel)

    plano, custo, exp, ger = _buscar(mundo, algoritmo == "astar")
    dt = time.perf_counter() - t0
    if plano is None:
        return Resultado(False, [], None, exp, ger, dt, algoritmo,
                         "A busca esgotou todos os estados alcançáveis sem conseguir entregar o pacote.",
                         "busca esgotada sem entregar o pacote")
    return Resultado(True, plano, custo, exp, ger, dt, algoritmo, f"Plano ótimo encontrado ({nome}).")


# ------------------------------------------------------------ referência (validação)
def resolver_modelo_completo(mundo: Mundo) -> Optional[Tuple[List[str], int]]:
    """Dijkstra sobre o espaço de estados *completo*, sem nenhuma poda.

    Usa as 6 ações em todo estado (inclusive largar o pacote em qualquer
    célula) e o simulador ``Mundo.aplicar``. É O(n⁴) e serve apenas para
    validar, em grids pequenos, que a modelagem reduzida de ``resolver``
    não perde a solução ótima. Devolve (plano, custo) ou None.
    """
    from .mundo import ACOES

    inicio = mundo.estado_inicial()
    if mundo.eh_objetivo(inicio):
        return [], 0
    g = {inicio: 0}
    pai = {inicio: None}
    cont = itertools.count()
    fronteira = [(0, next(cont), inicio)]
    fechados = set()
    while fronteira:
        gs, _, s = heapq.heappop(fronteira)
        if s in fechados:
            continue
        if mundo.eh_objetivo(s):
            plano = []
            while pai[s] is not None:
                s, acao = pai[s]
                plano.append(acao)
            plano.reverse()
            return plano, gs
        fechados.add(s)
        for acao in ACOES:
            t, c = mundo.aplicar(s, acao)
            if t != s and gs + c < g.get(t, float("inf")):
                g[t] = gs + c
                pai[t] = (s, acao)
                heapq.heappush(fronteira, (gs + c, next(cont), t))
    return None


# ----------------------------------------------------------------------- utilidades
SIMBOLOS = {CIMA: "↑", BAIXO: "↓", ESQUERDA: "←", DIREITA: "→", PEGAR: "[pegar]", ENTREGAR: "[entregar]"}
SIMBOLOS_ASCII = {CIMA: "^", BAIXO: "v", ESQUERDA: "<", DIREITA: ">", PEGAR: "[pegar]", ENTREGAR: "[entregar]"}


def resumir_plano(plano: List[str], ascii_puro: bool = False) -> str:
    """Plano em uma linha, com repetições comprimidas: ``→×3 ↓×2 [pegar] ...``."""
    tab = SIMBOLOS_ASCII if ascii_puro else SIMBOLOS
    partes = []
    i = 0
    while i < len(plano):
        j = i
        while j < len(plano) and plano[j] == plano[i]:
            j += 1
        k = j - i
        partes.append(tab[plano[i]] + (f"x{k}" if ascii_puro and k > 1 else f"×{k}" if k > 1 else ""))
        i = j
    return " ".join(partes) if partes else "(plano vazio)"


def trajeto_do_plano(mundo: Mundo, plano: List[str]) -> List[Pos]:
    """Posições visitadas pelo agente ao executar o plano (sem repetições consecutivas)."""
    sim = mundo.simular(plano)
    out: List[Pos] = []
    for e in sim.estados:
        if not out or out[-1] != e.agente:
            out.append(e.agente)
    return out
