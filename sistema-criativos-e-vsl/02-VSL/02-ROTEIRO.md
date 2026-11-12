# 02 — ROTEIRO (o formato que o pipeline parseia + as regras pagas a sangue)

> O roteiro não é um texto corrido: é um arquivo .md num formato FIXO que os scripts transformam em spec de geração, em legendas e em QA. Escrever fora do formato quebra o pipeline inteiro. E as regras de fala deste documento não são estilo — cada uma custou uma leva de clipes perdida até virar lei.

O comando pro seu Claude:

```
Leia 02-VSL/02-ROTEIRO.md e MODELAGEM.md. Escreva vsls/VSL-<NOME>.md no
formato parseável, transplantando a estrutura da referência pra minha
oferta: [descreva produto, persona, idioma, preço]. Antes de escrever,
ative suas skills de copywriting. Depois rode os greps de compliance e
me mostre o resultado.
```

---

## O formato do arquivo (o pipeline depende dele)

`vsls/VSL-<NOME>.md`:

```markdown
## BLOQUE 3 — A DESCOBERTA (cenas 41-58)
CENARIO: <descrição EM INGLÊS do frame-base do bloco: local, roupa, luz, pose neutra>

41. [EXPERT, tom acolhedor] "Fala completa da cena, entre dezesseis e vinte e seis palavras, sem reticências, com números por extenso."
42. [DEMO: close of two hands pouring dark liquid into a glass jar, no face visible]
43. [DEPOENTE-1, 58 anos, dona de casa, tom emocionado] "Fala completa da depoente na primeira pessoa, com detalhe concreto do antes e do depois, também entre dezesseis e vinte e seis palavras."
44. [SKIP: print real de estudo — insert de montagem, não gerar no Flow]
```

As regras do formato:

- `## BLOQUE N — TÍTULO (cenas X-Y)` abre cada bloco. **1 frame-base por bloco** (as cenas do bloco reusam o mesmo frame = jump cuts). O `CENARIO:` muda POR BLOCO e só com motivo narrativo (foi pra cozinha porque vai demonstrar algo).
- Cada cena: `N. [persona, tom] "fala"`. 🔴 **O "tom" é tom + GESTO + OLHAR, e varia cena a cena** (`[EXPERT, urgente, olhando direto na câmera]`, `[EXPERT, energia, inclinada pra frente]`, `[EXPERT, mostrando exatamente UM dedo pra câmera]`, `[EXPERT, chegando mais perto, quase sussurrando]`) — o parser injeta isso no prompt de cena; tag pobre = expert parada. Nunca 3 cenas seguidas com a mesma tag (lista e leis em `06-EDICAO-DINAMICA-OBRIGATORIA.md` §3). A numeração é global e nunca se renumera — cena adicionada depois entra com decimal (`95.1`, `95.2`); o parser aceita float e a montagem ordena por float.
- Tags especiais: `[DEMO: ...]` = clipe MUDO só de mãos/objetos (vira cutaway na montagem) · `[SKIP: ...]` = asset que NÃO se gera no Flow (print real, par antes/depois, tela de app — entram na montagem, doc 04/05). **Regra de densidade:** `[DEMO]`/`[SKIP]` amarrados na palavra da fala do momento, a cada 2-3 cenas nos 2 primeiros minutos e no máximo a cada 5-6 no corpo — é o roteiro que garante que a montagem tem com o que trabalhar (doc 06 §4).
- Só a expert fala fora dos blocos de depoimento. FAQ = perguntas em overlay de chat na tela, expert responde em áudio.
- 1 depoente por dor, nomes distintos por VSL (não repetir entre as VSLs do mesmo funil).

## Estrutura front (~14 blocos, 15-25min) — o esqueleto quando não há referência

Lead (≈10 cenas) → Prova intercalada (≈14) → História (≈18) → Escada causa-raiz (≈20) → Descoberta (≈16) → Teste íntimo (≈18) → Inimigo (≈10) → Receita aberta (≈12) → Nasce o produto (≈10) → Demo + future pacing (≈12) → Pitch (≈18) → Garantia + bônus (≈12) → FAQ em chat (≈12) → Encruzilhada (≈12).

Quando você MODELOU uma referência (doc 01), a estrutura vem de lá — esta é o fallback validado.

---

## REGRAS DE FALA (pagas a sangue — o Veo pune cada violação)

1. **≤26 palavras por cena E ≥16.** O clipe tem 8s: mais de ~26 palavras = o Veo TRUNCA o fim da fala; menos de ~14-16 = metade do clipe fica muda e o render é RECUSADO por vídeo silencioso. A janela 16-26 é a zona segura.
2. **NUNCA nome próprio em áudio.** Nem da expert ("Sou a doutora Fulana" = fail instantâneo), nem em 3ª pessoa ("o teste da Dra. Fulana" = 3 renders falhados seguidos), nem AUTO-nomeação de depoente ("Eu sou o Fulano" = dezenas de recusas). Nome existe SÓ em overlay/texto de tela. Em áudio: "a doutora", "essa mulher", "ele".
3. **NUNCA celebridade identificável em áudio.** "Uma das atrizes mais famosas de Hollywood" = fail; "uma atriz muito querida" = passa. O print real na tela carrega o nome — o áudio, nunca.
4. **Nome próprio TAMBÉM não entra no prompt visual da cena.** "the expert Fulana smiling" fez 15/15 cenas falharem em 3 rodadas seguidas; removido o nome do prompt → 100% na primeira. Persona nomeada só existe em docs e overlays.
5. **Zero reticências. Números por extenso.** ("doze quilos", nunca "12kg" — o TTS nativo do Veo lê dígito de forma imprevisível.)
6. **Palavra estrangeira/rara quebra a pronúncia.** Ou troca pelo equivalente local, ou introduz com aposto ("minha avó, minha *nonna*") e aceita o risco só ali.
7. **Fala que falha 2x+ na MESMA palavra = problema de CONTEÚDO, não de sorte.** Trocar a palavra por sinônimo (sentido idêntico, documentar a troca no roteiro com comentário). Padrões já mapeados: palavra que soa como termo técnico de vídeo ("estática"), construção mórbida, "guia" + nome. 8 recusas com tudo trocado = CORTAR a cena e absorver o beat nas vizinhas — não insistir.

## REGRAS DE COPY (as leis do que vende sem quebrar o funil)

1. 🔴 **CTA de clique SÓ junto do preço.** NUNCA "clica no botão aqui embaixo" antes da revelação do preço — na página, o botão só APARECE sob o player depois da ancoragem; antes disso a chamada aponta pra um botão que não existe. Retenção no meio da VSL = "fica comigo até o final", SEM mencionar botão/link. Chamadas de clique válidas: na oferta (preço em tela) e no CTA final.
2. **Preço NUNCA falado em áudio (no front).** "O valor que aparece na sua tela" — isso permite price-swap futuro trocando só um PNG, sem cirurgia de vídeo. Referência de custo só relativa ("dividido pelos seus vinte e um dias, menos que um café"). Exceção: upsell pode falar preço (doc 05).
3. **Produto personalizado: NUNCA "automático/algoritmo/formulário/gerado".** A sensação tem que ser: a expert faz especificamente pra cada pessoa ("meu método clínico", "eu analiso o seu caso"). Até o depoimento cético respeita isso ("como ela vai saber o que eu preciso sem me ver?" ✔ · "um formulário automático não pode saber..." ✘).
4. **Claims científicos: só o que EXISTE.** Estudo citado tem que ser real e verificável. Nunca inventar estudo, nunca inventar número de prova social específico ("doze mil mulheres" inventado = reprovado; "milhares" = ok).
5. **Nome do produto: fonética do idioma-alvo manda, e valida com o DONO antes de gerar.** Nome reprovado depois de pronto = re-render de tudo que o fala. E o nome só aparece em áudio na revelação/garantia/resumo (as referências campeãs seguram o nome por 15+ minutos); o mecanismo fica sem nome próprio até lá.
6. **Coerência áudio-visual:** se a fala diz "ela pediu pra não mostrar o rosto", o clipe não pode mostrar o rosto. A solução barata é mudar a COPY, não escurecer o vídeo.
7. **Coerência de persona cultural:** revisar a 1ª pessoa (uma expert estrangeira não fala do próprio povo em 3ª pessoa errada).

## Greps de compliance (obrigatórios, ANTES de gerar qualquer clipe)

```bash
grep -in "automátic\|algoritmo\|generado\|formulário" vsls/VSL-X.md
grep -in "soy la doctora\|sou a doutora\|eu sou o \|eu sou a " vsls/VSL-X.md
grep -n  "<NomeDaExpert>" vsls/VSL-X.md     # só pode aparecer em linha de overlay
grep -n  '\.\.\.' vsls/VSL-X.md             # zero reticências
grep -in "clica no botão\|botão aqui" vsls/VSL-X.md  # só nas cenas de oferta/CTA final
grep -in "R\$\|dólares\|reais" vsls/VSL-X.md         # preço não pode estar em FALA
```

Qualquer hit fora do lugar = corrigir antes de seguir. Depois dos greps, um **review brutal por um segundo agente** (subagente do Claude ou outro modelo): idioma, lógica, física das cenas (dá pra filmar isso em 8s?), compliance. Triagem das sugestões — nem tudo se acata; padrões validados do nicho o revisor externo não conhece.

## O TRANSPLANTE de persona (entre idiomas e nichos)

Modelar não é traduzir. O que se preserva e o que se troca:

| PRESERVA (o esqueleto) | TROCA (a pele) |
|---|---|
| Escada de crenças completa, na ordem | Persona (idade, história, sotaque, figurino) |
| Loops: onde abre, onde fecha | Nome e "sabor" do mecanismo (renomeado pro seu produto) |
| Estrutura do pitch (ancoragem → propósito → preço → garantia → bônus) | Referências culturais (moeda, comida, instituições, gírias) |
| Ritmo por bloco (meta de cortes) | O inimigo — **calibrado**: nunca atacar a instituição que dá autoridade à sua persona |
| Dispositivos de edição (onde entra prova, demo, sussurro) | Provas (estudos/matérias REAIS do novo idioma/nicho) |
| Prazos e promessas SE sustentáveis | Depoentes (sotaques regionais distintos do novo país) |

Regra do inimigo: se a sua persona é uma médica, o inimigo não pode ser "os médicos" — é a indústria X, o mito Y. A autoridade da persona e o inimigo nunca podem se anular.

E a mesma disciplina da voz: cada persona ganha um bloco `[VOICE]` de prosódia nativa (doc 03) — o transplante de idioma vive ou morre na naturalidade da fala.

## Saída desta fase

`vsls/VSL-X.md` aprovado (greps limpos + review triado + seu OK no conceito). Ele é a fonte única: o spec de geração (doc 03), as legendas e o QA de fala (doc 05) derivam TODOS deste arquivo. Mudou uma fala depois? Edita AQUI primeiro, sempre — senão a legenda sai velha.
