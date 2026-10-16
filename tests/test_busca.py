"""Testes do solver: otimalidade, validade dos planos e detecção de instâncias sem solução."""
import os
import sys
import time
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from entregador.busca import (  # noqa: E402
    alcancaveis, resolver, resolver_modelo_completo, resumir_plano, trajeto_do_plano,
)
from entregador.mundo import EXEMPLO_PROVA_ASCII, Mundo  # noqa: E402


def mundo(texto: str) -> Mundo:
    return Mundo.de_ascii(texto)


class TestExemploDaProva(unittest.TestCase):
    def setUp(self):
        self.m = mundo(EXEMPLO_PROVA_ASCII)

    def test_plano_e_valido_e_otimo(self):
        r = resolver(self.m)
        self.assertTrue(r.existe_solucao)
        sim = self.m.simular(r.plano)
        self.assertTrue(sim.objetivo)
        self.assertEqual(sim.custo, r.custo)
        # confere com duas referências independentes
        self.assertEqual(resolver(self.m, algoritmo="ucs").custo, r.custo)
        self.assertEqual(resolver_modelo_completo(self.m)[1], r.custo)

    def test_custo_conhecido(self):
        self.assertEqual(resolver(self.m).custo, 24)

    def test_astar_expande_menos_que_ucs(self):
        a, u = resolver(self.m), resolver(self.m, algoritmo="ucs")
        self.assertLess(a.expandidos, u.expandidos)


class TestCasosEspeciais(unittest.TestCase):
    def test_pacote_ja_no_destino(self):
        m = Mundo(3, frozenset(), frozenset(), (0, 0), (2, 2), (2, 2))
        r = resolver(m)
        self.assertTrue(r.existe_solucao)
        self.assertEqual((r.plano, r.custo), ([], 0))

    def test_agente_comeca_sobre_o_pacote(self):
        m = Mundo(3, frozenset(), frozenset(), (1, 1), (1, 1), (1, 2))
        r = resolver(m)
        self.assertEqual(r.plano, ["PEGAR", "DIREITA", "ENTREGAR"])
        self.assertEqual(r.custo, 3)

    def test_pedagio_inevitavel_e_cobrado(self):
        # Corredor de uma linha (o resto é parede): não há como evitar o pedágio em (0,2).
        m = mundo("AP~X\n####\n####\n####")
        r = resolver(m)
        # DIREITA A→P (1) + PEGAR (1) + DIREITA P→(0,2) (1)
        # + DIREITA saindo do pedágio (1+2=3) + ENTREGAR (1) = 7
        self.assertEqual(r.plano, ["DIREITA", "PEGAR", "DIREITA", "DIREITA", "ENTREGAR"])
        self.assertEqual(r.custo, 7)
        self.assertEqual(m.simular(r.plano).custo, 7)

    def test_pedagio_compensa_desvio(self):
        # Reto, de P até X, são 3 ações a custo 1 + 3 + 3 = 7 (as duas últimas saem de pedágio).
        # Desviando pela linha de baixo são 5 ações a custo 1 cada = 5. Logo o plano ótimo desvia.
        m = mundo("AP~~X\n.....\n#####\n#####\n#####")
        r = resolver(m)
        self.assertEqual(r.custo, 1 + 1 + 5 + 1)  # ir até P + PEGAR + desvio + ENTREGAR
        self.assertEqual(m.simular(r.plano).custo, r.custo)
        rota = trajeto_do_plano(m, r.plano)
        self.assertNotIn((0, 2), rota)
        self.assertNotIn((0, 3), rota)
        self.assertEqual(r.custo, resolver_modelo_completo(m)[1])

    def test_pedagio_nao_compensa_desvio_longo(self):
        # Um único pedágio: reto = 1 + 3 = 4; desvio = 4 ações = 4 -> empate; o custo ótimo é o mesmo.
        m = mundo("AP~X\n....\n####\n####")
        self.assertEqual(resolver(m).custo, 1 + 1 + 4 + 1)


class TestSemSolucao(unittest.TestCase):
    def test_pacote_isolado_do_agente(self):
        # P = (1,3) tem os três vizinhos livres de borda bloqueados: (0,3), (2,3) e (1,2).
        m = mundo("A..#\n..#P\n...#\n#.#X")
        r = resolver(m)
        self.assertFalse(r.existe_solucao)
        self.assertEqual(r.plano, [])
        self.assertIsNone(r.custo)
        self.assertIn("pacote", r.motivo.lower())

    def test_destino_isolado_do_pacote(self):
        # X = (2,3): vizinhos (1,3), (3,3) e (2,2) são obstáculos; agente e pacote estão conectados.
        m = mundo("AP#.\n..##\n..#X\n####")
        r = resolver(m)
        self.assertFalse(r.existe_solucao)
        self.assertIn("destino", r.motivo.lower())

    def test_busca_sozinha_tambem_detecta_sem_solucao(self):
        """Mesmo sem o pré-teste de alcançabilidade, a busca esgota a fronteira e conclui 'sem solução'."""
        m = mundo("A..#\n..#P\n...#\n#.#X")
        r = resolver(m, verificar_alcancabilidade=False)
        self.assertFalse(r.existe_solucao)
        self.assertGreater(r.expandidos, 0)

    def test_alcancaveis(self):
        m = mundo("A.#\n.##\n#PX")
        self.assertEqual(alcancaveis(m, (0, 0)), {(0, 0), (0, 1), (1, 0)})


class TestContraReferenciaExaustiva(unittest.TestCase):
    """O modelo reduzido (r, c, carregando) não pode perder a solução ótima nem inventar uma."""

    def test_grids_pequenos_aleatorios(self):
        casos = sem = 0
        for n in (2, 3, 4, 5):
            for semente in range(120):
                m = Mundo.aleatorio(n, semente)
                ref = resolver_modelo_completo(m)
                r = resolver(m)
                r2 = resolver(m, verificar_alcancabilidade=False)
                casos += 1
                if ref is None:
                    sem += 1
                    self.assertFalse(r.existe_solucao, (n, semente))
                    self.assertFalse(r2.existe_solucao, (n, semente))
                else:
                    self.assertTrue(r.existe_solucao, (n, semente))
                    self.assertEqual(r.custo, ref[1], (n, semente))
                    self.assertEqual(r2.custo, ref[1], (n, semente))
        # garante que os dois tipos de instância foram exercitados
        self.assertGreater(sem, 5)
        self.assertGreater(casos - sem, 100)


class TestPropriedadesGerais(unittest.TestCase):
    def test_plano_valido_e_astar_igual_ucs(self):
        resolvidos = 0
        for n in (6, 10, 15, 25, 40):
            for semente in range(25):
                m = Mundo.aleatorio(n, semente)
                a = resolver(m)
                u = resolver(m, algoritmo="ucs")
                self.assertEqual(a.existe_solucao, u.existe_solucao, (n, semente))
                if a.existe_solucao:
                    resolvidos += 1
                    self.assertEqual(a.custo, u.custo, (n, semente))
                    sim = m.simular(a.plano)
                    self.assertTrue(sim.objetivo, (n, semente))
                    self.assertEqual(sim.custo, a.custo, (n, semente))
        self.assertGreater(resolvidos, 50)

    def test_custo_minimo_teorico(self):
        """Todo plano custa ao menos Manhattan(agente→pacote→destino) + 2 (PEGAR e ENTREGAR)."""
        for semente in range(40):
            m = Mundo.aleatorio(12, semente)
            r = resolver(m)
            if r.existe_solucao:
                d = (abs(m.agente[0] - m.pacote[0]) + abs(m.agente[1] - m.pacote[1])
                     + abs(m.pacote[0] - m.destino[0]) + abs(m.pacote[1] - m.destino[1]))
                self.assertGreaterEqual(r.custo, d + 2)

    def test_grid_grande_e_rapido(self):
        m = Mundo.aleatorio(60, 7, max_obstaculos=0.25)
        t0 = time.perf_counter()
        r = resolver(m)
        self.assertLess(time.perf_counter() - t0, 3.0)
        if r.existe_solucao:
            self.assertTrue(m.simular(r.plano).objetivo)

    def test_resumo_do_plano(self):
        self.assertEqual(resumir_plano(["DIREITA", "DIREITA", "BAIXO", "PEGAR"]), "→×2 ↓ [pegar]")
        self.assertEqual(resumir_plano([]), "(plano vazio)")


if __name__ == "__main__":
    unittest.main()
