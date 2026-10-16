"""Desenho do mundo em Pygame e exportação para PNG."""
from __future__ import annotations

import os
from typing import List, Optional, Tuple

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame

from .mundo import Mundo, Pos

COR_FUNDO = (255, 255, 255)
COR_GRADE = (35, 40, 50)
COR_OBSTACULO = (20, 20, 20)
COR_PEDAGIO = (185, 188, 198)
COR_ROTA_IDA = (30, 110, 220)
COR_ROTA_ENTREGA = (40, 160, 90)
COR_AGENTE = (24, 90, 115)
COR_AGENTE_CABECA = (150, 225, 240)
COR_PACOTE = (240, 180, 70)
COR_PACOTE_BORDA = (110, 65, 10)
COR_DESTINO = (200, 40, 40)
COR_TEXTO = (25, 35, 55)


def _reduzir(rect: pygame.Rect, fator: float) -> pygame.Rect:
    largura = int(rect.w * fator)
    altura = int(rect.h * fator)
    return pygame.Rect(
        rect.centerx - largura // 2,
        rect.centery - altura // 2,
        largura,
        altura,
    )


def desenhar_agente(superficie: pygame.Surface, rect: pygame.Rect) -> None:
    x, y, largura, altura = rect
    centro_x = x + largura / 2
    espessura = max(2, int(largura * 0.07))
    raio = max(3, int(largura * 0.14))
    centro_cabeca = (centro_x, y + 0.24 * altura)

    pygame.draw.circle(superficie, COR_AGENTE_CABECA, centro_cabeca, raio)
    pygame.draw.circle(superficie, COR_AGENTE, centro_cabeca, raio, espessura)
    pygame.draw.line(superficie, COR_AGENTE, (centro_x, y + 0.38 * altura),
                     (centro_x, y + 0.62 * altura), espessura)
    pygame.draw.line(superficie, COR_AGENTE, (centro_x - 0.22 * largura, y + 0.52 * altura),
                     (centro_x + 0.22 * largura, y + 0.46 * altura), espessura)
    pygame.draw.line(superficie, COR_AGENTE, (centro_x, y + 0.62 * altura),
                     (centro_x - 0.18 * largura, y + 0.86 * altura), espessura)
    pygame.draw.line(superficie, COR_AGENTE, (centro_x, y + 0.62 * altura),
                     (centro_x + 0.18 * largura, y + 0.86 * altura), espessura)


def desenhar_pacote(superficie: pygame.Surface, rect: pygame.Rect) -> None:
    caixa = _reduzir(rect, 0.58)
    espessura = max(1, int(rect.w * 0.04))
    pygame.draw.rect(superficie, COR_PACOTE, caixa)
    dobra = [
        (caixa.left, caixa.top),
        (caixa.right, caixa.top),
        (caixa.centerx, caixa.top + int(caixa.h * 0.45)),
    ]
    pygame.draw.polygon(superficie, (252, 215, 125), dobra)
    pygame.draw.polygon(superficie, COR_PACOTE_BORDA, dobra, espessura)
    pygame.draw.rect(superficie, COR_PACOTE_BORDA, caixa, espessura)


def desenhar_destino(superficie: pygame.Surface, rect: pygame.Rect) -> None:
    marca = _reduzir(rect, 0.6)
    espessura = max(2, int(rect.w * 0.1))
    pygame.draw.line(superficie, COR_DESTINO, marca.topleft, marca.bottomright, espessura)
    pygame.draw.line(superficie, COR_DESTINO, marca.topright, marca.bottomleft, espessura)


def desenhar_grade(
    superficie: pygame.Surface,
    area: pygame.Rect,
    mundo: Mundo,
    *,
    agente: Optional[Pos] = None,
    pacote: Optional[Pos] = None,
    carregando: bool = False,
    trajeto: Optional[List[Tuple[Pos, bool]]] = None,
) -> int:
    """Desenha um mundo e retorna o tamanho em pixels de cada célula."""
    lado = max(4, min(area.w, area.h) // mundo.n)
    origem_x = area.x + (area.w - lado * mundo.n) // 2
    origem_y = area.y + (area.h - lado * mundo.n) // 2
    agente = mundo.agente if agente is None else agente
    pacote = mundo.pacote if pacote is None else pacote

    def celula(posicao: Pos) -> pygame.Rect:
        return pygame.Rect(
            origem_x + posicao[1] * lado,
            origem_y + posicao[0] * lado,
            lado,
            lado,
        )

    grade = pygame.Rect(origem_x, origem_y, lado * mundo.n, lado * mundo.n)
    pygame.draw.rect(superficie, COR_FUNDO, grade)
    for posicao in mundo.obstaculos:
        pygame.draw.rect(superficie, COR_OBSTACULO, celula(posicao))
    for posicao in mundo.pedagios:
        pygame.draw.rect(superficie, COR_PEDAGIO, celula(posicao))

    for indice in range(mundo.n + 1):
        pygame.draw.line(
            superficie, COR_GRADE,
            (origem_x, origem_y + indice * lado),
            (origem_x + mundo.n * lado, origem_y + indice * lado),
        )
        pygame.draw.line(
            superficie, COR_GRADE,
            (origem_x + indice * lado, origem_y),
            (origem_x + indice * lado, origem_y + mundo.n * lado),
        )

    if trajeto and len(trajeto) > 1:
        espessura = max(2, lado // 7)
        for (posicao, carregava), (proxima, _) in zip(trajeto, trajeto[1:]):
            if posicao != proxima:
                cor = COR_ROTA_ENTREGA if carregava else COR_ROTA_IDA
                pygame.draw.line(
                    superficie, cor, celula(posicao).center, celula(proxima).center,
                    espessura,
                )

    desenhar_destino(superficie, celula(mundo.destino))
    if carregando:
        desenhar_agente(superficie, celula(agente))
        atual = celula(agente)
        desenhar_pacote(
            superficie,
            pygame.Rect(atual.centerx, atual.y, atual.w // 2, atual.h // 2),
        )
    else:
        desenhar_pacote(superficie, celula(pacote))
        desenhar_agente(superficie, celula(agente))
    return lado


def exportar_png(
    mundo: Mundo,
    caminho_saida: str,
    *,
    trajeto: Optional[List[Tuple[Pos, bool]]] = None,
    titulo: str = "",
    subtitulo: str = "",
) -> None:
    """Exporta o mundo desenhado para um arquivo PNG."""
    pygame.font.init()
    lado = max(14, min(64, 640 // mundo.n))
    margem, topo, base = 24, 70, 100
    largura_grade = lado * mundo.n
    largura = max(largura_grade + 2 * margem, 760)
    altura = topo + largura_grade + base
    superficie = pygame.Surface((largura, altura))
    superficie.fill(COR_FUNDO)

    fonte_titulo = pygame.font.Font(None, 30)
    fonte_pequena = pygame.font.Font(None, 21)
    if titulo:
        texto = fonte_titulo.render(titulo, True, COR_TEXTO)
        superficie.blit(texto, ((largura - texto.get_width()) // 2, 14))
    if subtitulo:
        texto = fonte_pequena.render(subtitulo, True, (90, 100, 115))
        superficie.blit(texto, ((largura - texto.get_width()) // 2, 44))

    area = pygame.Rect((largura - largura_grade) // 2, topo, largura_grade, largura_grade)
    desenhar_grade(superficie, area, mundo, trajeto=trajeto)
    pygame.image.save(superficie, caminho_saida)
