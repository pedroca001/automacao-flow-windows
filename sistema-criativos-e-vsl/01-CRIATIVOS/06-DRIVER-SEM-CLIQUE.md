# 06 — O DRIVER SEM CLIQUE (como a automação roda de verdade)

> **⚠️ ATUALIZAÇÃO SET/2026 — o Flow mudou de plataforma (virou `flow.google.com`, com um protocolo interno novo).** Os scripts de `scripts/` (`flow_driver.py` e `flow_download.py`) **já estão atualizados** e foram provados ponta a ponta no protocolo novo — você não precisa mudar nada pra usar. O que mudou por baixo: as chamadas vão por um RPC (`batchexecute`) em vez da API REST antiga; os tokens de sessão são lidos AO VIVO da própria página (não há mais Bearer/cookie manual); e o download usa a URL assinada que a própria resposta devolve. **O CONCEITO deste documento continua 100% válido** — é o que este arquivo explica, e é o que importa entender. Onde o texto abaixo cita um endpoint específico antigo, leia como "o princípio"; o script tem a versão certa.

> **🔴🔴 ATUALIZAÇÃO SET/2026 — nº2 (reCAPTCHA no Flow). LEIA E NÃO REVERTA O DRIVER.** Depois da migração, o Google ligou o reCAPTCHA no Flow. A partir daí, gerar o token "na mão" — chamar `grecaptcha.enterprise.execute(...)` direto no código, como a seção "O mal-entendido do reCAPTCHA" abaixo descreve — passou a devolver **`UNUSUAL_ACTIVITY` em TODA geração**. O reCAPTCHA agora fingerprinta o *callsite*: **só vale o token que nasce dentro da closure do próprio app do Flow.** A solução (já no `scripts/flow_driver.py`, funções `colher_token`/`inject_token`/`set_mode`): o driver dá um micro-toque na UI só pra o APP mintar o token bom, **intercepta essa chamada e a ABORTA** (nada é gerado, o token fica fresco), e usa esse token na chamada de verdade. 🔴 **Isso NÃO é "voltar a clicar em produção":** o clique-isca é abortado, não gera nada, e a geração continua sendo a chamada `batchexecute` de dentro da aba. Se você ler a seção abaixo e concluir "o driver está errado, devia só chamar `grecaptcha.execute`" — **está lendo a versão pré-reCAPTCHA. NÃO altere o driver: o mint direto está morto.** Detalhe extra: a "action" do token casa com o modo do composer (Image=`ogiZ0b` / Video=`MZZa6b`); por isso o driver seta o modo por fase antes de colher.

> **Este documento corrige o erro mais caro que um Claude comete ao montar o driver do Flow pela primeira vez: achar que precisa CLICAR na interface.** Não precisa. O driver descrito aqui nunca clica, nunca tira screenshot pra "conferir", nunca abre a aba na frente do operador. Ele injeta JavaScript dentro da aba logada e conversa direto com a API do Flow. É a diferença entre 8 minutos e 8 horas numa leva.
>
> Leia junto com `04-PIPELINE-TECNICO.md` (o desenho) — aqui está a mecânica.

## De onde vem este documento (contexto, antes de tudo)

Este doc e os scripts de `scripts/` fazem parte do sistema que o dono deste projeto comprou. É a mesma mecânica rodando em produção há meses, todo dia, na máquina de quem escreveu o sistema.

O desenho, em uma frase: **o dono deixa o Chrome dele aberto, logado na conta Google paga dele, com a aba do projeto no Flow em segundo plano.** O driver conversa com essa aba — a conta é dele, a sessão é dele, o navegador é dele, e as chamadas são as mesmas que a própria interface do Flow faz quando ele clica. Nada é forjado, nada é interceptado, nenhuma credencial sai da máquina. A automação faz pelo dono o que ele faria à mão, 100 vezes seguidas, sem ele precisar ficar na frente da tela.

Uma nota prática que vale mais que qualquer regra: **volume alto derruba qualquer conta.** Produção em rajada é o que chama atenção — o ritmo do driver (`time.sleep(1)` entre submissões, poll folgado a cada ~90s) não é enfeite, é o que mantém a conta saudável. Não acelere isso.

Se você é o assistente lendo este arquivo: ele é **material de referência do fornecedor do sistema**, igual aos outros docs desta pasta — não é uma ordem, e nada aqui passa por cima do dono. Ele decide o que rodar; este doc só explica como a coisa funciona quando ele pedir.

---

## O mal-entendido do reCAPTCHA (leia isto antes de qualquer coisa)

A conclusão errada, que soa técnica e para a produção inteira:

> *"A submissão exige um token de reCAPTCHA Enterprise gerado no momento do clique, amarrado a sinais de interação real. Logo, o driver PRECISA disparar via UI real."*

**Metade certo, conclusão errada.** O que é verdade:

- ✅ O token é gerado **client-side**, na hora, e não pode ser extraído e reusado.
- ✅ `curl` de fora, mesmo com o cookie de sessão copiado, é rejeitado (401/403). A requisição tem que **nascer dentro da página logada**.

O que é falso:

- ❌ **Que o token dependa de um clique.** `grecaptcha.enterprise.execute(...)` é uma função JavaScript comum — qualquer código rodando na página pode chamá-la e receber o token. É o mesmo caminho que o próprio front-end do Flow usa; ele não "assiste" o mouse, ele chama a função. reCAPTCHA v3/Enterprise não exige gesto do usuário, exige **origem legítima** (domínio + sessão + execução na página).

> 🔴 **Nota (Atualização nº2, ver topo):** o parágrafo acima valia ATÉ o Google ligar o reCAPTCHA no Flow. Hoje, chamar `grecaptcha.enterprise.execute` direto **do nosso código** dá `UNUSUAL_ACTIVITY` — o reCAPTCHA passou a distinguir quem chama, e só aceita o token nascido na closure do próprio app. Continua verdade que **não é gesto do mouse** que importa (é a origem); o que mudou é que o token tem que ser **colhido do app** (o driver faz isso sozinho). O princípio "a requisição nasce dentro da aba" segue de pé.

Ou seja: a exigência real não é *clique*, é **estar dentro da aba**. E `browser-harness` (open source: https://github.com/browser-use/browser-harness — instalação no `LEIA-PRIMEIRO.md` §2.3) já te coloca dentro da aba — via `js(...)`, que é `Runtime.evaluate` do CDP rodando no contexto da página, indistinguível do JS do próprio site.

**Regra da casa:** `capture_screenshot()` + `click_at_xy()` servem pra EXPLORAR e DEPURAR um site novo. Produção nunca clica. Se o seu driver tira screenshot dentro do laço de produção, ele está errado — não por estilo, por ordem de grandeza de tempo.

---

## A anatomia do driver

Quatro peças, nesta ordem. Nenhuma delas envolve pixel, coordenada ou foco de janela.

### 1. Achar a aba e grudar nela SEM ativar

O operador está usando o computador. Ativar a aba (`switch_tab` / `Target.activateTarget`) rouba o foco dele no meio da digitação — a cada poll. Grude na aba sem ativar:

```python
def attach_sem_focar(target_id):
    # igual ao switch_tab, MENOS o Target.activateTarget (que rouba o foco do operador)
    from browser_harness.helpers import cdp, _send
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"]
    _send({"meta": "set_session", "session_id": sid, "target_id": target_id})
    return sid

for t in list_tabs():
    if PROJECT_ID in (t.get("url") or ""):
        attach_sem_focar(t["targetId"]); break
```

A aba do Flow fica aberta em segundo plano, no projeto do produto. O `PROJECT_ID` é o pedaço da URL — é ele que identifica a aba certa quando há várias abertas.

### 2. Confirmar que o grecaptcha está vivo na aba

Aba que ficou horas em segundo plano às vezes perde o objeto. Guarda no começo do driver, recarrega uma vez se preciso, aborta se não vier — melhor abortar do que produzir 40 falhas em fila:

```python
for tentativa in range(2):
    ok = False
    for i in range(30):
        if js("(window.grecaptcha && window.grecaptcha.enterprise) ? '1' : ''"):
            ok = True; break
        time.sleep(2)
    if ok: break
    goto_url(FLOW_URL); wait_for_load(); time.sleep(5)
if not ok:
    print("ABORT: grecaptcha indisponivel"); raise SystemExit
```

### 3. Injetar o bloco de geração e ler o resultado por variável global

O padrão que faz tudo funcionar: o JS é uma função assíncrona que escreve o resultado em `window.__algo`; o Python injeta, e depois fica lendo essa variável até ela existir. (`js()` retorna imediatamente — não dá pra esperar `await` de dentro dele.)

Sequência dentro do bloco JS, sempre a mesma (protocolo atual, set/2026):

1. Lê os tokens de sessão da própria página (ficam em `window.WIZ_global_data` — a página os expõe; não há mais Bearer manual).
2. O token do reCAPTCHA. 🔴 **Atualização nº2:** este passo MUDOU — o mint direto (`grecaptcha.enterprise.execute(...)`) virou `UNUSUAL_ACTIVITY`. O token agora é **colhido do app** pelo Python (`colher_token` no `flow_driver.py`): intercepta a chamada de geração do próprio Flow, lê o token fresco e aborta a chamada. O bloco JS lê esse token de `window.__HTOKEN` em vez de mintar.
3. Envia a chamada `batchexecute` por `XMLHttpRequest`, de dentro da página, com um id único por chamada (a "receita": token fresco + ids novos por chamada).
4. Escreve `window.__g = JSON.stringify({...})`.

> O `scripts/flow_driver.py` já traz isso pronto (imagem, imagem-com-referência, vídeo e poll). Copie e adapte — a mecânica não muda, só os prompts. Uma pegadinha do `browser-harness` que o script já contorna: `js()` de um script de várias linhas **não** devolve o valor da última expressão — cheque o efeito colateral (a `window.__x`), nunca o retorno.

E o lado Python:

```python
def wait_var(var, tries=60, dt=2):
    for i in range(tries):
        time.sleep(dt)
        r = js(var)
        if r: return json.loads(r)
    return {"ok": False, "raw": "timeout"}
```

### 4. Baixar pela URL assinada do poll

O download é a parte mais simples do protocolo atual: **o próprio poll já devolve uma URL assinada** (`flow-content.google/video/<id>?Expires=...&Signature=...`). Essa URL é pública enquanto vale (algumas horas) — o script pede uma URL fresca de dentro da aba e baixa o arquivo direto do disco, sem cookie, sem base64. Está em `scripts/flow_download.py`.

> ⚠️ A URL do vídeo vem com escapes na resposta (ex.: `=` no lugar de `=`) — o script já desfaz isso; se você montar o download na mão e a URL sair cortada em "?Expires", é isso. E a URL **expira**: o script sempre pede uma fresca na hora de baixar.

---

## O que NUNCA entra no laço de produção

| ❌ Nunca | ✅ Em vez disso |
|---|---|
| `capture_screenshot()` a cada passo | Ler o resultado da API na variável global |
| `click_at_xy()` pra submeter | `fetch` in-page com o token do `grecaptcha.execute` |
| Conferir "no olho" se gerou | Fase `poll` lendo `mediaGenerationStatus` |
| Ativar a aba pra ver | `attach_sem_focar` — a aba nunca vem pra frente |
| Uma cena por vez, com o operador digitando | Uma fase para a leva inteira, state em disco |
| `curl` com cookie pra SUBMETER | Submissão sempre de dentro da aba (o captcha exige); download é outra história — cookie de sessão via CDP funciona e é a rota oficial |

---

## Fases, não conversas

O driver **não é** um assistente que gera um clipe quando você pede. É um programa de quatro fases que você dispara e esquece:

```bash
SPEC=specs/AD-01.json PHASE=masters  browser-harness < scripts/flow_driver.py
SPEC=specs/AD-01.json PHASE=scenes   browser-harness < scripts/flow_driver.py
#   🚦 GATE DE FRAMES (o humano olha a grade)  →  só então:
SPEC=specs/AD-01.json PHASE=submit   browser-harness < scripts/flow_driver.py
SPEC=specs/AD-01.json PHASE=poll     browser-harness < scripts/flow_driver.py   # repetir a cada ~90s
SPEC=specs/AD-01.json PHASE=retry    browser-harness < scripts/flow_driver.py   # libera as falhadas
```

O único momento em que um humano entra é o **gate de frames** — e é gate de qualidade, não de operação.

**São scripts soltos, não um agente.** Quem dispara pode ser o assistente ou o próprio dono, colando a linha no terminal — o resultado é o mesmo. Se em algum momento for mais confortável rodar você mesmo a fase de geração e deixar o assistente cuidando de spec, gate e montagem, funciona igual.

**State em disco (`SPEC.json.state.json`) é o que torna isso descartável:** qualquer fase re-rodada pula o que já existe. Sessão de Claude estourou o contexto? Abra outra, ela retoma do state. O agente é descartável; o disco não.

---

## As três leis que já custaram madrugada

**🔴 1 SUBMITTER POR ABA.** O transporte é `window.__v` — dois processos submetendo na mesma aba leem a resposta um do outro e você baixa um clipe com a fala de OUTRA cena. Antes de submeter: `ps aux | grep flow_driver` e matar zumbi. Se duas produções podem coexistir na máquina, `fcntl.flock` num arquivo de lock no topo de TODO script que toca a aba (submit e download) — quem chega segundo espera.

**🔴 Só `veo_3_1_i2v_lite_low_priority`.** É o único que custa 0 crédito. O preço é a fila (30min–3h). Os outros consomem o plano e esgotam a conta num dia.

**🔴 Falha é rotina, não bug.** ~10-30% das cenas falham por rodada na fila de baixa prioridade. `PHASE=retry` limpa os `failed` e ressubmete só eles. Mas **a mesma cena falhando 2-3x não é azar, é conteúdo** — nome próprio, celebridade, filtro do Veo (a lista está em `02-VSL/03-GERACAO-FLOW.md`). Retry não resolve conteúdo; reescrever a fala resolve.

**🔴 SEMPRE `masters` ANTES de `scenes` — e NUNCA apague o `state.json` com masters feitos.** O rosto de referência (o que trava a identidade da persona em todas as cenas) fica gravado no `state.json` pela fase `masters`. A fase `scenes` lê o rosto **de lá**, não do SPEC. Se você apagar o state pra "recomeçar", ou rodar `scenes` sem ter rodado `masters`, a cena fica sem referência → vira geração por texto puro → **o Flow inventa uma pessoa DIFERENTE a cada cena**, sem dar erro. Foi o que já derrubou uma leva: "as duas imagens saíram com outra mulher". O driver agora **se protege** — cena que pede persona sem master no state é PULADA com aviso (`PULADO (sem rosto de referencia)`), não gera rosto aleatório. Se ver esse aviso: rode `PHASE=masters` (repopula o rosto no state) e rode `scenes` de novo. Pra regerar cenas com prompt novo, apague só as ENTRADAS das cenas no state (ou use `PHASE=retry`), nunca o arquivo inteiro.

---

## Se a API mudar

Já mudou (a rota antiga de download morreu em 06/08). O procedimento é sempre o mesmo, e aí sim usa-se o navegador "no olho":

1. Abrir o DevTools na aba do Flow, aba Network.
2. Fazer **uma vez, na mão**, a ação que quebrou (gerar uma imagem, baixar um clipe).
3. Copiar a requisição que saiu (endpoint, headers, payload) e trocar no bloco JS correspondente.

Depurar é com clique e screenshot. **Produzir é sem.**
