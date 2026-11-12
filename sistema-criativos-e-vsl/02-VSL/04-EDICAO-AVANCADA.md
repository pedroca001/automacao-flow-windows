# 04 — EDIÇÃO AVANÇADA ⭐ (o diferencial: as técnicas que fazem parecer editor humano)

> Qualquer um concatena clipes de IA. O que separa uma VSL que segura audiência é a camada de edição: a expert recortada falando SOBRE a prova, tela dividida, antes/depois que grita em miniatura, movimento de câmera liso, primeiro minuto denso. Este documento é o COMO e o PORQUÊ de cada técnica — todas rodando local, custo zero, via ffmpeg + PIL + RobustVideoMatting.

> 🔴 **Este doc é o COMO. O QUANTO, o ONDE e o que REPROVA estão em `06-EDICAO-DINAMICA-OBRIGATORIA.md`** (a régua de ≥12 trocas/min, o plano de edição obrigatório e o gate medido). Técnica sem régua vira "eu sei fazer, mas não fiz" — foi exatamente assim que uma VSL saiu com 5 minutos de expert parada. E a implementação de referência que aplica tudo isto a partir do plano é `scripts-referencia/montar_vsl.py`.

Cada técnica abaixo é declarativa no pipeline: você marca no spec/montagem QUAIS cenas recebem qual efeito (`RVM_PRINTS = {10: 11}`, `SPLITS = {...}`, `PARES = {...}`) e o script aplica. O seu Claude adapta os scripts de `scripts-referencia/` pro seu projeto.

---

## (a) REMOÇÃO DE FUNDO / fundo transparente — a expert flutuando sobre a prova

**O que é:** o clipe da expert falando vira uma versão TELA-VERDE (fundo removido por IA), e o ffmpeg recompõe: a pessoa recortada em cima de um fundo-prova (print de estudo, foto, anatomia, matéria). O espectador OUVE a explicação enquanto VÊ a prova — retenção alta nos trechos mais "aula" da VSL.

**Como:** [RobustVideoMatting](https://github.com/PeterL1n/RobustVideoMatting) (RVM, da ByteDance) rodando LOCAL — em Mac roda no MPS (GPU Apple), em PC na CUDA; ~1 min por clipe de 8s. O wrapper inteiro tem ~30 linhas (`scripts-referencia/rvm_matte.py`): decodifica o vídeo frame a frame via ffmpeg rawvideo, passa cada frame pela rede (`downsample_ratio=0.25`, estado recorrente entre frames = borda estável), compõe `foreground*alpha + VERDE*(1-alpha)` e re-encoda mantendo o áudio original.

```bash
RVM_DIR=~/RobustVideoMatting python3 scripts-referencia/rvm_matte.py clipe_expert.mp4 clipe_expert.green.mp4   # RVM_DIR = o clone do repositório com o peso .pth (ver 00-VISAO-GERAL.md)
```

Depois, a recomposição no ffmpeg — chromakey + despill + overlay sobre o fundo-prova com um zoom lento:

```bash
ffmpeg -y -loop 1 -t $DUR -i fundo_prova.png -i clipe_expert.green.mp4 -filter_complex "
[0:v]scale=2160:-2,zoompan=z='min(1.0+0.0004*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/6-(ih/zoom/6)':d=$((FRAMES)):s=1080x1920:fps=24[bg];
[1:v]chromakey=0x00ff00:0.24:0.08,despill=type=green,scale=490:-2[fg];
[bg][fg]overlay=x=W-w-6:y=H-h:shortest=1,format=yuv420p[v]" \
-map "[v]" -map 1:a -t $DUR -c:v libx264 -pix_fmt yuv420p -c:a aac cena_final.mp4
```

**As regras que importam (pagas em reprovação):**
- **A pessoa recortada vai no CANTO DIREITO, MENOR (~490px de largura em canvas 1080)** e ancorada no rodapé (`overlay=x=W-w-6:y=H-h`). O fundo-prova tem que APARECER INTEIRO — a narradora nunca cobre a prova. Narradora gigante no centro = matou o propósito do efeito.
- `despill=type=green` é obrigatório — sem ele fica um halo verde no cabelo.
- Chromakey `0.24:0.08` (similaridade:blend) é o par calibrado pro verde puro que o RVM gera; verde 100% sintético = chroma perfeito, é por isso que se compõe verde em vez de exportar alpha.
- Guardar o clipe original como `_flat.mp4` antes de substituir — a técnica é reversível e o QA compara.

## (b) TELA DIVIDIDA — b-roll/prova em cima, expert embaixo (quem fala carrega o áudio)

**O que é:** o quadro 9:16 dividido: metade de cima = b-roll/prova/still, metade de baixo = a expert falando. Usado no início da VSL (densidade visual) e em qualquer trecho onde a prova merece tela dividida em vez de cutaway.

**Como (horizontal, topo/baixo):** cada metade é escalada pra cobrir `1080x960` (`force_original_aspect_ratio=increase` + crop) e empilhada com `vstack` — com um divisor branco fino opcional. Variante validada: b-roll no topo com 40% da altura, expert com 60%.

**Como (vertical, lado a lado — ex. antes | agora):**

```bash
ffmpeg -y -i clipe_expert.mp4 -loop 1 -i antes.png \
  -i tag_antes.png -i tag_hoje.png -filter_complex "
[1:v]scale=540:1920:force_original_aspect_ratio=increase,crop=540:1920,setsar=1[left];
[0:v]crop=540:1920:270:0,setsar=1[right];
[left][right]hstack=inputs=2[sp];
[sp][2:v]overlay=x=30:y=260[s1];
[s1][3:v]overlay=x=570+((510-w)/2):y=260,format=yuv420p[v]" \
-map "[v]" -map 0:a -shortest -r 24 -c:v libx264 -pix_fmt yuv420p -c:a copy saida.mp4
```

**As regras:**
- **Quem fala CARREGA o áudio** — o still/b-roll nunca entra mudo sozinho; o áudio da fala segue contínuo (`-map 0:a` do clipe falado).
- O lado do clipe falado usa crop CENTRAL (`crop=540:1920:270:0`) pra não decepar o rosto.
- **Tags com PIL, não com drawtext:** gerar PNGs de rótulo ("ANTES" vermelho, "HOJE" verde) com `rounded_rectangle` semi-transparente + Arial Black — tipografia limpa, posicionamento por overlay. (Função `tag()` de ~10 linhas: mede o texto com `textbbox`, desenha caixa arredondada, salva RGBA.)
- Split de IMAGEM que vai receber zoom: cobrir a proporção-alvo ANTES do zoom (`scale=W*6:(H/2)*6:force_original_aspect_ratio=increase,crop=...`) — zoompan com `s=` não preserva proporção e ESMAGA a imagem.

## (c) ANTES/DEPOIS — a prova visual (onde mais se erra)

**Regras invioláveis:**
- **SEMPRE a MESMA pessoa.** NUNCA 2 gerações independentes ("antes" e "depois" de t2i separados = duas pessoas diferentes, prova morta).
- **i2i ENCADEADO no Flow:** identidade = frame-base da cena FALADA da depoente (do state) → i2i ref=identidade gera o **ANTES** ("same woman, casual phone photo on her WORST day, different clothes and different corner of the house from the video") → i2i ref=ANTES gera o **DEPOIS**.
- **O DEPOIS é uma FOTO NOVA** — outro dia, outra pose, outra roupa, outro canto da casa, "DRAMATICALLY transformed, difference OBVIOUS at a glance even at thumbnail size". NUNCA a mesma foto retocada (parece edição, mata a prova).
- **GATE DE CONTRASTE:** montar as duas lado a lado (hstack) e INSPECIONAR antes de usar. O contraste tem que gritar EM MINIATURA: antes = o pior dia (luz dura, aspecto carregado), depois = radiante mas crível. Fraco = REGERAR, sem exceção.
- Nicho de corpo: o "antes" tem o peso espalhado pelo CORPO INTEIRO (rosto cheio, braços, cintura, barriga MOLE e caída) — barriga redonda e firme lê como GRÁVIDA = reprovado. Prompt: "weight spread over the WHOLE body, clearly NOT pregnant, belly soft and saggy not round and firm".

**Na montagem (par de fotos):** slide de 5s — antes 2.2s → `xfade=wipeleft` 0.8s → depois 2s — MUDO, rodando como cutaway sobre a fala da PRÓPRIA depoente (par sobre a intro da depoente seguinte = incoerência narrativa, bug pago). As fotos "antes" também servem de FLASHES de choque no primeiro minuto (full-screen 0.8s).

**Variante em VÍDEO (a mais forte):** quando existem 2 clipes validados da mesma pessoa (dia 1 e dia N), recortar os dois (`crop` rosto inteiro + ombros, ex. `crop=iw*0.47:ih*0.94:iw*0.02:ih*0.03`) e montar LADO A LADO SIMULTÂNEO com rótulos "DIA 1" / "DIA 27". Movimento real dos dois lados, identidade garantida, transformação inegável. Close demais estoura a qualidade no scale — rosto inteiro + ombros é o enquadramento.

**Quando a geração de par falha 3x** (o modelo troca a pessoa ou não entrega a melhora): não insista no i2i — use a variante em vídeo ou reaproveite par validado de outra peça sua.

## (d) KEN BURNS SEM TREMER — o bug que denuncia edição amadora

**O problema:** o `zoompan` do ffmpeg move a janela em PIXEL INTEIRO. Em zoom lento isso vira um tremor visível (reprovado 3x em produção). É a "zika do zoompan".

**A solução definitiva (PIL, sub-pixel real):** renderizar cada frame no PIL com a janela de crop em coordenadas FLOAT + resample Lanczos — o `Image.resize(box=(x0,y0,x1,y1))` aceita float e interpola de verdade. Zoom LINEAR (velocidade constante, sem "pulso"). Script completo em `scripts-referencia/kenburns.py`:

```python
ken_burns("print_estudo.png", "insert_10.mp4", secs=5.0,
          W=1080, H=1920, z0=1.0, z1=1.14, anchor=(0.5, 0.42))
```

**Se PRECISAR usar zoompan** (ex.: sobre vídeo, onde o PIL não entra): supersample 6x antes (`scale=W*6:-2`) + zoom lento (`z='min(1.0+0.00045*on,1.08)'`). 2x AINDA treme; 6x fica liso. Pra zoom sobre clipe de vídeo com áudio preservado, 2x + `zoompan d=1` (1 frame de saída por frame de entrada) é o compromisso aceitável.

**Safe area:** arte com texto que recebe ken burns precisa de ~78px de margem interna — senão o movimento come o header/rodapé.

## (e) CUTAWAY — b-roll NUNCA em silêncio

A regra de ouro da fluidez: **a VSL nunca para de falar.** Demo/insert/b-roll não existe como cena solta — existe como CUTAWAY: o visual cobre os primeiros ~5s do clipe FALADO seguinte, com o áudio da fala contínuo por trás. Mínimo **2.4s do falante visível no fim** do clipe (o espectador precisa "voltar" pra quem fala). Implementação: trim do visual em `CUT_MAX=5.2s`, concat visual demo + resto do clipe falado, áudio = o do clipe falado inteiro. Zero som ambiente sozinho, zero silêncio.

## (f) PRIMEIRO MINUTO DE IMPACTO — cheio desde o frame 1

O diagnóstico que originou a técnica: talking head estático por 60s = o scroller reconhece "apresentação de vendas" e sai (queda de 44% até 1:20 numa lead real, consertada com estas regras).

- **00:00 JÁ CHEIO:** split screen desde o PRIMEIRO frame (expert numa faixa, b-roll na outra) — nada de entrar "depois".
- Split da expert: crop de uma faixa do frame (ex. `y=H/8..H/8+H/2`) no topo; b-roll de VÍDEO embaixo.
- **B-roll de vídeo com curiosidade amarrada na fala do momento** (o objeto misterioso, o ritual, o calendário) — imagem estática só pra ROSTOS: flashes de 0.8s das fotos "antes" (choque).
- **Zoom in/out alternado** nas cenas cheias (zoompan d=1 sobre supersample 2x, z linear 1.0↔1.06-1.08) — cada cena respira diferente.
- **Nenhum plano >6-8s sem trocar o estímulo** (b-roll, split, PIP, flash, zoom).
- Trilha ambiente em volume 0.10, fade in 1.2s/out 2.5s, loop. **SFX pontuais SÓ se casarem 100%** com a ação — SFX incongruente foi reprovado e removido; na dúvida, sem SFX.
- **Duração e áudio de cada cena PRESERVADOS** (efeitos só no vídeo) — assim os offsets de legenda e overlay continuam válidos.
- O arquivo `VSL-X_intro.mp4` substitui as cenas 1-N no concat da montagem.
- Prova visual no segundo ZERO: antes/depois já no primeiro beat, inimigo nomeado até ~0:16, expert NUNCA estática (sempre com PIP/split/b-roll ao lado).

## (g) PÁGINA EDITORIAL PRÓPRIA — em vez de print cru

Print cru de matéria/estudo real fica feio e ilegível no canvas do vídeo. A técnica: **montar a própria página editorial em PIL** (1080 de largura) com a informação REAL — header com nome de editoria + filete colorido, chapéu ("DERMATOLOGIA · SEUL"), manchete serifada grande em 2-3 linhas, subtítulo, **antes/depois real em caixas retrato (~496x600) com legenda de foto**, corpo de texto e assinatura. Fontes do sistema: Times New Roman (serifada, manchete/corpo) + Arial (sans, header/legendas). Depois, ken burns lento por cima (técnica d).

Regras: a INFORMAÇÃO é real (estudo/matéria verificável — doc 01); o layout é seu. Não imitar a marca de um veículo real — o header é uma editoria genérica ("SAÚDE & BELEZA"). +78px de safe area pro ken burns. O resultado lê como "saiu na imprensa" com legibilidade perfeita em qualquer canvas.

Prints reais continuam existindo (captura via browser headless, viewport mobile 430x932, remover banners de cookie via JS, crop do rodapé) — a página editorial é pro momento de DESTAQUE da prova; o print cru serve de insert rápido.

## (h) CROSSFADE + NORMALIZAÇÃO — a cola invisível

- **Crossfade de 0.25s em TODAS as transições de bloco/insert** (`xfade=transition=fade` no vídeo + `acrossfade` no áudio) — corte seco entre fontes diferentes lê como amador. (Jump cuts DENTRO do mesmo frame-base são a exceção: são estética, ficam secos.)
- **Normalizar TUDO pra 1080x1920/24fps/aac 48k ANTES do xfade** — clipes do Flow vêm 720x1280 e o xfade quebra com "Invalid argument" em resolução mista. Normalização é o passo 0 de qualquer composição.
- Punch-in como ritmo: clipe falado >4.6s ganha jump-cut com zoom 1.12 no meio (corta o clipe em 2, segunda metade com punch-in) — imita o ritmo de corte de ~3s das VSLs editadas à mão sem mexer no áudio.

---

## Checklist de aplicação (o que o Claude marca no plano de montagem)

| Técnica | Onde entra | Marcação |
|---|---|---|
| RVM fundo transparente | trechos "aula" com prova forte (estudo, anatomia) | `RVM_PRINTS = {cena_print: cena_falada}` |
| Tela dividida | primeiro minuto + prova que merece tela | `SPLITS` / intro |
| Antes/depois | bloco de depoimentos (par da própria depoente) + flashes na intro | `PARES = {cena_par: (nome, alvo)}` |
| Ken burns PIL | todo insert estático (prints, página editorial, telas de app) | inserts → clipe 5s |
| Cutaway | toda demo muda e todo insert | `DEMOS/INSERTS = {visual: alvo}` |
| Primeiro minuto | cenas 1-N do front | `VSL-X_intro.mp4` |
| Crossfade 0.25s | transições entre fontes distintas | no compose |

A execução disso tudo em ordem — com trim, legendas, overlays e QA — é o doc 05.
