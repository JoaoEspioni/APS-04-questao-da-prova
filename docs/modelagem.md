# Modelagem e justificativas

Este documento explica **como o problema foi modelado**, **por que o algoritmo devolve o plano ótimo** e **como o programa reconhece que não existe solução**. O código correspondente está em `entregador/mundo.py` (regras) e `entregador/busca.py` (busca).

## 1. O problema

Um grid quadrado N×N tem um agente, um pacote, um destino, células **obstáculo** (intransponíveis) e células de **pedágio** (cinza). O agente executa 6 ações: `CIMA`, `BAIXO`, `ESQUERDA`, `DIREITA`, `PEGAR`, `ENTREGAR`. Quer-se uma sequência de ações (plano) de **custo mínimo** que deixe o pacote na célula de destino. Todas as ações custam 1, exceto as executadas em pedágio, que custam 1 + 2 = 3.

## 2. Interpretações adotadas

O enunciado deixa alguns pontos em aberto. Escolhi o seguinte, e o simulador (`Mundo.aplicar`) implementa exatamente isso:

| Ponto | Interpretação |
|---|---|
| Onde o pedágio é cobrado | Em **qualquer ação executada com o agente sobre uma célula cinza** (a célula onde o agente está *quando executa* a ação, inclusive `PEGAR` e `ENTREGAR`). Entrar na célula não paga; qualquer ação executada de dentro dela paga 3. |
| Movimento bloqueado (borda ou obstáculo) | O agente fica onde está, **mas a ação ainda custa** (e custa 3 se ele estiver em pedágio). |
| `PEGAR` fora da célula do pacote | Não tem efeito (custa normalmente). |
| `ENTREGAR` | Solta o pacote na célula atual do agente; só tem efeito se ele está carregando. O problema termina quando o pacote está **solto** na célula de destino. |
| Geração aleatória | Agente, pacote e destino em 3 células distintas e sem obstáculo; pedágios não ficam sobre essas 3 células. A fração de obstáculos é sorteada entre 0% e 45%. |

> Se a sua prova considerava o pedágio cobrado *ao entrar* na célula, a mudança é local: basta cobrar o custo extra na transição que **chega** à célula cinza (em `Mundo.aplicar`/`custo_acao` e no laço de sucessores de `_buscar`). A heurística continua a mesma.

## 3. Formulação como problema de busca

- **Estado (modelo completo):** `(posição do agente, posição do pacote, carregando?)`.
- **Estado inicial:** agente e pacote nas posições sorteadas, `carregando = falso`.
- **Ações e transição:** as 6 ações acima (`Mundo.aplicar`).
- **Custo da ação:** `1`, ou `3` se o agente está num pedágio.
- **Teste de objetivo:** `carregando = falso` **e** `posição do pacote = destino`.

## 4. Redução do espaço de estados

O modelo completo tem O(N⁴) estados (posição do agente × posição do pacote). Dá para reduzir para **2·N² + 1** sem perder nenhum plano ótimo:

**Fato 1.** Enquanto não for pego, o pacote não se mexe; depois de pego, ele acompanha o agente. Então, se o agente só larga o pacote no destino, a posição do pacote é sempre "a inicial" (antes do `PEGAR`) ou "a do agente" (depois). O estado resume-se a `(linha, coluna, carregando)`.

**Fato 2 (largar o pacote fora do destino nunca é ótimo).** Suponha um plano ótimo com `ENTREGAR` numa célula *c* diferente do destino. Antes dela o estado era (agente em *c*, carregando). Como o objetivo exige o pacote no destino, o agente precisa depois pegá-lo de novo, e só pode fazê-lo em *c* (o pacote parou lá). Nesse momento o estado volta a ser (agente em *c*, carregando). O trecho entre os dois estados é um **ciclo**; removê-lo gera um plano válido e **estritamente mais barato** (todos os custos são ≥ 1), contradizendo a otimalidade. Logo `ENTREGAR` só aparece no destino, e então o problema acaba (estado `FIM`).

**Fato 3.** Ações sem efeito (movimento bloqueado, `PEGAR` fora do pacote, `ENTREGAR` sem pacote) mantêm o estado e custam ≥ 1; nunca aparecem em plano ótimo. O solver nem as gera.

**Validação empírica:** `tests/test_busca.py` compara o solver com um Dijkstra sobre o **modelo completo, sem nenhuma poda** (`resolver_modelo_completo`, que usa as 6 ações em todo estado). Em 480 mundos aleatórios de 2×2 a 5×5, incluindo os sem solução, custos e existência de solução coincidem.

## 5. Heurística (A\*)

Para um estado `s = (r, c, carregando)`, com *a* = (r, c), *P* = pacote, *X* = destino e *d* = distância de Manhattan:

```
h(s) = d(a, X) + 1                       se carregando          (andar até X + ENTREGAR)
h(s) = d(a, P) + 1 + d(P, X) + 1         se não carregando      (ir a P + PEGAR + ir a X + ENTREGAR)
h(FIM) = 0
```

**Admissível.** Qualquer plano a partir de `s` precisa, no mínimo, dessas ações: cada movimento muda a distância de Manhattan em no máximo 1, `PEGAR` e `ENTREGAR` são obrigatórias, e cada ação custa ≥ 1 (o pedágio só aumenta o custo real). Portanto `h(s)` ≤ custo real até o objetivo.

**Consistente.** Para toda transição `s → s'` de custo `c ≥ 1`, vale `h(s) ≤ c + h(s')`:

- *movimento:* o termo de Manhattan muda em no máximo 1 ≤ c;
- `PEGAR` (em *P*): `h` cai exatamente 1 (de `d(P,X) + 2` para `d(P,X) + 1`) ≤ c;
- `ENTREGAR` (em *X*): `h` cai de 1 para 0 ≤ c.

Heurística consistente ⇒ o A\* com lista de fechados nunca precisa reabrir nós e devolve um **plano ótimo**. A heurística não "enxerga" obstáculos nem pedágios; por isso é segura, e mesmo assim poda bastante a busca (seção 8).

## 6. Algoritmo

```
fronteira ← {(início, g=0)}      # fila de prioridade ordenada por f = g + h (desempate: menor h)
enquanto fronteira não vazia:
    s ← remove o de menor f
    se s == FIM: devolve o plano (reconstruído pelos pais) e g(FIM)
    se s já foi expandido: continua
    para cada sucessor t de s:     # ≤ 5: 4 movimentos livres + (PEGAR em P | ENTREGAR em X)
        g' ← g(s) + custo(s)       # custo(s) = 1, ou 3 se s está em pedágio
        se g' < g(t): atualiza g(t), pai(t) e insere t na fronteira
devolve "sem solução"            # fronteira esgotada
```

Também há uma versão de **custo uniforme** (`h = 0`, `--algoritmo ucs`), usada como referência nos testes e na comparação de desempenho.

## 7. Detecção de "não existe solução"

Existe solução **se, e somente se**, (i) o pacote é alcançável a partir do agente e (ii) o destino é alcançável a partir do pacote, andando por células livres em 4-vizinhança.

- *(⇐)* Com os dois caminhos, o plano "ir até o pacote, `PEGAR`, ir até o destino, `ENTREGAR`" é válido.
- *(⇒)* O agente só se desloca por células livres, e o pacote só se desloca carregado pelo agente; sem esses caminhos o objetivo é inatingível.

O programa faz isso de **duas formas independentes**:

1. **Pré-teste por BFS** (`alcancaveis`): rápido, O(N²), e informa *por que* não há solução ("pacote isolado do agente" ou "destino inalcançável a partir do pacote").
2. **A própria busca**: se a fronteira esvazia sem alcançar `FIM`, conclui "sem solução". (Testado desligando o pré-teste: `resolver(..., verificar_alcancabilidade=False)`.)

Com obstáculos em excesso (≳ 40% das células) o grid costuma se fragmentar, então instâncias sem solução aparecem com frequência em mundos aleatórios grandes, e a interface mostra "NÃO EXISTE SOLUÇÃO" com o motivo.

## 8. Complexidade e desempenho

Há 2N² + 1 estados e no máximo 5 sucessores por estado. Com fila de prioridade binária, o A\* custa **O(N² log N)** de tempo e **O(N²)** de memória no pior caso, e funciona para qualquer N.

Medido com `python scripts/benchmark.py` (100 mundos aleatórios por tamanho, médias só sobre os que têm solução; ambos os algoritmos sempre encontraram o mesmo custo ótimo):

| N | mundos c/ solução | sem solução | A\*: nós expandidos | UCS: nós expandidos | A\*: tempo (ms) | UCS: tempo (ms) |
|---|---|---|---|---|---|---|
| 10 | 77 | 23 | 25 | 128 | 0.33 | 0.65 |
| 20 | 77 | 23 | 86 | 445 | 0.97 | 2.05 |
| 30 | 88 | 12 | 190 | 1026 | 1.76 | 3.85 |
| 40 | 83 | 17 | 321 | 1928 | 3.17 | 7.31 |
| 50 | 85 | 15 | 433 | 2728 | 4.35 | 10.08 |
| 60 | 85 | 15 | 617 | 3956 | 6.26 | 14.98 |

(Tempos em CPython num ambiente de nuvem; variam por máquina, mas a proporção entre os algoritmos se mantém.) O A\* expande em torno de 5–6× menos nós que o custo uniforme.

## 9. Como foi validado

| O quê | Como |
|---|---|
| Regras (movimento, bloqueios, pedágio, pegar/entregar) | `tests/test_mundo.py` |
| Plano devolvido é válido e o custo informado é o real | todo plano é re-executado no simulador (`Mundo.simular`) |
| Otimalidade | A\* = custo uniforme em ~125 mundos aleatórios (N de 6 a 40) e = Dijkstra do modelo completo em 480 mundos pequenos |
| Pedágio muda a rota | testes com mundos desenhados à mão (desvio compensa × pedágio inevitável) |
| Sem solução | pacote isolado, destino isolado, busca sem o pré-teste |
| Interface | `tests/test_interface.py` (headless): gerar, resolver, animar, digitar dimensão, mundo sem solução |
