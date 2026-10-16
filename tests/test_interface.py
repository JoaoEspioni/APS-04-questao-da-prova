"""Teste de fumaça da interface gráfica (headless, via driver 'dummy' do SDL)."""
import os
import sys
import unittest

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

try:
    import pygame
    from entregador.interface import App, X_PAINEL
except ImportError:  # pygame não instalado: o restante do projeto não depende dele
    pygame = None


@unittest.skipIf(pygame is None, "pygame não instalado")
class TestInterface(unittest.TestCase):
    def test_gerar_resolver_animar_e_desenhar(self):
        app = App(8, 1)
        self.assertEqual(app.mundo.n, 8)
        # procura uma semente com solução e anima o plano inteiro
        for s in range(50):
            app.novo_mundo(8, s)
            if app.resultado.existe_solucao:
                break
        self.assertTrue(app.tem_plano())
        app.alternar_tocar()
        t = 0
        while app.tocando:
            t += 10_000
            app.atualizar(pygame.time.get_ticks() + t)
        self.assertEqual(app.indice, len(app.resultado.plano))
        self.assertTrue(app.mundo.eh_objetivo(app.sim.estados[-1]))
        app.desenhar()

    def test_mundo_sem_solucao_e_informado(self):
        app = App(12, 0)
        for s in range(300):
            app.novo_mundo(12, s)
            if not app.resultado.existe_solucao:
                break
        self.assertFalse(app.resultado.existe_solucao)
        self.assertFalse(app.tem_plano())
        app.desenhar()  # não deve levantar exceção

    def test_digitar_dimensao(self):
        app = App(10, 0)
        app.tratar_evento(pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1, pos=(X_PAINEL + 10, 110)))
        self.assertTrue(app.entrada_foco)
        for _ in range(3):
            app.tratar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_BACKSPACE, unicode=""))
        for ch in "17":
            app.tratar_evento(pygame.event.Event(pygame.KEYDOWN, key=ord(ch), unicode=ch))
        app.tratar_evento(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN, unicode="\r"))
        self.assertEqual(app.mundo.n, 17)

    def test_dimensao_e_limitada(self):
        app = App(10, 0)
        app.entrada = "99"
        app.aplicar_entrada()
        self.assertEqual(app.mundo.n, 60)
        app.entrada = "1"
        app.aplicar_entrada()
        self.assertEqual(app.mundo.n, 2)


if __name__ == "__main__":
    unittest.main()
