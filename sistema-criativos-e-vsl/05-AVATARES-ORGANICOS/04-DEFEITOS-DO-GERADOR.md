# 04 — Defeitos do gerador

> 🔗 **O catálogo completo é a skill `video-ia-sem-defeito`**, que veio neste pacote em
> `.claude/skills/video-ia-sem-defeito/`. Ela é **niche-agnostic e ferramenta-agnostic**:
> vale igual em criativo pago, VSL e orgânico, e o Claude **ativa sozinho** toda vez que
> for escrever ou revisar prompt de vídeo.
>
> **Leia a skill antes de escrever qualquer prompt.** Este arquivo só registra o que é
> específico dos formatos orgânicos deste módulo.

---

## O resumo do catálogo, pra consulta rápida

| defeito | regra |
|---|---|
| objetos morfando | **um objeto, um movimento, o clipe inteiro** |
| matéria multiplicando | o gerador **não conta, clona** — peça matéria contínua ou uma unidade no singular |
| ação que não acontece | **transporte funciona, deformação não** (cortar, amassar, dobrar) |
| matéria saindo do lugar errado | diga **de onde** ela sai, em parágrafo próprio |
| texto pintado na parede | descrever por **aparência**, nunca por nome |
| faixa borrada em cima e embaixo | composição em **três camadas verticais** |
| final inventado | toda ação com **destino visível no frame** + estado final declarado |
| abertura parada | o movimento começa no **segundo zero** |
| vídeo sai diferente do prompt | **o frame manda mais que o texto** — confira o frame antes de animar |

---

## O que é específico do orgânico

### 1. A conferência de abertura mente em selfie

O checkpoint automático de "abertura parada" (diferença de hash entre o frame 0 e o de 1s)
**não enxerga movimento fino de rosto**. Ele acusou "parado" em vídeos que, medidos por
SSIM, tinham **mais** movimento que o campeão da página.

**A régua certa:** SSIM entre o frame de 0,1s e o de 1,1s, comparado contra um vídeo que
já performou. Menor = mais movimento.

```bash
ffmpeg -ss 0.1 -i v.mp4 -frames:v 1 a.png
ffmpeg -ss 1.1 -i v.mp4 -frames:v 1 b.png
ffmpeg -i a.png -i b.png -lavfi ssim -f null -
```

Números reais de uma página: campeão de 20 mil views = **0,565**. Vídeos novos aprovados =
**0,407** e **0,399** (mais movimento). O checkpoint acusou "parado" nos dois.

### 2. O produto sai de quadro no fim, e ninguém vê

No formato selfie o avatar **abaixa o braço** perto do fim e o produto sai de cena — o
último frame fica sem o produto, que é justamente o frame que fixa a marca.

**Correção:** varra o último segundo e meio de 0,3 em 0,3 e corte no **último instante com
o produto em quadro**. Cortar depois de legendar trunca a legenda queimada; corte o
intermediário e relegende.

### 3. O gerador desenha um celular na mão do avatar

No formato selfie, a câmera **é** o celular. Um segundo aparelho em quadro entrega a
encenação na hora.

Negativa obrigatória: `no phone visible in frame, no second phone, mirror selfie, reflection of a phone`.

### 4. O gerador cola fala extra depois do CTA

Medido: depois de `...then comment Yes`, o clipe continuou com uma palavra inventada
(`Chaitara`) que **foi parar na legenda queimada**.

**Correção:** silencie o trecho e corte deixando folga — não basta cortar seco, porque aí
a keyword do funil fica sem espaço pra durar o mínimo legível (ver módulo 05).

### 5. Recipiente escuro engole o produto

Vale só pro formato de bancada, e custou um vídeo inteiro: caneca azul-petróleo, cubos
rosa dentro, **o produto sumiu do vídeo**. Recipiente **sempre claro ou transparente**.
