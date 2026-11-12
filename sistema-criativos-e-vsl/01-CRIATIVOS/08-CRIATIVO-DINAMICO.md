# 08 — CRIATIVO DINÂMICO 🔴 (nunca 3 quadros iguais seguidos — o padrão que fez "os melhores até hoje")

> **Por que este documento existe:** um dono deste sistema gerou 15 criativos e recebeu **12 iguais** — a mesma pessoa, na mesma posição, falando de frente do começo ao fim, mudando só a frase. Isso não é uma leva: é um criativo com 12 legendas. O algoritmo aprende em horas que é o mesmo anúncio, o CPM sobe, e o teste não testa nada.
>
> O padrão abaixo nasceu de uma leva de 25 criativos aprovada como "os melhores até hoje" e do gancho de choque (doc 07). Ele tem 5 peças, e as 5 são obrigatórias: **gancho de choque · persona + cenário marcantes · corpo com plano por clipe (T/D/I/L) · punch-in · montagem sem silêncio.** Se você (Claude) está planejando uma leva e a tabela da seção 6 não está preenchida, você ainda não planejou.

---

## 1. O que faz um criativo ser dinâmico (na ordem que importa)

1. **Gancho = impacto + variedade + coisa estranha** (doc 07). 25 ads = 25 aberturas diferentes.
2. **Pessoa marcante + cenário que prende.** Não é "uma mulher na cozinha". É uma pessoa que se olha duas vezes na rua, num lugar que se olha duas vezes na tela.
3. **Corpo DINÂMICO — cada clipe tem um TIPO, e nunca 3 seguidos iguais.**
4. **Punch-in jump-cut** em todo clipe do corpo > 4,6s.
5. **Montagem que não respira demais:** zero silêncio > 0,3s, corte por FALA (gap entre palavras > 0,55s aparado), vídeo e áudio terminam juntos, ≥ 60s, 1080x1920.

---

## 2. Persona + cenário marcantes (é no MASTER que se decide)

O master (imagem-mestre da persona) ancora TODOS os clipes do ad. Master sem graça = ad inteiro sem graça, e não há montagem que salve.

**A regra:** *"pessoas que chamem atenção, cenário que chame atenção"*.
- **Pessoa:** cabelo e maquiagem feitos, roupa de cor forte ou de tecido nobre (seda, linho), um detalhe (brinco, corrente, relógio). Presença confiante. **E ainda assim real:** textura de pele com poros, leve assimetria natural — não é modelo de banco de imagem, é a pessoa bonita da vida real. Para nicho de dor física (peso, dor, pele), a **mensageira** é bonita e em forma; **corpo comum só na depoente do antes/depois** (é a lei da mensageira, doc 05).
- **Cenário:** luz forte e quente, pedra, mármore, madeira clara, uma vista (cidade, mar, jardim), um terraço, um carro conversível, um café de calçada, um banheiro de mármore. **Nunca** "sala genérica com parede branca". O cenário é metade do impacto.
- **1 pessoa + 1 cenário por ad, 25 rostos diferentes em 25 ads.** Lei da casa: variar o rosto. Duas personas iguais em ads diferentes = o algoritmo agrupa e o teste morre.

**Bloco LOOK (reusar em toda persona, adaptando nacionalidade/idade):**
```
polished photo-ready look: styled hair, natural but visibly done makeup with defined brows and lips,
an elegant confident presence that turns heads, realistic skin texture with visible pores and slight
natural asymmetry, the kind of woman people look at twice in the street.
```

**Bloco CRITICAL (anti-equipamento, anti-recusa — vai no master):**
```
The shot is a fixed, locked-off frame with nobody holding anything and no selfie arm. She is
well-groomed and elegant, the place is attractive, tidy and filled with warm bright light, NOT drab,
NOT gloomy. ABSOLUTELY CRITICAL: the room is EMPTY of any recording equipment: NO camera, NO DSLR,
NO tripod, NO light stand, NO microphone, NO phone, NO tablet, NO laptop, NO screen. An anonymous
face that does not resemble anyone famous.
```

🔴 **A descrição do master TEM que levar cenário + roupa explícitos.** Uma leva saiu com **21 ads da mesma camisa azul no mesmo apartamento** porque o master só descrevia o rosto e o gerador "completou" igual em todos. `descricao_visual` = pessoa **e** roupa; `cenario` = lugar **e** luz. Sem exceção.

**Nunca nomear câmera** ("camera propped up" desenhou uma DSLR na mesa) — use "fixed, locked-off frame". **Nunca descrever parte do corpo** (mão, pele, "slim", "toned", "glowing", "mouth open") — dispara recusa; gênero se resolve no sujeito da ação.

---

## 3. O corpo: cada clipe tem um TIPO (T / D / I / L)

| Tipo | O que é | Como se prompteia (adiciona ao `acao`) |
|---|---|---|
| **T** — talking, enquadramento variando | ela falando, mas **cada T com um enquadramento diferente** | `T-close`: *"tight close-up: her face and shoulders fill the whole frame"* · `T-aberto`: *"wide shot: she is seen from the waist up, the whole setting visible around her"* · `T-3/4`: *"three-quarter medium shot: she stands at the left third of the frame turned toward the right, then looks into the lens"* · `T-cta`: *"medium shot, one arm fully extended pointing straight down at the bottom edge of the frame"* |
| **D** — demonstrando | ela **faz** enquanto fala: verte, espreme, mexe, bebe, segura o objeto ao lado do rosto, aponta o antes e o depois | *"medium shot at the counter: she tips the bottle into a tall glass while a spoon of powder waits beside it, the glass beginning to fizz, speaking to the lens"* · *"close-up: she lowers the glass from her lips, a trace of foam on the rim"* · *"close-up: she holds the glass up beside her face"* |
| **I** — insert sem rosto, voz off | mãos e objetos, **a voz continua**: o *device* do ad (o objeto da promessa) · o **mecanismo grotesco** (o antes × depois do mecanismo: copo turvo com lodo × copo cristalino fervendo) · a **prova/resultado** | *"Photorealistic insert frame, hands and objects only, no face. macro on the marble: two tall glasses side by side, the left one full of murky brown water with grey sludge settling and greasy film on top, the right one crystal clear and fizzing hard with white foam; a hand slides the clear glass forward"* |
| **L** — outro lugar do mesmo cenário | a mesma pessoa, mesma roupa, **noutro canto** (da bancada pra janela, do sofá pra varanda) | *"same woman, same outfit, now standing by the window of the same room, leaning on the frame, speaking to the lens"* |

🔴 **Todo T leva `DIFFERENT FRAMING FROM THE REFERENCE. FRAMING AND POSE ARE NEW.`** — a âncora do master congela a pose; sem esta frase, os 8 clipes saem com o mesmo enquadramento e você está de volta ao criativo parado. (O `scripts/gerar_specs.py` injeta isso sozinho a partir do campo `tipo`.)

**Ordens que funcionaram (use como esqueleto, não como fôrma):**
- **LONGO (14 clipes, ~1m50):** `G · T-close · I-device · T-aberto · D-verter · I-grotesco · T-close · D-beber · T-cta · I-resultado · L · D-segurar · T-3/4 · T-cta`
- **CURTO (8 clipes, ~64s):** `G · T-close · I-device · D-verter · L · I-grotesco · D-beber · T-cta`

(`G` = o gancho do doc 07, que é o clipe 1.) Regra-mãe: **nunca 3 quadros seguidos do mesmo tipo/enquadramento.** O `gerar_specs.py` avisa quando acontece.

**Insert com voz off:** o clipe I não tem rosto, mas tem a fala da persona. No `leva.json`, cena I = `"persona": "n1"` (pra voz) + `"tipo": "I"` — o script tira a pessoa do prompt de imagem, mantém a voz e escreve *"off-camera narration, no person visible"*. Cabeçalho do insert é **mínimo** (cabeçalho longo dispara recusa).

**Onde entra o produto:** o *device* (o objeto que encarna a promessa) aparece no gancho, num I no meio, e num D perto do CTA. Três vezes, três jeitos.

---

## 4. Punch-in jump-cut (o ritmo das VSLs editadas à mão)

Clipe do corpo > 4,6s: corta no meio, e a 2ª metade entra com **zoom 1,12** (crop centralizado, olho a 30% do topo, `scale` de volta pra 1080x1920). É um corte visual sem trocar conteúdo — imita o corte de ~3s da edição humana. Áudio intocado. **Zoom fixo, não animado** — por isso não treme.

```python
def punch_in(path, z=1.12, min_dur=4.6):
    d = dur(path)
    if d < min_dur: return
    mid = d/2; W, H = dims(path)
    cw, ch = int(W/z//2*2), int(H/z//2*2)
    fc = (f"[0:v]trim=0:{mid:.2f},setpts=PTS-STARTPTS[a];"
          f"[0:v]trim={mid:.2f},setpts=PTS-STARTPTS,crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})*0.30,scale={W}:{H},setsar=1[b];"
          f"[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]")
    # ffmpeg -i path -filter_complex fc -map [v] -map 0:a -c:a copy …
```

Está ligado por padrão em `scripts/montar_leva.py` (`PUNCH_IN=1`; desligue com `PUNCH_IN=0`). **O gancho (clipe 1) fica inteiro** — o impacto dele é a ação, não o corte.

---

## 5. Montagem que não respira demais

Além do que `montar_leva.py` já fazia (trim por whisper, concat, legenda do roteiro, CTA nos últimos segundos):
- **Corte por FALA:** gap entre duas palavras > 0,55s é aparado pra ~0,30s (whisper por palavra). É o que separa "gente falando" de "IA esperando o próximo prompt".
- **Zero silêncio > 0,3s** a -25dB (loop até limpar; os clipes de IA têm ruído ambiente que engana o `silencedetect` a -35dB).
- **Vídeo e áudio terminam juntos** (≤ 1,5s de diferença) · **≥ 60s** · 1080x1920/24fps.
- **Legenda da casa:** Arial amarela, contorno preto, caixa baixa, terço inferior, sem fundo, blocos curtos. Karaoke com fundo colorido e caixa alta foi testado e reprovado como "fora do padrão".
- **CTA:** pílula amarela pulsando + seta, nos últimos 8-10s. Headline em faixa no topo é opcional (`SEM_HEADLINE=1` desliga) — em muitos nichos o vídeo escalado não tem headline dentro do vídeo; a headline vai no texto do anúncio.

---

## 6. A TABELA-PROVA DA LEVA (preencha ANTES de gerar — é o plano que o dono aprova)

Uma linha por ad. Sem duas linhas parecidas.

| id | persona (quem + roupa) | cenário | gancho: mecânica · família · objeto · verbo | plano do corpo (tipos em ordem) | device do ad | registro |
|---|---|---|---|---|---|---|
| AD-01 | mulher 50+, blusa de seda marfim, brinco dourado | cozinha de mármore com vista da cidade | ESTRANHO · quantidade · caixa de sapato cheia de caixinhas de remédio · despeja no lixo | G·T-close·I-device·D-verter·L·I-grotesco·D-beber·T-cta | copo de tônico borbulhando | próspero |
| AD-02 | … | … | SPLIT · escala · pote do tamanho de um balde · abraça | … | … | dor |

**Regras da tabela:** 4 mecânicas de gancho distribuídas · 5 famílias de choque distribuídas · **nenhum objeto repetido** · **nenhum verbo repetido** · 25 rostos/cenários diferentes · registro variado (próspero/neutro · dor · pedagógico/autoridade — numa leva boa: ~55% / 30% / 15%) · **um teste por vez** (se está testando gancho, mantém o resto; se está testando corpo, mantém o gancho).

O `gerar_specs.py` confere o que dá pra conferir por código (mecânicas, tipos repetidos, contagem de choque, personas repetidas) e **avisa**. A tabela é o que você mostra pro dono antes do primeiro submit.

---

## 7. Leis de prompt (custaram horas — não relaxar)

- **Cabeçalho longo dispara `UNSAFE_GENERATION`.** Gancho e inserts vão com prompt **mínimo**. Prompt de cena < ~600 caracteres.
- **Nunca descrever parte do corpo** (mão, pele, "slim/toned/glowing", "mouth open").
- **Nunca nomear câmera.** "fixed, locked-off frame".
- **Master leva cenário + roupa** (senão 21× a mesma camisa azul).
- **Âncora congela o enquadramento:** todo T e todo L levam "FRAMING AND POSE ARE NEW / DIFFERENT FRAMING FROM THE REFERENCE".
- **100% inglês no prompt visual**, só a `fala` na língua do público. Acento/palavra da língua do público dentro do prompt EN = erro (o script avisa).
- **Sem nome de pessoa real na fala** — 6/6 falhas de render tinham o nome, 0/67 sem. "O médico da TV", "esse nutricionista".
- **Sem palavra médica pesada empilhada** ("obesidade" → "sobrepeso"; nunca termo médico + marca-conceito + "queimar gordura" na mesma frase) — o gerador recusa o render.
- **Sem texto legível no quadro** ("labels blank / turned away") — rótulos saem sozinhos e saem errados.
- **Recusa de imagem 2×?** A/B em 1 minuto: mude UMA coisa no prompt e reenvie. **Recusa de clipe 3× com imagem boa** = palavra na fala; 8× = reescrever o beat.

---

## 8. Checklist da leva dinâmica

- [ ] Tabela-prova preenchida e mostrada pro dono (seção 6)
- [ ] 25 rostos + 25 cenários diferentes; master com cenário + roupa explícitos; bloco LOOK + CRITICAL
- [ ] Gancho de choque por ad (doc 07), 4 mecânicas distribuídas, choque contado
- [ ] Corpo com `tipo` em toda cena; nunca 3 iguais seguidos; todo T/L com "DIFFERENT FRAMING"
- [ ] Insert I com voz off e cabeçalho mínimo; device 3× no ad
- [ ] Punch-in ligado; gancho inteiro
- [ ] Montagem: corte por fala, zero silêncio > 0,3s, v×a ≤ 1,5s, ≥ 60s
- [ ] Grade de frames dos masters E das cenas olhada antes do submit (gate)
- [ ] `scripts/medir_ritmo.py finais/` aprovou (≥ 10 trocas/min, maior plano medido ≤ 9s — os "melhores até hoje" mediram 14-16/min e 7-8s)

> O dono deu um exemplo? Aplique o **princípio** do exemplo à leva inteira — não o exemplo. "Mulher com objeto gigante" repetido 25 vezes é tão parado quanto "mulher falando" repetido 25 vezes.
