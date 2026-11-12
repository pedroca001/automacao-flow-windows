# 05 — QA E AS LEIS ANTI-ERRO

> **Por que este doc existe:** cada lei aqui custou uma leva, uma madrugada ou um ad reprovado pelo dono do tráfego. O gate de 3 camadas é o pedágio obrigatório de TODO ad; as leis são o conhecimento consolidado de centenas de gerações. Seu Claude deve carregar este doc em TODA sessão de produção. Você (operador) deve conhecer as leis pra cobrar — o sintoma de cada uma está descrito exatamente pra você reconhecer quando aparecer.

## O prompt de QA

```
Leia 01-CRIATIVOS/05-QA-E-LEIS.md e rode o gate de 3 camadas em todos os
finais de criativos/LEVA-<data>/. Me devolva a tabela: ad → duração →
silêncios → resolução → veredito visual → veredito de fala → APROVADO ou
REPROVADO (com a lei violada e o clipe culpado).
```

---

## O GATE DE 3 CAMADAS (nenhum ad sai sem as três)

### Camada 1 — TÉCNICA (automática)
```bash
# duração: 60-100s
ffprobe -v error -show_entries format=duration -of csv=p=0 AD-FINAL.mp4

# silêncio: ZERO trechos ≥0,3s a -25dB (o limiar certo pra clipe de IA — a -35dB o ruído ambiente esconde o buraco; -35dB/1.0s era a régua antiga, grossa demais)
ffmpeg -i AD-FINAL.mp4 -af silencedetect=noise=-25dB:d=0.3 -f null - 2>&1 | grep silence

# resolução: 1080x1920
ffprobe -v error -select_streams v:0 -show_entries stream=width,height -of csv=p=0 AD-FINAL.mp4

# integridade: abre sem erro
ffprobe -v error AD-FINAL.mp4
```
Reprova se: <60s ou >100s · qualquer silêncio detectado · resolução errada · qualquer erro do ffprobe.

```bash
# ritmo (Atualização 04): trocas de estímulo/min, maior plano parado, silêncio >0,3s, vídeo×áudio
python3 scripts/medir_ritmo.py finais/     # 🟢 ≥10/min e maior plano ≤9s · 🔴 = volta ao plano
```
E o **gate de VARIEDADE da leva** (antes de gerar, no `gerar_specs.py`): sem gancho, sem tipo, 3 tipos iguais seguidos, mecânica de gancho dominando, choque baixo, persona repetida — cada aviso é uma leva parada anunciada (docs 07/08).

### Camada 2 — VISUAL (grade + frames cirúrgicos)
```bash
# grade de 1 frame a cada 3s do FINAL
ffmpeg -i AD-FINAL.mp4 -vf "fps=1/3,scale=270:-1,tile=8x3" GRADE.jpg
```
O Claude LÊ a grade e confere: anatomia correta (2 braços!) · rosto consistente do primeiro ao último frame · prop presente nas cenas que o citam · foto-prova NÍTIDA (nunca borrada) · sem moldura de celular/status-bar · faixa de headline presente e dentro da faixa · legenda legível.

**⚠️ A grade NÃO basta pra efeitos pontuais.** Carimbo que entra aos 35s, tag de pós-edição, gesto de 1 segundo — a amostragem de 3s pula. Todo efeito de pós-edição listado no spec ganha um frame cirúrgico NO timestamp esperado. (Caso real: um gesto obsceno de 1s do gerador passou pela grade e foi pego por frame cirúrgico.)

### Camada 3 — FALA/VOZ (whisper por clipe)
- Whisper de CADA clipe contra a fala do spec. Similaridade (dice de bigramas) **< 0.60 = colisão** — o clipe tem a fala de OUTRA cena (ver lei do submitter único, doc 04). É a ÚNICA camada que pega clipe cruzado quando as cenas compartilham o frame-base.
- Antes de comparar, normalizar números por extenso↔dígito nos dois lados ("trinta anos" vs "30 anos" — sem isso, clipe perfeito reprova).
- Em diálogo de 2 pessoas: medir o f0 (pitch mediano) de cada falante — coadjuvante a <35Hz da protagonista = mesma voz pro ouvido, re-rolar. E tirar uma tira de frames de CADA rosto (`crop` no rosto + `tile`) pra confirmar que só a falante mexe a boca.

---

## AS LEIS ANTI-ERRO (cada uma com o porquê e o sintoma)

### Leis de estrutura do criativo

**LEI 0 — O gancho é entregável SEPARADO e o corpo é DINÂMICO (Atualização 04).**
*Porquê:* gancho escrito como "cena 1" vira pessoa parada falando por inércia; corpo sem tipo por cena vira o mesmo enquadramento 8 vezes. Uma leva de 15 saiu com 12 iguais e uma de 25 com 25 ganchos idênticos — as duas reprovadas inteiras.
*Sintoma:* os finais parecem o mesmo vídeo com legendas diferentes; CPM sobe em horas; o teste "não testa nada". Regra: `01-CRIATIVOS/07-GANCHOS-DE-CHOQUE.md` + `08-CRIATIVO-DINAMICO.md`; medida: `scripts/medir_ritmo.py`.

**LEI 1 — Fala no SEGUNDO ZERO, sempre.**
*Porquê:* imagem mudando sem voz = o dedo passa. A prova visual de abertura entra COM a narradora falando por cima desde o primeiro frame.
*Sintoma:* hook "cinematográfico" mudo de 2-3s no início; hook-rate afunda.

**LEI 2 — Mínimo 60s, alvo 60-100s.**
*Porquê:* criativo de VSL precisa construir o clique (problema → mecanismo → prova → ponte). 28-32s não constrói — uma leva inteira já foi descartada por isso. Os campeões espionados rodam 60-220s.
*Sintoma:* CTR até ok, mas conversão da VSL péssima — o clique chegou frio.

**LEI 3 — IMPACTO VISUAL no frame 1.**
*Porquê:* o frame 1 é o outdoor do ad; composição banal não para o dedo. E o impacto precisa de física real e proporção crível — bizarrice implausível derruba a confiança.
*Sintoma:* frame 1 = pessoa parada em fundo neutro; hook-rate no chão.

**LEI 4 — Criativo MONTADO, não cabeça-falante. 1 ideia por ad.**
*Porquê:* cada cena = lugar + ação + objeto. Transformação MOSTRADA (a conta VENCIDA que vira PAGA), não narrada. E um ad carrega UMA ideia — dois ganchos no mesmo ad = nenhum gancho.
*Sintoma:* "os ads ficaram todos bem parecidos" — pessoa sentada falando 60s, só o texto muda.

**LEI 5 — Variação = trocar o ESPETÁCULO (e o CORPO), não só o hook.**
*Porquê:* trocar avatar/cenário com os mesmos beats produz o MESMO ad de roupa nova. O teto de variação só rompe trocando o que a câmera mostra e a história que entra. Corolário: variar o CORPO do ad, não apenas a primeira frase.
*Sintoma:* 10 "variações" com performance idêntica; fadiga em dias.

**LEI 6 — Headline = promessa concreta com NÚMERO, e é a SEGUNDA ponta.**
*Porquê:* headline vaga ("descubra o segredo") não trabalha. Promessa/curiosidade concreta com número-tempo-payoff, ≤46 caracteres, na voz da tribo. E NUNCA repete a primeira fala — são DOIS ganchos, desperdiçar um é jogar metade do ad fora.
*Sintoma:* headline que é um "conceito" bonito; ou headline = legenda da primeira fala.

**LEI 7 — Mensageira bonita e em forma (a narradora É a prova ambulante).**
*Porquê:* quem narra a promessa carrega a promessa no corpo — aparência aspiracional para o dedo. Corpo comum fica SÓ pra depoente do antes/depois (a prova da transformação), nunca pra quem narra. É o princípio da prosperidade: o cenário e a pessoa provam silenciosamente o resultado.
*Sintoma:* "avatar realista comum demais" — tecnicamente perfeito, ninguém para.

**LEI 8 — Coerência de persona + prosperidade no cenário.**
*Porquê:* cenário, roupa, paleta e resultado prometido falam a língua do MESMO avatar. E nunca botar pobreza em tudo: o padrão vencedor é próspero-mas-atingível; miséria no cenário nega a promessa.
*Sintoma:* ad "certinho" que não converte — o espectador não se projeta.

### Leis de formato

**LEI 9 — RVM/tela-verde: pessoa AO LADO, prova SEMPRE visível.**
*Porquê:* no formato narradora-sobre-prova, a prova É o gancho. Narradora centralizada cobre a prova = dispositivo perdido.
*Regra:* narradora no canto direito, ~490px de largura, prova inteira visível em TODAS as imagens da sequência.
*Sintoma:* ads desse formato reprovados em bloco no gate final.

**LEI 10 — Moldura de celular NUNCA.**
*Porquê:* o ad já é visto num celular; vídeo-dentro-de-celular desperdiça metade da tela e grita "anúncio". Vem de prompts com "phone footage / filmed on iPhone".
*Defesas:* FRAME RULE nos blocos globais (full-bleed edge to edge) + gate de frames reprova borda de device + se escapar, crop/zoom na montagem.
*Sintoma:* frame com barra de status, notch ou borda arredondada de device.

**LEI 11 — Split: contraste REAL, imagem própria, e só onde o gancho não tem visual próprio.**
*Porquê:* split com metades parecidas não comunica nada; a mesma imagem de topo reusada em 5 ads = 5 ads iguais no scroll; e hook de reação física NÃO leva split — a cara É o espetáculo.
*Sintoma:* leva inteira "com a mesma cara" no feed.

**LEI 12 — Cutaway de print: tela cheia limpa ou não entra.**
*Porquê:* print cobrindo metade de um rosto é lixo visual.
*Regra:* cutaway em tela cheia com fundo escuro, headline preservada por cima, e a falante VOLTA ao quadro ≥2,4s antes do fim do bloco.

**LEI 13 — Diálogo de 2 pessoas: 1 fala por clipe + punch-in + gate de timbre.**
*Porquê:* o gerador não segura atribuição de boca/voz com 2 pessoas no quadro — em algum take a ouvinte mexe a boca ou herda a voz da outra. A solução é determinística, na EDIÇÃO, não no prompt (receita R2, doc 03).
*Sintoma:* vozes trocadas; "as duas falando"; as duas com a MESMA voz.

### Leis de prompt (o que quebra o gerador)

**LEI 14 — Nome próprio/celebridade no prompt = render FALHA.**
*Porquê:* o filtro de pessoa nomeada do Veo bloqueia 100% das vezes — no `cena_visual` E na FALA. "Aquele ator famoso" como sujeito direto da fala também dispara.
*Fix:* pessoas descritas genericamente ("an ordinary anonymous Brazilian man in his fifties"); o peso específico (nome, série, "ao vivo") vai na HEADLINE e na legenda queimada — texto de pós-edição não passa por filtro nenhum e não perde força.
*Sintoma:* a mesma cena falhando 3-4x seguidas enquanto as outras passam.

**LEI 15 — Reticências ("...") na fala = áudio garbled.**
*Porquê:* o Veo interpreta "..." como espaço pra improvisar — sai fala inventada ou embolada.
*Fix:* pausa = vírgula ou ponto. Nunca reticências no prompt de fala.
*Sintoma:* clipe com palavras que não existem no roteiro; whisper acusa texto estranho.

**LEI 16 — Prop delicado/articulado: a pessoa NÃO manipula.**
*Porquê:* o Veo buga a física de objetos complexos em movimento — telefone de fio entorta, óculos derretem na mão.
*Fix:* o prop fica PARADO na mesa; a pessoa gesticula PERTO, aponta, pousa a mão. Prompt: "PHYSICS LOCK: the prop rests perfectly still... she NEVER lifts or manipulates it". Prop robusto simples (papel, caderno, toalha) pode ser manuseado.
*Sintoma:* objeto se deformando/sumindo no meio do clipe.

**LEI 17 — Palavras sensíveis no prompt = policy block silencioso.**
*Porquê:* termos como "censorship" no prompt de vídeo, ou falas com termos sensíveis de idade/corpo, derrubam a geração — e trocar UMA palavra não resolve.
*Fix:* descrever o efeito, não o conceito ("marked with a red X of two crossed tape strips" em vez de "censored"). Fala recusada 4x = reescrever a frase ESTRUTURALMENTE e trocar o frame junto.
*Sintoma:* recusa persistente na mesma cena após retries.

**LEI 18 — Palavra no prompt CHAMA o elemento indesejado.**
*Porquê:* "bank" no prompt gera fachada com letreiro "BANCO BANK" errado, mesmo com "NO signage"; "smartphone front camera" gera braço de selfie; contagem nos dedos gera gesto obsceno de vez em quando.
*Fix:* tirar a palavra-gatilho e descrever genericamente ("busy commercial pedestrian street") · câmera sempre APOIADA · mãos abaixo do peito.
*Sintoma:* letreiro errado, 3º braço, dedo do meio aos 35s (caso real, pego só por frame cirúrgico).

**LEI 19 — Identidade entre gancho e corpo = MESMA referência de imagem.**
*Porquê:* frames gerados de referências diferentes = o ad começa com uma mulher e termina com outra. Figurino e luz também não se seguram sozinhos entre blocos.
*Fix:* mesma ref de identidade (o frame aprovado, re-enviado como referência) no gancho E no corpo; cena de bloco novo repete "wearing the SAME <roupa>" + a luz explícita.
*Sintoma:* rosto/roupa/hora do dia trocando entre cenas do mesmo ad.

### Leis de pipeline (o que quebra a máquina)

**LEI 20 — MP4 sem moov atom = corrompido com cara de saudável.**
*Porquê:* montagem morta por timeout grava o arquivo com tamanho normal mas sem o índice — não abre em player nenhum. O `ls` não denuncia.
*Fix:* toda entrega termina com `ffprobe -v error` em TODOS os finais; montagem longa roda em background, nunca com timeout curto.
*Sintoma:* o arquivo está lá, com 27MB, e quem descobre que não abre é quem for subir o ad.

**LEI 21 — Asset baixado: conferir o CONTEÚDO, nunca só o tamanho.**
*Porquê:* curl pode salvar uma página de erro com o nome do arquivo pedido.
*Fix:* `file` no arquivo + validar `size > 200KB` em vídeo (14 bytes/HTML = sessão expirada).
*Sintoma:* "vídeo baixado" que é um HTML de erro 404.

**LEI 22 — Gerador de spec termina com o teste de placeholder.**
*Porquê:* um bug de template (f-string não interpolada) manda "{CENARIO}" LITERAL pro prompt — 12 cenas com luz/lugar errados, 2 rodadas de re-roll.
*Fix:* `grep -o "{[A-Z_]*}" specs/*.json` tem que voltar VAZIO. É o teste mais barato de toda a pipeline.

**LEI 23 — Gate de frames ANTES de animar, sempre.**
*Porquê:* frame ruim animado = 8s de vídeo ruim + fila de espera + retrabalho. Olhar a grade custa 2 minutos.
*Ordem fixa:* masters → scenes → GRADE → conferir CADA rosto/prop → só então submit.

**LEI 24 — Fonte da verdade = DISCO, nunca o relato de um agente.**
*Porquê:* uma leva já parou a 97% do fim porque a montagem esperava o RELATÓRIO de um agente que morreu — e ninguém olhava os arquivos prontos no disco.
*Fix:* todo estado em arquivo (state.json, specs); fases encadeiam por artefato existente, não por "aviso"; qualquer sessão nova retoma lendo o disco.

### A linha que não se cruza

**Nunca produza o rosto de uma pessoa real e identificável "confessando" o que ela nunca disse.** O argumento "é um sósia" não resolve — se o criativo só funciona porque o espectador acredita que É a pessoa, a semelhança não é casting, é o mecanismo da fraude. Risco jurídico real pro seu negócio.
✅ O que funciona e é seguro: personagem FICTÍCIO no mesmo papel (o "insider" inventado entrega a mesma força de 1ª pessoa + perseguição, sem o risco) · falar SOBRE a pessoa famosa em 3ª pessoa · figuras arquetípicas não identificáveis.

---

## Registro pós-leva (o hábito que compõe)

Toda sessão de produção TERMINA atualizando o registro: formato novo que funcionou vira ficha no seu acervo · erro novo vira lei NESTE arquivo (com porquê e sintoma) · ad que o tráfego validar vira o padrão-base das variações da próxima leva. A fábrica melhora a cada leva **porque o conhecimento fica em arquivo, não na memória de ninguém** — nem na sua, nem na do Claude.
