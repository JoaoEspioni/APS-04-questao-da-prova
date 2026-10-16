"""Modelo do mundo: grid quadrado com obstáculos, pedágios, agente, pacote e destino.

Este módulo contém as *regras do problema* (o "simulador"). O solver em
``busca.py`` é validado contra estas regras: todo plano que ele devolve é
re-executado aqui, ação por ação, para conferir custo e objetivo.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Iterable, List, Optional, Tuple

Pos = Tuple[int, int]  # (linha, coluna); (0, 0) é o canto superior esquerdo

# --- Ações do agente --------------------------------------------------------
CIMA, BAIXO, ESQUERDA, DIREITA = "CIMA", "BAIXO", "ESQUERDA", "DIREITA"
PEGAR, ENTREGAR = "PEGAR", "ENTREGAR"
ACOES = (CIMA, BAIXO, ESQUERDA, DIREITA, PEGAR, ENTREGAR)
MOVIMENTOS = {
    CIMA: (-1, 0),
    BAIXO: (1, 0),
    ESQUERDA: (0, -1),
    DIREITA: (0, 1),
}

# --- Custos -----------------------------------------------------------------
CUSTO_BASE = 1          # todas as ações custam o mesmo...
SOBRETAXA_PEDAGIO = 2   # ...exceto as executadas em célula de pedágio: custo + 2


@dataclass(frozen=True)
class Estado:
    """Estado completo do problema (usado pelo simulador).

    ``pacote`` é a célula onde o pacote está; enquanto o agente o carrega,
    ela acompanha a posição do agente.
    """

    agente: Pos
    pacote: Pos
    carregando: bool


@dataclass
class Simulacao:
    estados: List[Estado]  # estados[0] = inicial; estados[i] = após i ações
    custo: int
    objetivo: bool


@dataclass(frozen=True)
class Mundo:
    n: int
    obstaculos: frozenset
    pedagios: frozenset
    agente: Pos
    pacote: Pos
    destino: Pos
    semente: Optional[int] = None  # só informativo (reprodutibilidade)

    def __post_init__(self) -> None:
        if self.n < 1:
            raise ValueError("a dimensão do grid deve ser >= 1")
        for nome, p in (("agente", self.agente), ("pacote", self.pacote), ("destino", self.destino)):
            if not self.dentro(p):
                raise ValueError(f"{nome} fora do grid: {p}")
            if p in self.obstaculos:
                raise ValueError(f"{nome} não pode estar sobre um obstáculo: {p}")
        for p in self.obstaculos | self.pedagios:
            if not self.dentro(p):
                raise ValueError(f"célula fora do grid: {p}")

    # ------------------------------------------------------------------ regras
    def dentro(self, p: Pos) -> bool:
        return 0 <= p[0] < self.n and 0 <= p[1] < self.n

    def livre(self, p: Pos) -> bool:
        """Célula dentro do grid e sem obstáculo."""
        return self.dentro(p) and p not in self.obstaculos

    def estado_inicial(self) -> Estado:
        return Estado(self.agente, self.pacote, False)

    def eh_objetivo(self, e: Estado) -> bool:
        """Objetivo: o pacote está (solto) na célula de destino."""
        return (not e.carregando) and e.pacote == self.destino

    def custo_acao(self, e: Estado) -> int:
        """Custo de qualquer ação executada com o agente na célula ``e.agente``."""
        extra = SOBRETAXA_PEDAGIO if e.agente in self.pedagios else 0
        return CUSTO_BASE + extra

    def aplicar(self, e: Estado, acao: str) -> Tuple[Estado, int]:
        """Executa uma ação. Devolve (novo estado, custo da ação).

        * Movimento bloqueado (borda ou obstáculo): o agente permanece na
          célula, mas a ação ainda custa.
        * PEGAR só tem efeito se o agente está na célula do pacote.
        * ENTREGAR solta o pacote na célula atual do agente.
        """
        custo = self.custo_acao(e)
        agente, pacote, carregando = e.agente, e.pacote, e.carregando
        if acao in MOVIMENTOS:
            dr, dc = MOVIMENTOS[acao]
            alvo = (agente[0] + dr, agente[1] + dc)
            if self.livre(alvo):
                agente = alvo
                if carregando:
                    pacote = alvo
        elif acao == PEGAR:
            if not carregando and agente == pacote:
                carregando = True
        elif acao == ENTREGAR:
            if carregando:
                carregando = False
                pacote = agente
        else:
            raise ValueError(f"ação desconhecida: {acao!r}")
        return Estado(agente, pacote, carregando), custo

    def simular(self, plano: Iterable[str]) -> Simulacao:
        """Executa um plano do estado inicial, ação por ação."""
        estados = [self.estado_inicial()]
        total = 0
        for acao in plano:
            novo, c = self.aplicar(estados[-1], acao)
            estados.append(novo)
            total += c
        return Simulacao(estados, total, self.eh_objetivo(estados[-1]))

    # --------------------------------------------------------------- geração
    @classmethod
    def aleatorio(
        cls,
        n: int,
        semente: Optional[int] = None,
        *,
        max_obstaculos: float = 0.45,
        max_pedagios: float = 0.20,
    ) -> "Mundo":
        """Gera um mundo aleatório n×n.

        Posições de agente, pacote e destino (três células distintas),
        quantidade e posição dos obstáculos e dos pedágios são sorteadas.
        A fração de obstáculos vai de 0 a ``max_obstaculos`` das células
        restantes; com ~40%+ de obstáculos o grid frequentemente fica
        desconexo, produzindo instâncias *sem solução* (que o solver deve
        reconhecer).
        """
        if n < 2:
            raise ValueError("para gerar um mundo aleatório a dimensão deve ser >= 2")
        if semente is None:
            semente = random.randrange(10**9)
        rng = random.Random(semente)
        celulas = [(r, c) for r in range(n) for c in range(n)]
        agente, pacote, destino = rng.sample(celulas, 3)
        especiais = {agente, pacote, destino}
        restantes = [p for p in celulas if p not in especiais]
        rng.shuffle(restantes)
        k_obst = rng.randint(0, int(max_obstaculos * len(restantes)))
        obstaculos = restantes[:k_obst]
        resto = restantes[k_obst:]
        k_ped = rng.randint(0, int(max_pedagios * len(resto)))
        pedagios = resto[:k_ped]
        return cls(n, frozenset(obstaculos), frozenset(pedagios), agente, pacote, destino, semente)

    # ----------------------------------------------------------------- ASCII
    def para_ascii(self, trajeto: Optional[Iterable[Pos]] = None) -> str:
        """Desenha o mundo em texto.

        ``.`` livre · ``#`` obstáculo · ``~`` pedágio · ``A`` agente ·
        ``P`` pacote · ``X`` destino (minúscula = especial sobre pedágio).
        Com ``trajeto``, marca a rota: ``*`` (livre) e ``+`` (pedágio).
        """
        especiais = {self.agente: "A", self.pacote: "P", self.destino: "X"}
        if len(especiais) < 3:
            raise ValueError("agente, pacote e destino coincidem: não representável em ASCII")
        rota = set(trajeto or [])
        linhas = []
        for r in range(self.n):
            linha = []
            for c in range(self.n):
                p = (r, c)
                if p in especiais:
                    ch = especiais[p]
                    if p in self.pedagios:
                        ch = ch.lower()
                elif p in self.obstaculos:
                    ch = "#"
                elif p in self.pedagios:
                    ch = "+" if p in rota else "~"
                else:
                    ch = "*" if p in rota else "."
                linha.append(ch)
            linhas.append("".join(linha))
        return "\n".join(linhas)

    @classmethod
    def de_ascii(cls, texto: str) -> "Mundo":
        """Lê um mundo no formato de ``para_ascii``.

        Linhas em branco e linhas iniciadas por ``;`` (comentários) são
        ignoradas. ``*`` é lido como livre e ``+`` como pedágio, então a
        saída com rota também pode ser relida.
        """
        linhas = [l.strip() for l in texto.splitlines() if l.strip() and not l.strip().startswith(";")]
        n = len(linhas)
        if n == 0:
            raise ValueError("mundo vazio")
        obst, ped = set(), set()
        pos = {"A": [], "P": [], "X": []}
        for r, linha in enumerate(linhas):
            if len(linha) != n:
                raise ValueError(f"o grid deve ser quadrado: linha {r} tem {len(linha)} colunas, esperado {n}")
            for c, ch in enumerate(linha):
                p = (r, c)
                up = ch.upper()
                if ch in ".*":
                    pass
                elif ch == "#":
                    obst.add(p)
                elif ch in "~+":
                    ped.add(p)
                elif up in pos:
                    pos[up].append(p)
                    if ch.islower():
                        ped.add(p)
                else:
                    raise ValueError(f"caractere inválido {ch!r} em ({r}, {c})")
        for k, nome in (("A", "agente"), ("P", "pacote"), ("X", "destino")):
            if len(pos[k]) != 1:
                raise ValueError(f"esperado exatamente um {nome} ({k}); encontrados {len(pos[k])}")
        return cls(n, frozenset(obst), frozenset(ped), pos["A"][0], pos["P"][0], pos["X"][0])


# Mundo 10×10 da figura do enunciado da prova.
EXEMPLO_PROVA_ASCII = """\
A~.#......
..~#......
...#~~..P.
.......##.
.###....~.
.........~
...~..#...
.~....#...
......#...
.........X
"""
