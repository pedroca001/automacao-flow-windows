# 01 — Identidade do avatar

O que faz o público reconhecer a página no feed é **o mesmo rosto aparecendo todo dia**.
Se o rosto muda entre vídeos, você não tem uma persona — tem uma sequência de estranhas.

---

## O master: a foto que trava a identidade

Gere **uma** imagem da pessoa e guarde o `mediaId` dela. Toda geração de frame passa esse
master como referência. É ele, não o texto, que mantém o rosto.

```
avatares.json
  <id-da-pagina>:
    ref: "<mediaId do master>"     ← a identidade permanente
    abertura: "<quem ela é>"
    fechamento: "<cenário + negativas>"
```

Esse arquivo é **seu** (o Claude cria e mantém — não há script que o leia; ele é a memória da identidade entre sessões). Um exemplo pronto pra copiar: `scripts/exemplo-avatares.json`. Na hora de gerar, a `abertura` vira a `descricao_visual` da persona e o `fechamento` vira `cenario` + negativas no `leva.json` do `gerar_specs.py`; o `ref` entra como `master_mediaId` da persona no spec (o driver reusa o frame em vez de gerar outro).

O prompt final de cada frame é montado assim:

```
abertura  +  _frame_prompt da cena  +  fechamento
```

> Enquanto `ref` for `null`, cada geração inventa um rosto novo. Gere, aprove, **fixe o
> mediaId** — e só então comece a produzir em série.

---

## 🔴 O erro mais caro deste módulo: identidade contaminada por cena

**Na `abertura` fica SÓ quem a pessoa é**: idade, tipo físico, cabelo, olhos, pele,
textura, sinais de idade. Nada mais.

**Roupa, enquadramento, expressão e o que ela segura são da CENA.**

### Por que isso quebra na prática

Num projeto real a `abertura` do avatar tinha esta frase cravada:

> *"Her free hand holds a clear glass mason jar filled with bright pink cubes, with a
> handwritten label taped to the front, raised up beside her face."*

Como esse bloco é colado na frente de **todo** `_frame_prompt`, aconteceu o seguinte:

- Um roteiro pedindo explicitamente **abertura sem o produto** saiu com o produto na mão.
  Nenhuma redação de cena resolvia — a identidade ganhava sempre.
- Antes disso, um cfg de **consultório médico com três personagens** gerou *a mesma
  senhora na cozinha com o pote* — porque a identidade dela vinha ensanduichada entre a
  descrição da cena e uma lista de negativas que proibia exatamente o que o cfg pedia.

### O teste que revela a contaminação

> *"Se eu escrever uma cena que contradiz este campo, quem ganha?"*

Se a resposta for "o campo", ele está no lugar errado.

### O formato correto

```
abertura (identidade — nunca muda):
  Uma mulher americana comum, 39 anos, cabelo loiro-escuro ondulado na altura dos
  ombros, olhos cor de mel, sardas leves, sem maquiagem, textura de pele real com
  linhas de expressão.
  O CELULAR NUNCA APARECE: a câmera É o celular.
  O enquadramento, a roupa e o que as mãos fazem são descritos abaixo e mudam a
  cada vídeo.

_frame_prompt (cena — muda sempre):
  Ela veste uma regata justa azul-petróleo com um colar fino de ouro. ENQUADRAMENTO
  MAIS ABERTO: do peito pra cima, com a bancada visível ao lado. A mão livre segura
  [o objeto desta cena]. NÃO HÁ pote, rótulo, nem nada da marca em quadro.
```

---

## Um frame por cena, ou corrente de continuidade?

Duas arquiteturas, e a escolha muda o que é possível:

| | **Frame próprio por cena** | **Corrente (`continuar do anterior`)** |
|---|---|---|
| como funciona | cada cena gera o próprio frame inicial | a cena N começa do último frame da cena N-1 |
| emenda | corte seco (edição normal) | invisível |
| a cena 2 pode introduzir objeto novo? | ✅ sim | ❌ **não** — tudo que ela precisa já tem que existir no frame final da cena 1 |
| deriva acumulada | nenhuma | cresce a cada elo |

**Regra prática:**

- Precisa que a **cena 1 não tenha o produto** e a cena 2 tenha? → **frame por cena**,
  obrigatoriamente. Não existe de onde herdar.
- Quer emenda invisível entre duas poses da mesma pessoa no mesmo lugar? → corrente,
  com no máximo 2-3 elos.

⚠️ Numa corrente, quando a cena 2 falha repetidamente, **olhe o frame-ponte antes de
mexer no prompt dela**. Quase sempre o defeito nasceu na cena 1 e você está corrigindo
o lugar errado.

---

## Consistência de roupa entre cenas

Com frame por cena não há continuidade automática. Descreva a roupa **igual, palavra por
palavra**, nas três cenas — e confira depois com uma medida de distância entre o primeiro
e o último frame de cada clipe. Se a roupa derivar, aparece ali.

---

## ✅ Checklist

1. O master existe e o `mediaId` está fixado?
2. A `abertura` tem alguma coisa que não seja "quem a pessoa é"?
3. Se eu escrever uma cena contradizendo a `abertura`, quem ganha?
4. A arquitetura (frame por cena × corrente) permite o que o roteiro pede?
5. A roupa está descrita igual em todas as cenas?
6. Se é corrente: tudo que a cena N precisa existe no frame final da N-1?
