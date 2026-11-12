# 01 — MODELAGEM (engenharia reversa da VSL de referência)

> Antes de escrever uma linha de roteiro, você destrincha uma VSL que JÁ vende até ela virar um doc-mestre: arquitetura em blocos com timestamps, escada de crenças, dispositivos de edição, ritmo de corte e mapa de compressão. O roteiro novo é construído POR CIMA desse esqueleto. Isso é o que separa "modelar" de "assistir e imitar de memória".

## O que você precisa ter em mãos

- A VSL de referência em .mp4 local (se for link, o Claude baixa com yt-dlp ou ferramenta equivalente).
- O conteúdo do SEU produto (quiz, página de resultado, oferta, stack, preço) — é a fonte da verdade da copy nova.
- Opcional mas poderoso: uma segunda referência só de PITCH (uma VSL sua que já converte, pra transplantar o fechamento).

O comando pro seu Claude:

```
Leia 02-VSL/01-MODELAGEM.md. Faça a engenharia reversa completa de
referencia/vsl-ref.mp4: transcrição com timestamps, contagem de cortes,
grids de frames, análise bloco a bloco e o doc-mestre final
(MODELAGEM.md) no formato do passo 6.
```

---

## Passo 1 — Transcrição local (whisper.cpp)

Extrai o áudio e transcreve com timestamps. Uma VSL de 54 min leva ~10 min de máquina:

```bash
ffmpeg -y -i referencia/vsl-ref.mp4 -ar 16000 -ac 1 analise/ref.wav
whisper-cli -m tools/whisper/ggml-small.bin -l auto -osrt -otxt \
  -of analise/transcricao -f analise/ref.wav
```

Saída: `transcricao.srt` (com timestamps — é este que a análise usa) e `transcricao.txt` (leitura corrida).

## Passo 2 — Contar os cortes = extrair a META DE RITMO

O ritmo de edição é um dado tão importante quanto a copy. O scene-detect do ffmpeg conta cada corte de cena:

```bash
ffmpeg -i referencia/vsl-ref.mp4 -vf "select='gt(scene,0.30)',showinfo" -f null - 2> analise/scene.log
grep -o "pts_time:[0-9.]*" analise/scene.log | wc -l
```

O Claude parseia os `pts_time:` num JSON (`cortes.json` com total + lista de timestamps). Exemplo real de leitura: uma VSL escalada de 33 min com ~650 cortes = **ritmo médio de ~3,1s por corte** — e o ritmo NÃO é uniforme: o bloco do hook roda a ~2,0s/corte, os blocos educativos relaxam pra ~4s, o pitch volta a acelerar. Esse perfil de ritmo por bloco vira a meta da SUA edição (é ele que justifica punch-ins e cutaways na montagem, doc 04/05).

## Passo 3 — Leitura visual: frames a 0.25fps + grids 3x3

Um frame a cada 4 segundos, montados em grades de 9 (cada grid = 36s de vídeo), com um mapa temporal do que cada grid cobre:

```bash
ffmpeg -y -i referencia/vsl-ref.mp4 -vf "fps=0.25,scale=360:-2" -q:v 4 analise/frames/f%04d.jpg
```

Depois o Claude monta os grids com `xstack` (9 entradas, layout 3x3) e grava um `mapa.json`: `{"grid_01.jpg": {"inicio_s": 0, "fim_s": 36}, ...}`. Convenção fixa: ordem cronológica esquerda→direita, cima→baixo, **cada frame = 4 segundos**. Com o mapa, qualquer frame do grid vira timestamp sem ambiguidade.

Os grids revelam o que a transcrição não mostra: talking head vs b-roll, prints de estudo na tela, antes/depois, props físicos, trocas de figurino e cenário (= as "sessões de gravação" da narradora), overlays de preço, texto queimado, CTA gestual.

## Passo 4 — Análise bloco a bloco DELEGADA (paralela)

Uma VSL de 30+ min é grande demais pra analisar de uma vez com qualidade. O método que funciona:

1. **Dividir em blocos de ~4 min** (7 grids por bloco). Pra cada bloco, gerar um `transcript_N.txt` com só as falas daquele trecho (com timestamps) + a contagem de cortes do trecho no cabeçalho.
2. **Despachar um agente de visão POR BLOCO, em paralelo** (subagentes do Claude Code, ou um segundo CLI de modelo com visão — qualquer um que leia imagem serve). Cada agente recebe: os 7 grids do bloco + o transcript do bloco + este prompt-molde:

```
Você é um analista de VSLs de resposta direta. Analise o BLOCO {n}/{N}
(trecho {t0} a {t1}) de uma VSL que vamos MODELAR — preciso de detalhe
cirúrgico. Insumos: os grids 3x3 listados (cada frame = 4 SEGUNDOS,
ordem esquerda→direita, cima→baixo) + a transcrição com timestamps.
Escreva analise/blocos/bloco-{n}.md com EXATAMENTE estas seções:
## Cena a cena (visual, com timestamps) — quem aparece, enquadramento,
   cenário, roupa, o que está FAZENDO, props, b-rolls, prints na tela,
   antes/depois; transcreva TODO texto de overlay LETRA A LETRA.
## Copy deste bloco (com timestamps) — o arco argumentativo, frases-chave
   LITERAIS, loops abertos e fechados.
## Dispositivos de edição e retenção — padrão de corte, zooms, tela
   verde/recorte da narradora, provas visuais, o que segura a atenção.
## Função estrutural — 1-2 frases: o papel do bloco na arquitetura.
REGRAS: seja LITERAL e visual (o doc serve pra reproduzir sem ver o
vídeo). Não invente o que não está nos frames/transcrição.
```

3. **Rodar com retry**: agentes de visão falham ~10-20% das vezes; o Claude roda até 3 rodadas repescando só os blocos sem arquivo no disco.

**Regra do prompt de análise:** exigir texto de overlay letra a letra e frases literais. É isso que transforma a análise em material reproduzível em vez de resumo.

## Passo 5 — Síntese: o DOC-MESTRE de modelagem

Com os 8 blocos analisados + transcrição completa + cortes.json, um único agente forte (o próprio Claude, com raciocínio) escreve o `MODELAGEM.md` com estas 9 seções:

1. **Arquitetura macro** — tabela: bloco | timestamps | função | % do tempo total. (VSLs profissionais costumam ter blocos de duração quase idêntica — isso é um dado, anote.)
2. **O método vendido** — nome, mecanismo central como cadeia lógica (`causa → sintoma → por que tudo falhou → solução`), promessa, prazo, entregáveis, preço, garantia.
3. **Escada de crenças** — a sequência de crenças que a VSL instala, em ordem, com o dispositivo usado em cada degrau. Esta é a seção mais valiosa: cada crença só é possível depois que a anterior foi aceita. A VSL nova PRESERVA esta espinha inteira.
4. **Dispositivos de retenção e edição** — ritmo de corte por bloco, tela verde/recorte, b-rolls, props físicos, prints de estudo, antes/depois, sussurro, CTA gestual, cores de legenda — QUANDO e COMO cada um aparece.
5. **A narradora** — quem é, aparência, figurinos POR SESSÃO de gravação, cenários, o que ela FAZ em cena (demonstrações físicas com timestamps).
6. **Pitch e oferta** — a estrutura do pitch minuto a minuto, ancoragem, bônus, garantia, urgência, CTAs com frases literais.
7. **Loops abertos** — tabela: onde abre, o que promete, onde fecha (e quais NUNCA fecham — urgência contínua).
8. **Mapa de compressão** — ver abaixo.
9. **Pontos fracos** — onde a referência perde força = onde a SUA versão fica mais forte (hook genérico, prova insuficiente pro volume prometido, falta de origin story, meio lento...).

## O que extrair de cada referência (o mapa, não a cópia)

- **Lead:** pergunta-hook com mecanismo estranho + promessa específica + risk-frame. (Doc 05 do módulo tem as regras da lead que segura.)
- **Escada CAUSA-RAIZ:** dor → causa oculta → "a culpa não é sua" → invalida as alternativas → insight → mecanismo → conclusão inevitável (a One Belief). É o coração de qualquer VSL de mecanismo.
- **História:** incidente de humilhação + deadline concreto.
- **Descoberta:** mentor/tradição + validação científica + teste íntimo + censura/inimigo.
- **Receita ABERTA:** a referência boa DÁ os ingredientes de graça e vende a CALIBRAÇÃO/dose exata — é daí que nasce o produto digital.
- **Pitch híbrido:** "quanto você já gastou" → ancoragem externa → "pagariam X" → "jamais cobraria isso" → PROPÓSITO (motivo pra ser barato) → preço EM TELA → escassez honesta → garantia estendida → bônus com valores → FAQ → encruzilhada de 2 caminhos.

## Alavanca-mestra (buscar SEMPRE uma)

Um fio único que amarre **história + mecanismo + nome do produto** numa coisa só. Exemplo do padrão: se o método tem um prazo (ex.: 21 dias), a origin story deve EXPLICAR esse número ("faltavam exatamente 21 dias pro evento que mudou tudo") — o prazo deixa de ser arbitrário e vira prova narrativa. Se a referência não tem alavanca-mestra, criar uma é a sua maior vantagem competitiva sobre ela.

## Mapa de compressão (ex.: 33min → 15min)

VSL de referência longa NÃO se corta por blocos — se comprime POR DENTRO, mantendo TODA a lógica:

- **Cortar:** repetições, re-explicações, tempo morto gestual, passo-a-passo de compra burocrático, detour que já foi coberto.
- **Manter intacto:** hook, metáfora física central, escada de crenças completa, provas com timestamp, ancoragem, técnica de fechamento.
- **Condensar:** listas de 8 viram listas de 3 (os itens mais polêmicos), diferenciais fundem em uma frase, cada bônus em ~30s.
- Formato da tabela por bloco: `duração original | % alvo | o que cortar | o que manter | o que condensar`.
- Sanidade: contar as crenças da escada antes e depois — a compressão certa perde MICRO-loops, nunca degraus.

## Manchetes e estudos reais (pesquisar JÁ nesta fase)

- WebSearch por matérias e estudos REAIS que sustentem os claims da VSL nova. Guardar as URLs — os prints são capturados na fase de assets (doc 04).
- **REGRA: nunca inventar endosso nem estudo.** A fala em áudio fica genérica ("uma atriz muito querida", "um estudo publicado em 2018") e o print REAL na tela carrega a especificidade. Prova real > prova gerada, sempre — em conversão e em compliance.
- Fallback: quando o estudo original bloqueia bot/print, uma matéria médica séria citando o estudo vale como print.

## Saída desta fase

```
analise/
  transcricao.srt / .txt
  cortes.json
  frames/f0001.jpg ... grid_01.jpg ... mapa.json
  blocos/bloco-1.md ... bloco-8.md (+ transcript_N.txt)
MODELAGEM.md   ← o doc-mestre. Toda decisão de roteiro/edição sai daqui.
```

Com o doc-mestre pronto e o SEU conceito aprovado (persona + ângulo + nome), siga pro doc 02.
