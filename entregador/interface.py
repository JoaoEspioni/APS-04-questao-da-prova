"""Interface gráfica (pygame).

O usuário define a dimensão N do grid; a posição do agente, do pacote e do
destino, e a quantidade e a posição dos obstáculos e pedágios são sorteadas a
cada "Novo mundo". O plano ótimo é calculado na hora e pode ser animado passo
a passo. Quando o mundo sorteado não tem solução, a interface avisa.

Atalhos: N novo mundo · Espaço tocar/pausar · setas esquerda/direita: passo ·
R reiniciar · T mostrar/ocultar rota · A trocar A*/custo uniforme · +/- dimensão · Esc sair.
"""
from __future__ import annotations

import os
import random
from typing import Callable, List, Optional

os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")
import pygame  # noqa: E402

from . import desenho  # noqa: E402
from .busca import Resultado, resolver, resumir_plano  # noqa: E402
from .mundo import Mundo  # noqa: E402

LARGURA, ALTURA = 1040, 700
AREA_GRADE = pygame.Rect(35, 20, 630, 630)
X_PAINEL, L_PAINEL = 700, 320
N_MIN, N_MAX = 2, 60
INTERVALOS_MS = [700, 350, 180, 90, 45, 20]

COR_BOTAO = (232, 236, 244)
COR_BOTAO_HOVER = (214, 222, 238)
COR_BOTAO_OFF = (242, 243, 246)
COR_BORDA = (150, 160, 180)
COR_OK = (30, 130, 70)
COR_ERRO = (190, 35, 35)
COR_CINZA = (100, 110, 125)


class Botao:
    def __init__(self, rect: pygame.Rect, texto: Callable[[], str] | str, ao_clicar: Callable[[], None],
                 ativo: Callable[[], bool] = lambda: True):
        self.rect = rect
        self.texto = texto if callable(texto) else (lambda t=texto: t)
        self.ao_clicar = ao_clicar
        self.ativo = ativo

    def desenhar(self, tela, fonte, mouse) -> None:
        on = self.ativo()
        cor = COR_BOTAO_OFF if not on else (COR_BOTAO_HOVER if self.rect.collidepoint(mouse) else COR_BOTAO)
        pygame.draw.rect(tela, cor, self.rect, border_radius=6)
        pygame.draw.rect(tela, COR_BORDA, self.rect, 1, border_radius=6)
        t = fonte.render(self.texto(), True, desenho.COR_TEXTO if on else (160, 165, 175))
        tela.blit(t, t.get_rect(center=self.rect.center))

    def clique(self, pos) -> bool:
        if self.rect.collidepoint(pos) and self.ativo():
            self.ao_clicar()
            return True
        return False


class App:
    def __init__(self, tamanho: int = 10, semente: Optional[int] = None, algoritmo: str = "astar",
                 tela: Optional[pygame.Surface] = None):
        pygame.init()
        pygame.display.set_caption("APS – Entregador em grid")
        self.tela = tela if tela is not None else pygame.display.set_mode((LARGURA, ALTURA))
        self.f_titulo = pygame.font.Font(None, 34)
        self.f_normal = pygame.font.Font(None, 23)
        self.f_negrito = pygame.font.Font(None, 26)
        self.f_pequena = pygame.font.Font(None, 20)
        self.f_enorme = pygame.font.Font(None, 30)

        self.algoritmo = algoritmo
        self.mostrar_rota = True
        self.vel = 2  # índice em INTERVALOS_MS
        self.tocando = False
        self._ultimo_tick = 0
        self.entrada = str(max(N_MIN, min(N_MAX, tamanho)))
        self.entrada_foco = False

        self.mundo: Mundo
        self.resultado: Resultado
        self.sim = None
        self.acumulado: List[int] = [0]
        self.indice = 0
        self.rodando = True

        y = 190
        w = 156
        self.botoes: List[Botao] = [
            Botao(pygame.Rect(800, 95, 34, 34), "-", lambda: self.ajustar_dimensao(-1)),
            Botao(pygame.Rect(840, 95, 34, 34), "+", lambda: self.ajustar_dimensao(+1)),
            Botao(pygame.Rect(X_PAINEL, 140, L_PAINEL, 40), "Novo mundo aleatório (N)", self.aplicar_entrada),
            Botao(pygame.Rect(X_PAINEL, y, w, 34), lambda: "Pausar" if self.tocando else "Tocar (espaço)",
                  self.alternar_tocar, self.tem_plano),
            Botao(pygame.Rect(X_PAINEL + w + 8, y, w, 34), "Reiniciar (R)", self.reiniciar, self.tem_plano),
            Botao(pygame.Rect(X_PAINEL, y + 42, w, 34), "< Passo", lambda: self.passo(-1), self.tem_plano),
            Botao(pygame.Rect(X_PAINEL + w + 8, y + 42, w, 34), "Passo >", lambda: self.passo(+1), self.tem_plano),
            Botao(pygame.Rect(X_PAINEL, y + 84, w, 34), lambda: f"Rota: {'sim' if self.mostrar_rota else 'não'} (T)",
                  self.alternar_rota),
            Botao(pygame.Rect(X_PAINEL + w + 8, y + 84, w, 34),
                  lambda: f"Algoritmo: {'A*' if self.algoritmo == 'astar' else 'UCS'} (A)", self.alternar_algoritmo),
            Botao(pygame.Rect(X_PAINEL, y + 126, w, 34), "Mais lento", lambda: self.mudar_vel(-1)),
            Botao(pygame.Rect(X_PAINEL + w + 8, y + 126, w, 34), "Mais rápido", lambda: self.mudar_vel(+1)),
        ]
        self.novo_mundo(int(self.entrada), semente)

    # ------------------------------------------------------------------ estado
    def tem_plano(self) -> bool:
        return self.sim is not None

    def novo_mundo(self, n: Optional[int] = None, semente: Optional[int] = None) -> None:
        n = max(N_MIN, min(N_MAX, n if n is not None else int(self.entrada or N_MIN)))
        self.entrada = str(n)
        self.mundo = Mundo.aleatorio(n, semente if semente is not None else random.randrange(10**6))
        self.resolver_atual()

    def resolver_atual(self) -> None:
        self.resultado = resolver(self.mundo, algoritmo=self.algoritmo)
        self.indice = 0
        self.tocando = False
        if self.resultado.existe_solucao:
            self.sim = self.mundo.simular(self.resultado.plano)
            self.acumulado = [0]
            for e_ant, _ in zip(self.sim.estados, self.resultado.plano):
                self.acumulado.append(self.acumulado[-1] + self.mundo.custo_acao(e_ant))
        else:
            self.sim = None
            self.acumulado = [0]

    def aplicar_entrada(self) -> None:
        self.entrada_foco = False
        self.novo_mundo(int(self.entrada) if self.entrada else N_MIN)

    def ajustar_dimensao(self, d: int) -> None:
        n = int(self.entrada) if self.entrada else N_MIN
        self.entrada = str(max(N_MIN, min(N_MAX, n + d)))

    def alternar_tocar(self) -> None:
        if not self.tem_plano():
            return
        if self.indice >= len(self.resultado.plano):
            self.indice = 0
        self.tocando = not self.tocando
        self._ultimo_tick = pygame.time.get_ticks()

    def reiniciar(self) -> None:
        self.indice = 0
        self.tocando = False

    def passo(self, d: int) -> None:
        if not self.tem_plano():
            return
        self.tocando = False
        self.indice = max(0, min(len(self.resultado.plano), self.indice + d))

    def alternar_rota(self) -> None:
        self.mostrar_rota = not self.mostrar_rota

    def alternar_algoritmo(self) -> None:
        self.algoritmo = "ucs" if self.algoritmo == "astar" else "astar"
        self.resolver_atual()

    def mudar_vel(self, d: int) -> None:
        self.vel = max(0, min(len(INTERVALOS_MS) - 1, self.vel + d))

    # ------------------------------------------------------------------ eventos
    def tratar_evento(self, ev: pygame.event.Event) -> None:
        if ev.type == pygame.QUIT:
            self.rodando = False
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
            self.entrada_foco = pygame.Rect(X_PAINEL, 95, 90, 34).collidepoint(ev.pos)
            for b in self.botoes:
                if b.clique(ev.pos):
                    break
        elif ev.type == pygame.KEYDOWN:
            if self.entrada_foco:
                if ev.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    self.aplicar_entrada()
                elif ev.key == pygame.K_ESCAPE:
                    self.entrada_foco = False
                elif ev.key == pygame.K_BACKSPACE:
                    self.entrada = self.entrada[:-1]
                elif ev.unicode.isdigit() and len(self.entrada) < 2:
                    self.entrada += ev.unicode
                return
            if ev.key == pygame.K_ESCAPE:
                self.rodando = False
            elif ev.key == pygame.K_n:
                self.aplicar_entrada()
            elif ev.key == pygame.K_SPACE:
                self.alternar_tocar()
            elif ev.key == pygame.K_RIGHT:
                self.passo(+1)
            elif ev.key == pygame.K_LEFT:
                self.passo(-1)
            elif ev.key == pygame.K_r:
                self.reiniciar()
            elif ev.key == pygame.K_t:
                self.alternar_rota()
            elif ev.key == pygame.K_a:
                self.alternar_algoritmo()
            elif ev.key in (pygame.K_PLUS, pygame.K_KP_PLUS, pygame.K_EQUALS):
                self.ajustar_dimensao(+1)
            elif ev.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                self.ajustar_dimensao(-1)

    def atualizar(self, agora_ms: int) -> None:
        if self.tocando and agora_ms - self._ultimo_tick >= INTERVALOS_MS[self.vel]:
            self._ultimo_tick = agora_ms
            if self.indice < len(self.resultado.plano):
                self.indice += 1
            if self.indice >= len(self.resultado.plano):
                self.tocando = False

    # ------------------------------------------------------------------ desenho
    def _texto(self, s, fonte, pos, cor=desenho.COR_TEXTO) -> int:
        t = fonte.render(s, True, cor)
        self.tela.blit(t, pos)
        return pos[1] + t.get_height() + 4

    def _quebrado(self, s, fonte, x, y, cor=desenho.COR_TEXTO, max_linhas=6) -> int:
        palavras, linha, linhas = s.split(" "), "", []
        for p in palavras:
            teste = (linha + " " + p).strip()
            if fonte.size(teste)[0] <= L_PAINEL:
                linha = teste
            else:
                linhas.append(linha)
                linha = p
        linhas.append(linha)
        if len(linhas) > max_linhas:
            linhas = linhas[:max_linhas]
            linhas[-1] = linhas[-1][: max(0, len(linhas[-1]) - 4)] + " ..."
        for l in linhas:
            y = self._texto(l, fonte, (x, y), cor)
        return y

    def desenhar(self) -> None:
        self.tela.fill((250, 250, 252))
        e = self.sim.estados[self.indice] if self.sim else self.mundo.estado_inicial()
        trajeto = None
        if self.sim and self.mostrar_rota:
            trajeto = [(s.agente, s.carregando) for s in self.sim.estados]
        desenho.desenhar_grade(self.tela, AREA_GRADE, self.mundo, agente=e.agente, pacote=e.pacote,
                               carregando=e.carregando, trajeto=trajeto)
        if not self.resultado.existe_solucao:
            pygame.draw.rect(self.tela, COR_ERRO, AREA_GRADE.inflate(6, 6), 3)

        x = X_PAINEL
        self._texto("Entregador em grid", self.f_titulo, (x, 22))
        self._texto("Dimensão do grid (N × N, de 2 a 60)", self.f_normal, (x, 70))
        caixa = pygame.Rect(x, 95, 90, 34)
        pygame.draw.rect(self.tela, (255, 255, 255), caixa, border_radius=6)
        pygame.draw.rect(self.tela, (40, 110, 220) if self.entrada_foco else COR_BORDA, caixa,
                         2 if self.entrada_foco else 1, border_radius=6)
        cursor = "|" if self.entrada_foco and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        self._texto(self.entrada + cursor, self.f_enorme, (caixa.x + 10, caixa.y + 7))

        mouse = pygame.mouse.get_pos()
        for b in self.botoes:
            b.desenhar(self.tela, self.f_normal, mouse)

        y = 372
        pygame.draw.line(self.tela, (210, 215, 225), (x, y - 8), (x + L_PAINEL, y - 8))
        r = self.resultado
        semente = self.mundo.semente if self.mundo.semente is not None else "-"
        y = self._texto(f"Semente: {semente}   ·   Obstáculos: {len(self.mundo.obstaculos)}   ·   "
                        f"Pedágios: {len(self.mundo.pedagios)}", self.f_pequena, (x, y), COR_CINZA)
        if r.existe_solucao:
            y = self._texto("Plano ótimo encontrado" if r.plano else "Pacote já está no destino",
                            self.f_negrito, (x, y + 2), COR_OK)
            y = self._texto(f"Custo total: {r.custo}    Ações: {len(r.plano)}", self.f_normal, (x, y))
            y = self._texto(f"Nós expandidos: {r.expandidos}    Tempo: {r.tempo_s * 1000:.2f} ms",
                            self.f_normal, (x, y))
            y = self._texto(f"Execução: passo {self.indice}/{len(r.plano)}    custo acumulado: "
                            f"{self.acumulado[self.indice]}", self.f_normal, (x, y + 4))
            if self.indice > 0:
                y = self._texto(f"Última ação: {r.plano[self.indice - 1]}", self.f_normal, (x, y))
            y = self._texto("Plano:", self.f_normal, (x, y + 6), COR_CINZA)
            self._quebrado(resumir_plano(r.plano, ascii_puro=True), self.f_pequena, x, y, max_linhas=6)
        else:
            y = self._texto("NÃO EXISTE SOLUÇÃO", self.f_enorme, (x, y + 4), COR_ERRO)
            y = self._quebrado(r.motivo, self.f_normal, x, y + 2, max_linhas=6)
        self._texto("Atalhos: N novo mundo · Espaço tocar/pausar", self.f_pequena, (x, ALTURA - 72), COR_CINZA)
        self._texto("Setas: passo a passo · R reiniciar · T rota", self.f_pequena, (x, ALTURA - 52), COR_CINZA)
        self._texto("A: A*/UCS · + e -: dimensão · Esc: sair", self.f_pequena, (x, ALTURA - 32), COR_CINZA)
        self._legenda()

    def _legenda(self) -> None:
        y, lado, x = AREA_GRADE.bottom + 10, 26, 24
        itens = [("Agente", desenho.desenhar_agente), ("Pacote", desenho.desenhar_pacote),
                 ("Destino", desenho.desenhar_destino), ("Obstáculo", None), ("Pedágio", None),
                 ("Ida", "ida"), ("Entrega", "entrega")]
        for nome, d in itens:
            r = pygame.Rect(x, y, lado, lado)
            if nome == "Obstáculo":
                pygame.draw.rect(self.tela, desenho.COR_OBSTACULO, r)
            elif nome.startswith("Pedágio"):
                pygame.draw.rect(self.tela, desenho.COR_PEDAGIO, r)
                pygame.draw.rect(self.tela, desenho.COR_GRADE, r, 1)
            elif d in ("ida", "entrega"):
                cor = desenho.COR_ROTA_IDA if d == "ida" else desenho.COR_ROTA_ENTREGA
                pygame.draw.line(self.tela, cor, (r.left, r.centery), (r.right, r.centery), 4)
            else:
                d(self.tela, r)
            t = self.f_pequena.render(nome, True, desenho.COR_TEXTO)
            self.tela.blit(t, (r.right + 5, y + (lado - t.get_height()) // 2))
            x = r.right + 5 + t.get_width() + 14

    # ------------------------------------------------------------------ laço
    def executar(self) -> None:
        relogio = pygame.time.Clock()
        while self.rodando:
            for ev in pygame.event.get():
                self.tratar_evento(ev)
            self.atualizar(pygame.time.get_ticks())
            self.desenhar()
            pygame.display.flip()
            relogio.tick(60)
        pygame.quit()


def executar(tamanho: int = 10, semente: Optional[int] = None, algoritmo: str = "astar") -> None:
    App(tamanho, semente, algoritmo).executar()
