# 👋 Comece por aqui

Você acabou de receber um **sistema completo de produção de criativos, VSL e conteúdo orgânico com avatar de IA** — o mesmo método usado pra escalar ofertas de tráfego direto, empacotado pra rodar no **Claude Code** (o Claude que trabalha dentro do seu computador, no terminal).

A ideia é simples: você conversa com o Claude em português, manda um link ou uma referência, e ele produz. Este documento te coloca de pé em ~30 minutos.

---

## 0. Antes de tudo: confira que o pacote chegou inteiro (30 segundos)

Abra o terminal dentro da pasta `sistema-criativos-e-vsl/` (ou peça pro Claude fazer) e rode:

```
bash scripts/verificar-pacote.sh
```

Se sair 🟢, siga em frente. Se acusar falta da `.claude/skills/`, é o caso clássico: **essa pasta começa com ponto e fica oculta** no Finder/Explorer — quem arrasta ou copia os arquivos pra outra pasta deixa ela pra trás sem ver. Conserto em um comando:

```
bash scripts/instalar-skills.sh
```

Ele recria a `.claude/skills/` a partir da cópia visível `SKILLS/`. Se você prefere abrir o Claude numa pasta maior (o sistema dentro de um projeto seu), instale as skills lá também: `bash scripts/instalar-skills.sh /caminho/da/pasta/onde/abre/o/claude`.

> 🔴 Regra simples: **mova a pasta inteira, nunca "os arquivos de dentro"**. E, na dúvida, rode o verificador — ele diz exatamente o que faltou e como resolver.

---

## 1. O que tem dentro desta pasta

- **`SISTEMA.md`** — o cérebro. O Claude lê isso pra saber operar. Você não precisa ler tudo.
- **`.claude/skills/`** — sete comandos prontos (⚠️ pasta **oculta** — começa com ponto; no Finder aperte **Cmd+Shift+.** pra ver; a cópia visível está em `SKILLS/`): `/criativos`, `/vsl` e `/avatares-organicos` (as **três máquinas**) + `/direct-response-copywriter`, `/copy-legends` e `/marketing-psychology` (as skills de copy — o Claude ativa sozinho toda vez que for escrever roteiro, CTA, headline ou oferta; ver seção 5) + `/video-ia-sem-defeito` (o catálogo de defeitos do gerador de vídeo — o Claude ativa sozinho antes de escrever ou revisar qualquer prompt de vídeo).
- **`SKILLS/`** — a mesma coisa que `.claude/skills/`, só que visível. Existe pra você nunca perder as skills se mover a pasta (ver seção 0).
- **`01-CRIATIVOS/`** — a máquina de anúncios (link de biblioteca → criativos prontos).
- **`scripts/`** — os **8 scripts do pipeline, prontos**: `gerar_specs.py` (copy → specs), `flow_driver.py` + `flow_download.py` (o Flow sem clique), `gate_frames.py` + `gate_clipes.py` (os gates), `montar_leva.py` + `banner.py` (a montagem final com legenda, headline e CTA) e `voz-unica.py` (voz única, orgânico). Paths por variável de ambiente — seu Claude ajusta e roda. Mapa e fluxo em **`scripts/LEIA.md`**; a mecânica do driver em `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md`.
- **`02-VSL/`** — a máquina de VSL (uma VSL de referência → uma VSL nova editada).
- **`03-BRINDE-UPSELLS/`** — 🎁 estruturas de esteira de upsell pra multiplicar seu ticket.
- **`04-BRINDE-BIBLIOTECA-FORMATOS/`** — 🎁 a biblioteca de formatos, hooks campeões e nichos.
- **`05-AVATARES-ORGANICOS/`** — 🎁 a **terceira máquina**, o jogo SEM tráfego pago: uma persona de IA postando reels todo dia, funil de comentário → DM → oferta. Mesma fábrica de vídeo, leis diferentes (várias regras do pago se INVERTEM lá — comece por `00-VISAO-GERAL.md`; comando `/avatares-organicos`, ver seção 4.5).
- **`swipefile/`** — um banco de ~800 ofertas escaladas pra você estudar, **online e sempre atualizado**: **https://001class.site/swipefile/** (veja `swipefile/ACESSE-AQUI.md`).

---

## 2. Setup (uma vez só)

Você precisa de algumas ferramentas instaladas (os 5 grupos abaixo). O próprio Claude te ajuda a instalar cada uma — se travar em qualquer passo, é só pedir: *"me ajuda a instalar o ffmpeg"*, por exemplo.

### 2.1 Claude Code
Se você está lendo isto dentro do Claude Code, já tem. Se não: instale o Claude Code e **abra ele nesta pasta** (`sistema-criativos-e-vsl/`). Assim ele carrega o `SISTEMA.md` e as skills (`.claude/skills/`) automaticamente. Se `/criativos` e `/vsl` não aparecerem como comando, volte na seção 0 — as skills não estão onde o Claude olha.

### 2.2 Google Flow (a fábrica de vídeo)
- Tenha uma conta Google com acesso ao **Flow** (Veo 3 + Nano Banana 2). É aqui que os vídeos e imagens são gerados.
- Deixe o **Chrome logado** nessa conta. O sistema pilota o Flow por uma aba oculta — você não precisa fazer nada manual.

### 2.3 browser-harness (como o Claude pilota o Flow)
Ferramenta **open source** que dá ao Claude o controle do seu Chrome pelo protocolo de depuração (CDP): repositório público **https://github.com/browser-use/browser-harness**. Instalação (o Claude faz por você — peça *"instala e configura o browser-harness"*):

```bash
git clone https://github.com/browser-use/browser-harness ~/Developer/browser-harness
cd ~/Developer/browser-harness && uv tool install -e .      # (precisa do `uv`: https://docs.astral.sh/uv/ — ou `pip install uv`)
command -v browser-harness                                   # tem que responder com o caminho
```
Depois: adicione a linha `@~/Developer/browser-harness/SKILL.md` no seu `~/.claude/CLAUDE.md` (é assim que o Claude aprende a usar a ferramenta em qualquer pasta), e **abra o Chrome com a depuração remota liberada** — a primeira vez que o harness conectar, o Chrome pede autorização em `chrome://inspect/#remote-debugging` (clique em *Permitir*). O arquivo install.md **do repositório do browser-harness** (não deste pacote) cobre conexão e problemas comuns. Ele conecta no seu Chrome **já logado** no Flow — não abre navegador próprio.

> 🔴 **Como você sabe que está rodando certo:** depois que a produção começa, **nada aparece na sua tela**. Nenhuma janela pula, nenhum clique, nenhuma pergunta a cada clipe. Você dispara uma fase e ela roda a leva inteira sozinha. Se o seu Claude estiver clicando na tela do Flow, tirando print e te perguntando clipe por clipe, ele montou o driver errado — mande ele ler `01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md` e usar os scripts de `scripts/`.

### 2.4 Apify (a espionagem)
- Crie uma conta em **apify.com** (tem plano grátis pra começar).
- Pegue seu **API token** em Settings → API & Integrations.
- Guarde em `~/.config/apify/token` (é o caminho que os comandos prontos do `01-CRIATIVOS/01-ESPIONAGEM-APIFY.md` leem: `mkdir -p ~/.config/apify && echo "SEU_TOKEN" > ~/.config/apify/token`). O sistema usa o actor `curious_coder/facebook-ads-library-scraper` (~$0,75 por 1000 anúncios).

### 2.5 Ferramentas locais de vídeo (grátis)
- **ffmpeg** com libass (corta, monta, legenda).
- **whisper.cpp** (`whisper-cli`) + os modelos `ggml-base.bin` e `ggml-small.bin` (transcrição local).
- **Python 3** com **Pillow** (`pip install pillow`).
- **edge-tts** (`pip install edge-tts`) — TTS grátis e sem chave, usado pelo `scripts/voz-unica.py` pra unificar a voz em vídeo sem rosto (máquina de orgânico). Sem ele só esse script quebra; o resto roda normal.
- **RobustVideoMatting (RVM)** — pra remoção de fundo nas VSLs. Peça pro Claude: *"instala o RVM pra remoção de fundo"* (ele clona o repositório e baixa os pesos).

> Não precisa decorar nada disso. Peça: *"confere o que já está instalado e me diz o que falta"* — o Claude roda o diagnóstico e instala o que faltar.

---

## 3. Seu primeiro criativo (5 minutos de conversa)

1. Abra o Claude Code nesta pasta.
2. Ache uma oferta que está escalando: abra o swipe file online em **https://001class.site/swipefile/**, ou pegue um link direto da Facebook Ads Library.
3. Digite:

   ```
   /criativos
   ```
   e cole o link da biblioteca de anúncios. Ou escreva:
   > *"Espiona essa biblioteca, me mostra os formatos que estão rodando e monta um plano de 5 criativos pra minha oferta de [nicho]."*

4. O Claude vai: raspar a biblioteca → transcrever → analisar os frames → te mostrar o que achou → propor os criativos. **Ele te apresenta o plano antes de gerar.** Você aprova, ele produz, e te entrega os criativos em lotes pra você aprovar.

5. **O que você tem que ver no plano (e cobrar se não vier):** uma **tabela com uma linha por criativo** — quem é a pessoa e onde ela está (diferente em cada ad), **qual é o gancho** (o que acontece de estranho/grande/absurdo nos 2 primeiros segundos — nunca "ela fala pra câmera"), e a sequência de planos do corpo (close, aberto, demonstração, insert sem rosto, outro canto do cenário). Se os 15 vierem com a mesma pessoa falando de frente, **manda voltar** e cita `01-CRIATIVOS/07-GANCHOS-DE-CHOQUE.md` e `08-CRIATIVO-DINAMICO.md`. Depois de montado, peça o resultado do `scripts/medir_ritmo.py finais/` — é o número que diz se ficou dinâmico.

---

## 4. Sua primeira VSL

1. Tenha uma **VSL de referência** (um link ou um arquivo de vídeo de uma VSL que vende no seu nicho).
2. Digite:

   ```
   /vsl
   ```
   e aponte a referência. Ou escreva:
   > *"Modela essa VSL pra minha oferta de [nicho]. Quero antes/depois, prova e depoimento."*

3. O Claude faz a engenharia reversa, te mostra o mapa da VSL, escreve o roteiro modelado (você aprova), gera os clipes e monta com a edição completa. **Você aprova em cada etapa.**

4. **Antes de ele montar, você tem que receber o PLANO DE EDIÇÃO** (uma tabela: cena por cena, o que entra além da expert falando — tela dividida no começo, B-roll, insert de estudo, antes/depois, expert recortada sobre a prova). Se ele pular direto pra "montei", manda voltar e cita `02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md`. A régua é simples: **nada de plano parado por mais de 6-8 segundos**, zoom (punch-in) em toda fala longa, os 2 primeiros minutos cheios. E ele te mostra o resultado do `scripts/medir_ritmo.py` — se der 🔴, ele remonta, não entrega.

---

## 4.5. Sua primeira página orgânica

A terceira máquina não compra mídia: ela monta uma **página com uma persona de IA que posta
reels todo dia**, e o funil fecha em **comentário → DM → bridge → oferta**.

1. Digite:

   ```
   /avatares-organicos
   ```
   Ou escreva:
   > *"Quero montar uma página orgânica de [nicho], com avatar. Me ajuda desde a persona."*

2. O Claude vai: propor a persona → gerar a identidade visual da página (perfil e capa,
   renderizadas localmente, custo zero) → gerar o **master** do avatar (a foto que trava o
   rosto pra todos os vídeos) → montar os primeiros reels → e te apresentar tudo pra aprovar.

3. **Antes de publicar o primeiro post** ele vai te cobrar três coisas que travam o funil:
   a **bridge no ar**, a **automação comentário→DM** com a keyword da página, e o **filtro
   de palavrão desligado** (ligado, ele esconde o comentário e o funil morre calado).

> 🔴 **Se você já roda anúncio, cuidado:** as leis de criativo pago não valem todas aqui.
> A mais cara: **o produto NÃO pode aparecer nos primeiros segundos** de um reel orgânico.
> Medimos dois reels com roteiro idêntico palavra por palavra — **375 views contra
> 20.000** — e a única diferença era o produto no frame 0. Em anúncio pago é o contrário.
> O porquê está em `05-AVATARES-ORGANICOS/00-VISAO-GERAL.md`.

**Dependência extra desta máquina:** `pip install edge-tts` (TTS grátis, sem chave, usado
pra unificar a voz em vídeo sem rosto — o `scripts/voz-unica.py`).

## 5. Como falar com o sistema

Você não precisa saber comandos técnicos. Fale o que quer, em português. Exemplos que funcionam:

- *"Atualiza meu swipe file com as ofertas novas de emagrecimento."*
- *"Pega os 3 hooks mais fortes do nicho de finanças e faz 3 variações de corpo diferente."*
- *"Monta a esteira de upsell da minha oferta — 3 upsells e 2 downsells."* (usa o `03-BRINDE-UPSELLS/`)
- *"Refaz o criativo 4 com o mecanismo diferente, mantém o resto."*
- *"Confere esse criativo no gate de qualidade antes de eu subir."*

## 6. As skills de copy (o texto que vende)

Todo roteiro, CTA, headline e oferta que o sistema escreve — dentro do `/criativos` e do `/vsl` — passa por três skills de copywriting que vieram no pacote:

- **`direct-response-copywriter`** — a espinha dorsal: o que dizer, em que ordem e por quê — consciência do público (Schwartz), oferta (Hormozi), mecanismo único (RMBC), estrutura de criativo e de VSL de tráfego direto, gatilhos (Cialdini) costurados na história.
- **`copy-legends`** — as lendas do copywriting (Halbert, Schwartz, Kennedy, Sugarman, Bencivenga, Georgi e outros) condensadas em fórmulas prontas de headline, VSL, oferta, bullets e funil.
- **`marketing-psychology`** — os gatilhos e modelos mentais por trás de por que as pessoas compram (ancoragem, prova social, escassez, etc.).

**Você não precisa chamar nada disso na mão** — o Claude ativa sozinho sempre que for escrever algo que vende. Mas se quiser um texto avulso (um e-mail, uma headline, uma oferta nova), é só pedir direto:

- *"Escreve 5 headlines pro meu produto de [nicho] usando a copy-legends."*
- *"Monta a oferta com bônus e garantia pro meu upsell."*
- *"Que gatilho de persuasão eu uso pra vencer a objeção de preço aqui?"*

## 6.5. A skill de vídeo sem defeito

Tem mais uma skill que o Claude ativa sozinho: **`video-ia-sem-defeito`**. Ela não decide
gancho nem copy — cuida só de o **vídeo nascer mecanicamente correto**, e vale nas três
máquinas.

É um catálogo de defeitos medidos em produção, com a regra que evita cada um: objeto que
vira outro objeto no meio do movimento, matéria que se multiplica sozinha, texto aparecendo
pintado na parede, líquido que ignora a gravidade, cena encolhida numa faixa borrada.

Vale saber que ela existe por um motivo prático: **quando um clipe falhar 3 vezes seguidas,
não é azar de fila — é conteúdo.** Peça: *"roda a triagem de falha nessa cena"*.

## 7. Duas regras que valem ouro

1. **Você é o QA final.** O sistema produz e te apresenta — nada "vai pro ar" sem seu OK. Confie, mas confira.
2. **Sempre comece pelo que já vende.** O sistema nunca cria do nada — ele parte do que está escalando no mercado. É por isso que funciona.
3. **Vídeo parado é vídeo reprovado.** Criativo ou VSL em que a pessoa fica falando de frente, sem gancho de impacto, sem troca de plano, sem B-roll, sem zoom, é o que 100% dos amadores fazem — e o dedo do usuário já aprendeu a passar reto. O sistema tem a régua (docs 07/08 dos criativos e 06 da VSL) e um medidor (`scripts/medir_ritmo.py`). Se o seu Claude entregar parado, o erro é de processo: ele pulou o plano. Manda voltar.

## 8. Duas ressalvas honestas sobre os números do módulo orgânico

O `05-AVATARES-ORGANICOS/` traz números medidos, não deduzidos. Mas eles têm limite, e é
melhor você saber qual:

**1. Os números vêm de uma operação, num nicho.** São reais — página de saúde masculina em
inglês, público americano. O **método** de medir transfere pra qualquer nicho; os **números**
você refaz no seu antes de tratar como lei.

**2. Um achado vale onde foi medido.** "Produto fora da abertura" nasceu num formato **com
rosto**, onde o produto na mão interrompe o que interessa. Não há dado dizendo que
transfere pra formato **sem rosto**, onde manipular o produto *é* a ação. O módulo 07
mostra como testar isso de propósito, em vez de assumir.

Bom trabalho. Qualquer dúvida, pergunte ao próprio Claude — ele conhece o sistema inteiro.
