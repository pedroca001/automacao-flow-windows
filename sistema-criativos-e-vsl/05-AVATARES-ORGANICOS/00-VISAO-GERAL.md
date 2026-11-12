# 00 — Visão geral: o jogo orgânico

> Módulo complementar ao sistema de Criativos & VSL. Mesma fábrica de vídeo (Flow/Veo),
> mesmo ffmpeg, mesmo whisper — **jogo diferente**.

## O que é uma operação de avatar orgânico

Uma página de rede social com uma persona de IA que **posta reels todo dia** e nunca
compra mídia. O dinheiro entra assim:

```
reel na aba de recomendações
   → alguém comenta a KEYWORD ("yes", "horse", o que você escolher)
      → automação responde no direct com o link da bridge
         → bridge entrega a "receita/aula" e leva pra oferta
            → venda rastreada por subid do vídeo
```

Custo de mídia: **zero**. Custo de produção: o da geração de vídeo, que em plano com
i2v de baixa prioridade fica em zero crédito. O gargalo não é dinheiro — é **cadência**
e **compliance**.

---

## 🔴 Pago × Orgânico — as leis que se invertem

Esta é a seção mais importante do módulo. Várias leis do `SISTEMA.md`, corretas para
criativo pago, **derrubam a distribuição em orgânico**. A diferença de fundo:

| | Pago | Orgânico |
|---|---|---|
| quem decide quem vê | você, comprando impressão | o algoritmo, de graça |
| o vídeo precisa | **converter** quem já foi impactado | **ser distribuído** antes de converter |
| métrica que manda | CPA, ROAS | **distribuição** (quantas views a plataforma te dá) |

### As três inversões, com número

**1. Produto no frame 0: obrigatório em pago, veneno em orgânico.**

Numa página nossa, seis reels publicados. Os dois que **não** abrem com o produto na
mão foram os dois únicos que entregaram:

| abertura | views |
|---|---|
| **sem** o produto em quadro | **20.000** |
| **sem** o produto em quadro | 1.000 |
| com o produto no frame 0 | 375 |
| com o produto no frame 0 | 512 · 329 · 244 |

🔑 O reel de 20 mil e o de 375 têm **o roteiro idêntico, palavra por palavra**, mesma
avatar, mesma cozinha. A única diferença relevante é o produto no primeiro segundo.

> ⚠️ **Tirar o produto destrava, mas não basta.** O reel de 1 mil também não tinha
> produto na abertura — o gancho dele abria com subordinada temporal (*"For a while I
> thought…"*), o pior hook rate da operação. **O produto decide SE entrega; o gancho
> decide QUANTO.**

**2. Duração: 60s+ em pago, 17-20s em orgânico.**

Os dois que entregaram têm 18 e 19 segundos. Os quatro de 8 segundos ficaram no fundo
da lista. E cuidado com a armadilha de medição: 8s **maximiza porcentagem assistida** —
a curva de retenção comprova. Só que porcentagem assistida não traz view; distribuição
traz. Otimizar retenção e perder distribuição é o erro clássico deste formato.

**3. "Impacto visual no frame 1" continua valendo — mas o que impacta muda.**

A lei sobrevive inteira: **tem que ACONTECER algo antes de 2 segundos, e não pode ser
uma pessoa parada falando**. O que muda é *o quê* se move. Em pago é o produto; em
orgânico é qualquer coisa **menos** o produto — as mãos preparando comida, a faca, o
líquido sendo despejado, um objeto do cotidiano na mão.

---

## O mapa deste módulo

| arquivo | o que resolve |
|---|---|
| `01-IDENTIDADE-DO-AVATAR.md` | o rosto não mudar entre vídeos, e o erro de misturar identidade com cena |
| `02-PAGINA-E-PERSONA.md` | criar a página sem levantar bandeira de rede coordenada |
| `03-FORMATOS-ORGANICOS.md` | os 3 formatos medidos + a ponte com a biblioteca de formatos do sistema |
| `04-DEFEITOS-DO-GERADOR.md` | o que é específico do orgânico (o catálogo geral é a skill `video-ia-sem-defeito`) |
| `05-LEGENDA-E-VOZ.md` | legenda queimada sem bug e voz única em vídeo multi-cena |
| `06-FUNIL-DM-ORGANICO.md` | keyword, bridge, automação de DM e rastreio por vídeo |
| `07-MEDIR-E-DECIDIR.md` | quais números decidem e como não se enganar com eles |

## 🔗 O que este módulo NÃO refaz

Ele se apoia no que o sistema já tem, em vez de duplicar:

| pra isso | continue usando |
|---|---|
| escrever roteiro, CTA, headline, oferta | as skills `direct-response-copywriter`, `copy-legends`, `marketing-psychology` |
| escolher a embalagem do formato e o hook | `04-BRINDE-BIBLIOTECA-FORMATOS/` (a ponte está no módulo 03) |
| operar o Flow sem clique, state em disco | `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md` + `scripts/` |
| montar em ffmpeg, normalizar, legendar | `01-CRIATIVOS/04-PIPELINE-TECNICO.md` |
| achar oferta escalada pra modelar | o swipe file online + `01-CRIATIVOS/01-ESPIONAGEM-APIFY.md` |
| prompt de vídeo que não quebra | a skill **`video-ia-sem-defeito`**, que veio neste pacote |

**O que só existe aqui:** a identidade do avatar, a página e a persona, o esqueleto de cena
do reel orgânico, o funil de DM, e as leis que se invertem entre pago e orgânico.

## As 5 coisas que valem mais aqui

Se você só tiver 10 minutos, leia estas:

1. **Produto no frame 0 mata a distribuição orgânica.** Dois reels com roteiro idêntico
   palavra por palavra: **375 views contra 20.000**. *(este arquivo, acima)*

2. **Identidade do avatar ≠ cena.** Se a descrição da identidade disser o que a pessoa
   segura, nenhum roteiro consegue tirar aquilo de lá. Custou um lote inteiro pra
   descobrir. *(01-IDENTIDADE-DO-AVATAR)*

3. **O gerador não conta, ele clona.** Peça "três ou quatro cubos" e a tigela vira dez e
   continua crescendo depois de a mão sair do quadro. *(skill `video-ia-sem-defeito`)*

4. **A keyword do funil ficava 0,27s na tela.** Tempo insuficiente pra ler a palavra de
   que o funil inteiro depende — e folha de contato não pega isso, porque bloco curto não
   cai na amostra. Legenda se confere por **lista de tempos**. *(05-LEGENDA-E-VOZ)*

5. **Retenção e distribuição são coisas diferentes.** Um formato foi "validado" por
   maximizar porcentagem assistida e estava no fundo da lista em views. *(07-MEDIR-E-DECIDIR)*

---

## ⚠️ Duas ressalvas sobre estes números

**Os números vêm de uma operação, num nicho.** Página de saúde masculina em inglês, público
americano. São reais e medidos, não deduzidos — mas são **uma** amostra. O **método** de
medir transfere; os **números** você refaz no seu nicho antes de tratar como lei.

**Um achado vale onde foi medido.** "Produto fora da abertura" nasceu num formato **com
rosto**, onde o produto na mão interrompe o que interessa. Não há nenhum dado dizendo que
transfere pra formato **sem rosto**, onde manipular o produto *é* a ação, não uma
interrupção dela. O módulo `07-MEDIR-E-DECIDIR.md` mostra como transformar isso num A/B de
propósito — duas páginas fazendo coisas opostas — em vez de assumir.

---

## As 3 leis que resumem o módulo

1. **O produto fecha o vídeo, não abre.** (E se o seu nicho contrariar isso, meça antes
   de assumir — veja a ressalva de escopo em `07-MEDIR-E-DECIDIR.md`.)
2. **Identidade é quem a pessoa é. Todo o resto é cena.**
3. **Uma variável por teste.** Trocar gancho e visual juntos produz um vídeo, não um dado.
