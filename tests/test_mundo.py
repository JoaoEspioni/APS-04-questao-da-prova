"""Testes das regras do problema (simulador)."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from entregador.mundo import (  # noqa: E402
    BAIXO, CIMA, DIREITA, ENTREGAR, ESQUERDA, EXEMPLO_PROVA_ASCII, PEGAR, Estado, Mundo,
)


def mundo(texto: str) -> Mundo:
    return Mundo.de_ascii(texto)


class TestRegras(unittest.TestCase):
    def setUp(self):
        # A . #
        # ~ P .
        # . . X
        self.m = mundo("A.#\n~P.\n..X")

    def test_movimento_livre(self):
        e, c = self.m.aplicar(self.m.estado_inicial(), DIREITA)
        self.assertEqual(e.agente, (0, 1))
        self.assertEqual(c, 1)

    def test_movimento_bloqueado_por_borda_mantem_celula(self):
        e0 = self.m.estado_inicial()
        for acao in (CIMA, ESQUERDA):
            e, c = self.m.aplicar(e0, acao)
            self.assertEqual(e.agente, e0.agente)
            self.assertEqual(c, 1)  # a ação ainda custa

    def test_movimento_bloqueado_por_obstaculo(self):
        e = Estado((0, 1), (1, 1), False)
        e2, _ = self.m.aplicar(e, DIREITA)  # (0,2) é obstáculo
        self.assertEqual(e2.agente, (0, 1))

    def test_pedagio_custa_3_quando_a_acao_e_executada_nele(self):
        e = Estado((1, 0), (1, 1), False)  # agente sobre o pedágio
        for acao in (CIMA, BAIXO, DIREITA, PEGAR, ENTREGAR):
            _, c = self.m.aplicar(e, acao)
            self.assertEqual(c, 3, acao)

    def test_pegar_so_funciona_na_celula_do_pacote(self):
        e0 = self.m.estado_inicial()
        e, _ = self.m.aplicar(e0, PEGAR)
        self.assertFalse(e.carregando)
        e = Estado((1, 1), (1, 1), False)
        e, _ = self.m.aplicar(e, PEGAR)
        self.assertTrue(e.carregando)

    def test_pacote_acompanha_o_agente_quando_carregado(self):
        e = Estado((1, 1), (1, 1), True)
        e, _ = self.m.aplicar(e, DIREITA)
        self.assertEqual((e.agente, e.pacote), ((1, 2), (1, 2)))

    def test_pacote_nao_se_move_quando_solto(self):
        e = Estado((0, 0), (1, 1), False)
        e, _ = self.m.aplicar(e, BAIXO)
        self.assertEqual(e.pacote, (1, 1))

    def test_entregar_solta_pacote_na_celula_do_agente(self):
        e = Estado((2, 1), (2, 1), True)
        e, _ = self.m.aplicar(e, ENTREGAR)
        self.assertFalse(e.carregando)
        self.assertEqual(e.pacote, (2, 1))
        self.assertFalse(self.m.eh_objetivo(e))  # (2,1) não é o destino
        e, _ = self.m.aplicar(Estado((2, 2), (2, 2), True), ENTREGAR)
        self.assertTrue(self.m.eh_objetivo(e))

    def test_entregar_sem_pacote_nao_faz_nada(self):
        e0 = self.m.estado_inicial()
        e, _ = self.m.aplicar(e0, ENTREGAR)
        self.assertEqual(e, e0)

    def test_objetivo_exige_pacote_solto_no_destino(self):
        self.assertFalse(self.m.eh_objetivo(Estado((2, 2), (2, 2), True)))
        self.assertTrue(self.m.eh_objetivo(Estado((0, 0), (2, 2), False)))

    def test_acao_desconhecida(self):
        with self.assertRaises(ValueError):
            self.m.aplicar(self.m.estado_inicial(), "PULAR")

    def test_simular_soma_custos(self):
        sim = self.m.simular([BAIXO, BAIXO, DIREITA])  # passa por (1,0) pedágio: ação lá custa 3
        self.assertEqual(sim.custo, 1 + 3 + 1)
        self.assertEqual(sim.estados[-1].agente, (2, 1))


class TestValidacaoEAscii(unittest.TestCase):
    def test_roundtrip_exemplo_prova(self):
        m = mundo(EXEMPLO_PROVA_ASCII)
        self.assertEqual(m.n, 10)
        self.assertEqual(m.agente, (0, 0))
        self.assertEqual(m.pacote, (2, 8))
        self.assertEqual(m.destino, (9, 9))
        self.assertEqual(len(m.obstaculos), 11)
        self.assertEqual(len(m.pedagios), 8)
        self.assertEqual(mundo(m.para_ascii()).para_ascii(), m.para_ascii())

    def test_ascii_com_rota_pode_ser_relido(self):
        m = mundo("AP~\n.#.\n..X")
        marcado = m.para_ascii(trajeto=[(0, 2), (1, 0)])
        self.assertEqual(marcado.splitlines()[0], "AP+")
        self.assertEqual(mundo(marcado).pedagios, m.pedagios)

    def test_pedagio_sob_especial_usa_minuscula(self):
        m = mundo("a.\npX")  # agente e pacote sobre pedágio
        self.assertIn((0, 0), m.pedagios)
        self.assertIn((1, 0), m.pedagios)
        self.assertEqual(mundo(m.para_ascii()), m)

    def test_comentarios_e_linhas_em_branco(self):
        m = mundo("; comentário\n\nAP\n.X")
        self.assertEqual(m.n, 2)

    def test_erros(self):
        with self.assertRaises(ValueError):
            mundo("AP.\n.X.")  # não quadrado
        with self.assertRaises(ValueError):
            mundo("AA\nPX")  # dois agentes
        with self.assertRaises(ValueError):
            mundo("A?\nPX")  # caractere inválido
        with self.assertRaises(ValueError):
            Mundo(2, frozenset({(0, 0)}), frozenset(), (0, 0), (0, 1), (1, 1))  # agente em obstáculo
        with self.assertRaises(ValueError):
            Mundo(2, frozenset({(5, 5)}), frozenset(), (0, 0), (0, 1), (1, 1))  # obstáculo fora


class TestGeracaoAleatoria(unittest.TestCase):
    def test_propriedades_para_varios_tamanhos(self):
        for n in (2, 3, 5, 10, 25, 60):
            for semente in range(30):
                m = Mundo.aleatorio(n, semente)
                self.assertEqual(m.n, n)
                especiais = {m.agente, m.pacote, m.destino}
                self.assertEqual(len(especiais), 3)
                for p in especiais:
                    self.assertTrue(m.dentro(p))
                    self.assertNotIn(p, m.obstaculos)
                self.assertFalse(m.obstaculos & m.pedagios)
                self.assertFalse(especiais & m.pedagios)
                self.assertTrue(all(m.dentro(p) for p in m.obstaculos | m.pedagios))

    def test_reprodutivel_pela_semente(self):
        self.assertEqual(Mundo.aleatorio(15, 123), Mundo.aleatorio(15, 123))
        self.assertNotEqual(Mundo.aleatorio(15, 123), Mundo.aleatorio(15, 124))

    def test_quantidade_de_obstaculos_varia(self):
        qtds = {len(Mundo.aleatorio(20, s).obstaculos) for s in range(40)}
        self.assertGreater(len(qtds), 10)

    def test_dimensao_invalida(self):
        with self.assertRaises(ValueError):
            Mundo.aleatorio(1)


if __name__ == "__main__":
    unittest.main()
