# 05 — Legenda queimada e voz única

Duas coisas que parecem detalhe de acabamento e são, na prática, **onde o funil vaza**.

---

# Parte 1 — Legenda queimada

## Por que queimada, e em duas camadas

Reel roda **sem som** na maior parte das impressões. A legenda é o que segura quem parou.
Os que performam usam duas camadas:

1. **Banner de gancho no topo** — caixa sólida colorida, texto escuro, **estático do
   segundo 0 até o fim**. É o que captura quem passa no scroll sem áudio.
   Regras medidas: frase gramaticalmente incompleta, **sem** reticências, sentence case
   (não CAPS), 3-5 palavras, **sem CTA** — CTA no gancho derrubou views a 1/5 na amostra.
2. **Karaokê no rodapé** — CAIXA ALTA, branco com contorno, palavras-chave em amarelo, e
   **a keyword do funil gigante** na zona do CTA.

## As regras de bloco que custaram reprovação

| regra | por quê |
|---|---|
| **≤3 palavras E ≤21 caracteres** por bloco | contar só palavras não basta: um token composto (o nome do produto, que o dicionário de correção junta num só) faz um bloco de "3 palavras" ter 26 caracteres, quebrar em duas linhas e virar paredão |
| **cada bloco termina quando o próximo começa** | mínimo fixo de duração faz dois blocos ficarem simultâneos quando a fala é rápida — e o renderizador **empilha** os dois na tela |
| 🔴 **duração mínima de 0,45s, e 0,75s pra keyword** | ver abaixo |
| **bloco nunca atravessa fronteira de cena** | ver abaixo |

### 🔴 Bloco curto demais pra ler — o pior de todos

Medido: um bloco de 3 palavras ficou **0,07s** na tela, e a **keyword do funil ficou
0,27s**. Três palavras em 0,07s não é fala rápida — é **timestamp errado**. O transcritor
comprime os tempos das primeiras palavras depois de um silêncio longo, e o agrupador
aceitava qualquer duração.

**Correção:** mínimo de **0,45s** por bloco e **0,75s pra keyword**, servido de duas
fontes nesta ordem:
1. o **espaço vazio antes** do bloco — estica pra trás, ninguém perde nada;
2. a **folga no fim do vídeo** — empurra este bloco e os seguintes, preservando a duração
   de cada um.

⚠️ **Confira por lista, não por imagem.** Um bloco de 0,07s não aparece nem amostrando a
5 fps. Imprima todos os blocos com entrada, saída e duração, e marque os que ficarem
abaixo do mínimo.

### 🔴 Bloco atravessando a emenda entre cenas

Sintoma: `TWO MINUTES SET` — o fim de uma frase grudado no começo da seguinte, virando
uma frase que não existe.

Tentativa 1: marcar fim de frase pela pontuação. **Falhou** — o transcritor nem sempre
emite o ponto, e quando emite pode ser um token separado que o filtro de pontuação apaga
antes do agrupador ver.

Tentativa 2: passar os **instantes de corte** (que você conhece — são os mesmos da
montagem) e obrigar o bloco a fechar ali. **Ainda escapou**: o transcritor deu início
`5,78` pra uma palavra com a fronteira em `5,83`. Cinco centésimos.

**Correção final:** classificar a palavra pelo **meio** dela, não pelo início. A palavra
vai pro lado onde está a maior parte dela — estável contra esse erro de timestamp.

### 🔴 Palavra partida no meio

O transcritor com um token por vez parte palavra: `Slice` virou `Sl` + `ice`, e noutra
rodada `S` + `lic` + `ed`. Queima `SL ICE IT` na tela.

**Correção genérica:** o roteiro é conhecido — use ele como **vocabulário**. Se juntar
2-3 tokens seguidos produz uma palavra do roteiro e nenhum pedaço existe sozinho, emenda.
Tolere até 3 letras de sufixo, porque o transcritor flexiona.

### ⚠️ A raiz que continua aberta

Três defeitos diferentes (`SL ICE`, `WARM ME DOWN` no lugar de *wore*, `BULL` no lugar de
*bowl*) têm **a mesma causa**: a legenda vem da **transcrição**, e você já conhece o
**roteiro**. O transcritor só precisa dar o *tempo*.

**A correção definitiva é alinhar as duas sequências** (roteiro × transcrição) e queimar
as palavras do roteiro nos tempos da transcrição. Mata a classe inteira de uma vez:
palavra partida, palavra trocada, número escrito por extenso virando dígito.

Enquanto isso não existe, há um paliativo barato: **não use no roteiro palavras que o
transcritor erra**. `bowl` vira `bull`; troque por "it".

### Outras armadilhas

- **CAIXA ALTA no texto falado faz o TTS soletrar.** `YES` vira "y-e-s". A keyword vai
  capitalizada normal na fala (`Yes`); CAIXA ALTA é trabalho da legenda.
- **Número por extenso vira dígito** na transcrição (`sixteen` → `16`), e aí não casa com
  a lista de palavras a destacar. Cadastre as duas formas.
- **Aceleração piora a transcrição.** Acelerar 1,2x fez `wore` virar `warm`.

---

# Parte 2 — Voz única

## O problema

Cada clipe do gerador traz **a própria locução** — ela vem junto com o vídeo, no mesmo
job, e não há parâmetro pra reusar a voz do clipe anterior. **Vídeo de 3 cenas sai com 3
pessoas diferentes narrando a mesma história.**

## A correção

Gere a locução **fora** do gerador, com uma voz só, e substitua a faixa inteira. Um TTS
neural gratuito e sem chave (`edge-tts`) resolve. Script pronto em
`scripts/voz-unica.py`.

🔴 **SÓ EM VÍDEO SEM ROSTO.** Sem rosto não há sincronia labial pra quebrar. Com avatar,
trocar o áudio dessincroniza a boca — ali a voz continua vindo do gerador.

⚠️ **Relegende sempre depois.** A legenda sai da transcrição, e o áudio mudou.

## Escolha a voz pela VELOCIDADE, não pelo timbre

Medido numa cena de 21 palavras em 7,38s de vídeo — quanto cada voz precisa acelerar:

| voz | ajuste |
|---|---|
| `en-US-EmmaNeural` | **+4%** |
| `en-US-AvaNeural` | +10% |
| `en-US-JennyNeural` | +29% |
| `en-US-AriaNeural` · `en-US-MichelleNeural` | +34% |

Aceleração alta soa apressada. **A voz naturalmente rápida sai mais natural**, porque
quase não precisa de ajuste. Mantenha a mesma voz em todos os vídeos da página — ela
vira parte da identidade.

## O ajuste vai nos DOIS sentidos

Primeira versão do script só acelerava quando não cabia, e o que sobrava virava silêncio:
deu **1,58s de buraco** entre duas cenas, acima do limite que reprova. Agora, quando
sobra tempo, ele **desacelera** (teto -18%), tira o silêncio das pontas do TTS antes de
medir, e distribui o respiro entre entrada e saída.

**Calibre:** `~18-20 palavras por 6s de segmento`. Fora disso o TTS bate no teto (+30%,
apressado) ou no piso (-18%, arrastado com buraco).

## 🔑 A propriedade que isso libera

Com a faixa substituída, **o texto falado se descola do que o gerador falou**. Dá pra
reescrever o roteiro e regerar **só o áudio**, com o vídeo já montado e aprovado intacto.

Usos reais: recalibrar uma cena cujo roteiro ficou curto pro segmento, e trocar uma
palavra que o transcritor erra — **sem gastar uma geração**.

## ⚠️ O log de corte mente

O montador imprime `corte em 8.27s` para um clipe que tem no máximo 8,0s — ele clampa na
montagem, o log mostra o valor **pedido**. Copiar o log às cegas somou 20,37s contra um
vídeo de 20,11s: **cada cena entraria atrasada em relação à imagem, sem nada acusar.**

**Ponha uma trava:** se a soma dos cortes não bater com a duração do vídeo, aborte.

---

## ✅ Checklist

1. Rodou a **lista de blocos** com duração? Algum abaixo de 0,45s?
2. A **keyword do funil** tem ≥0,75s na tela e está destacada?
3. Algum bloco atravessa a emenda entre cenas?
4. A transcrição bate palavra por palavra com o roteiro?
5. Vídeo sem rosto e multi-cena: a voz é a mesma do começo ao fim?
6. Relegendou **depois** de trocar o áudio?
7. Buracos de silêncio abaixo de 1,0s?
