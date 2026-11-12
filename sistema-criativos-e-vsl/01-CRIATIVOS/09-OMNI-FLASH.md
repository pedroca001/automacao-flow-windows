# 09 · OMNI FLASH — o modelo novo do Flow (opcional, consome créditos)

> ⚠️ **NOTA DA MIGRAÇÃO (set/2026):** os endpoints `aisandbox-pa.googleapis.com` deste doc são do
> **protocolo antigo** (labs.google/flow). Se a sua conta já migrou pro `flow.google.com`, eles podem
> não responder mais. O modelo em si **continua existindo e funcionando** (dá pra usar normalmente pela
> interface do Flow); pra chamá-lo **sem clique** no protocolo novo, o caminho é o MESMO `batchexecute`
> do driver (doc 06) trocando a string do modelo — capture uma geração manual sua no DevTools (aba
> Network, chamada `batchexecute` do submit) e copie a string do modelo pro driver, mesma receita que
> mapeou o protocolo novo. O padrão de produção segue o **veo lite low priority (custo zero)**, que já
> está 100% no protocolo novo nos scripts do pacote.
>
> 🔴 **Atualização set/2026 nº2 (reCAPTCHA):** as linhas abaixo que mostram `grecaptcha.enterprise.execute`
> como fonte do token são do jeito ANTIGO. Depois que o Google ligou o reCAPTCHA, mintar o token direto dá
> `UNUSUAL_ACTIVITY`; o driver agora **colhe** o token do próprio app (ver doc 06). Pra trocar o modelo
> (Omni Flash, Fast, Quality etc.), a mecânica é a mesma do driver — só muda a string do modelo capturada
> no DevTools; a fonte do token é a colheita, não o mint.

> O Omni Flash é o modelo mais novo do Google Flow (aparece no topo da lista, acima do
> Veo 3.1 Lite/Fast/Quality). Gera clipes de 8 segundos, 720p, vertical, com qualidade acima.
> Este doc ensina o Claude a chamá-lo pelo mesmo driver sem-clique do sistema.
>
> ⚠️ **REGRA DE OURO DO CUSTO:** o Omni Flash **CONSOME CRÉDITOS do plano pago** do Flow
> (o payload leva `userPaygateTier: 'PAYGATE_TIER_TWO'`). O `veo_3_1_r2v_lite_low_priority`
> que o motor usa é custo **ZERO** e **continua sendo o padrão de tudo**. Omni Flash é
> opt-in: só quando o dono pedir explicitamente ("gera no Omni Flash"). Nunca dispare uma
> leva inteira nele sem um clipe de ensaio aprovado pelo dono antes.

> ## 🎛️ COMO ESCOLHER O MODELO (o driver roda QUALQUER um) — atualizado set/2026
> O `scripts/flow_driver.py` já aceita a escolha do modelo por variável de ambiente na hora de rodar a
> fase `submit` — não precisa editar código:
>
> ```bash
> FLOW_QUALIDADE=gratis SPEC=specs/AD-01.json PHASE=submit browser-harness < scripts/flow_driver.py  # 0 créditos (padrão)
> FLOW_QUALIDADE=lite   ...   # veo_3_1_r2v_lite   — pago, existe em QUALQUER conta com Flow
> FLOW_QUALIDADE=omni   ...   # abra_r2v_8s        — Omni 1.1 Flash (qualidade acima, consome mais)
> FLOW_QUALIDADE=fast   ...   # veo_3_1_r2v_fast_portrait_ultra — Veo 3.1 Fast 9:16
> # controle total (qualquer modelo, inclusive um "Quality" capturado no DevTools):
> FLOW_VIDEO_MODEL="<string exata do modelo>" ... PHASE=submit ...
> ```
>
> - **Default = `gratis`** (`veo_3_1_r2v_lite_low_priority`, 0 créditos). Esse modelo só existe em conta
>   com **Google AI Ultra** (fila de baixa prioridade).
> - 🔴 **FALLBACK AUTOMÁTICO:** se a conta **não** tiver o modelo escolhido (ex.: `gratis` sem Ultra), o
>   Flow devolve `PUBLIC_ERROR_MODEL_*` e o driver **cai sozinho pro `veo_3_1_r2v_lite`** (pago) e segue —
>   a produção **não para** por causa do plano da conta. Quem tem Ultra gera de graça; quem não tem gera
>   pagando o lite, sem editar nada.
> - Pra achar a string interna de um modelo novo do Flow: abra o DevTools (aba Network), gere 1 clipe
>   manualmente com o modelo desejado, ache a chamada `batchexecute` (rpc `MZZa6b`) e copie a string do
>   modelo pro `FLOW_VIDEO_MODEL`. A fonte do token continua sendo a **colheita** (doc 06), não o mint.

## Os dois modos

### Modo A — r2v, COM imagem de referência (o que interessa: trava rosto/cenário do avatar)
- `videoModelKey`: **`abra_r2v_8s`**
- endpoint: `POST https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoReferenceImages`
- payload:

```json
{
  "mediaGenerationContext": { "batchId": "<uuid novo>", "audioFailurePreference": "BLOCK_SILENCED_VIDEOS" },
  "clientContext": {
    "projectId": "<id do projeto Flow>", "tool": "PINHOLE",
    "userPaygateTier": "PAYGATE_TIER_TWO",
    "sessionId": ";<Date.now()>",
    "recaptchaContext": { "token": "<token grecaptcha>", "applicationType": "RECAPTCHA_APPLICATION_TYPE_WEB" }
  },
  "requests": [{
    "outputSpec": { "resolution": "VIDEO_RESOLUTION_720P" },
    "aspectRatio": "VIDEO_ASPECT_RATIO_PORTRAIT",
    "textInput": { "structuredPrompt": { "parts": [{ "text": "<prompt da cena>" }] } },
    "videoModelKey": "abra_r2v_8s",
    "seed": 123456789,
    "metadata": {},
    "referenceImages": [{ "mediaId": "<mediaId da imagem-mestre>", "imageUsageType": "IMAGE_USAGE_TYPE_ASSET" }]
  }],
  "useV2ModelConfig": true
}
```

### Modo B — t2v, SEM imagem de referência (rosto pode variar entre clipes)
- `videoModelKey`: **`abra_t2v_8s`**
- endpoint: `POST https://aisandbox-pa.googleapis.com/v1/video:batchAsyncGenerateVideoText`
- payload: mesma casca do modo A, mas **sem `requests[]`** — os campos vão na raiz:
  `structuredPrompt` direto, `referenceImages: []`, `referenceAudioIds: []`,
  `shouldReturnSilentVideos: false`, sem `outputSpec`.
- Use só quando a consistência de rosto não importa (b-roll, objeto, cenário vazio).

## Como integrar no `scripts/flow_driver.py`

O bloco de submissão de vídeo que já existe (o que chama `video:batchAsyncGenerateVideoStartImage`
com `veo_3_1_i2v_lite_low_priority` e `startImage`) serve de molde. Para o r2v, as diferenças
são SÓ estas cinco:

1. Endpoint → `.../v1/video:batchAsyncGenerateVideoReferenceImages`
2. `videoModelKey` → `abra_r2v_8s`
3. `startImage: {mediaId}` → `referenceImages: [{mediaId, imageUsageType: 'IMAGE_USAGE_TYPE_ASSET'}]`
4. Entra `outputSpec: {resolution: 'VIDEO_RESOLUTION_720P'}` dentro do request
5. `clientContext` ganha `userPaygateTier: 'PAYGATE_TIER_TWO'`

Todo o resto é idêntico ao driver atual: a requisição **nasce dentro da aba logada** do Flow
(fetch na página), com `Authorization: Bearer <access_token de /fx/api/auth/session>`,
`Content-Type: text/plain;charset=UTF-8`, e o token do reCAPTCHA gerado por função —
`await window.grecaptcha.enterprise.execute(SITE_KEY, {action:'VIDEO_GENERATION'})`
(o mesmo SITE_KEY que o driver já usa).

A resposta devolve a operação em `d.media[0].name` **ou** `d.operations[0].operation.name`
(manter o fallback duplo) e `d.remainingCredits` — **logue esse número a cada submissão**,
é o alarme de custo.

Implemente como **parâmetro** (ex.: campo `modelo: "omni_flash"` no spec da cena / argumento
da função de submeter), com o veo lite continuando o padrão. Não reescreva o driver — adicione.

## A imagem-mestre (referência)

O `mediaId` é o mesmo que o driver já obtém ao gerar a imagem no projeto
(rota `flowMedia:batchGenerateImages`, resposta em `d.media[0].image.generatedImage.mediaId`).
Nada muda na fase de imagem: gera a mestre como sempre, guarda o `mediaId` e passa ele no
`referenceImages`. É o análogo direto do `startImage` do i2v atual.

## Poll e download — NÃO mudam

- Status: a mesma rota de sempre — `POST .../v1/video:batchCheckAsyncVideoGenerationStatus`
  com `{"media":[{"name":"<op>","projectId":"<proj>"}]}`.
  ⚠️ O status verdadeiro está em `media[0].mediaMetadata.mediaStatus.mediaGenerationStatus`
  (o campo de topo mente). `SUCCESS/COMPLETE/SUCCEEDED` = pronto · `FAILED/CANCELLED` = morto.
- Download: igual ao `scripts/flow_download.py`. Bônus: o poll do Omni Flash costuma devolver
  `media[0].video.fifeUrl` — URL direta que já baixa o MP4; se vier, pode usar.
  Valide o arquivo (>200KB; menor é HTML de erro — apague e re-tente).

## As leis que continuam valendo (não são sugestão)

1. Toda requisição nasce dentro da aba logada. Nunca copie cookie pra fora, nunca faça login
   por script, nunca automatize senha/captcha.
2. Ritmo humano: `sleep` de 1s entre submissões, poll folgado (20s+). Rajada derruba conta.
3. 1 submissor por aba por vez.
4. `FAILED` no poll = re-submete a MESMA cena (falha de moderação é estocástica, retry resolve).
   A mesma cena falhando 3× não é azar, é conteúdo: reescreva o prompt.
5. Estado em disco (op/mediaId/status no state.json), como o motor já faz — tudo retomável.
6. Custo: ensaio de 1 clipe → dono aprova → só então a leva.

## Teste de aceitação (nesta ordem)

1. Chrome logado no Flow, projeto aberto: gere 1 imagem-mestre normal e guarde o `mediaId`.
2. Submeta 1 clipe r2v com essa mestre e um prompt curto de fala pra câmera.
3. Poll até `SUCCESS`, baixe o clipe.
4. `ffprobe`: duração ~8s, 720p vertical, áudio presente.
5. Mostre ao dono: `mediaId` da mestre, o op name, `remainingCredits` antes/depois e o caminho do MP4.

Se o submit falhar com erro de payload, **não invente campos**: mostre o corpo da resposta de
erro ao dono e pare.

---

## 🔴 Correção que acompanha esta atualização: VOZ FIXA POR PERSONAGEM (vale pra tudo, não só Omni)

Bug real, reportado em produção: **a voz do personagem muda no meio do ad ou da VSL.**
A causa: cada clipe é gerado de forma independente — se a descrição de voz for genérica
("natural, clear voice") ou faltar, o gerador sorteia uma voz nova a cada cena.

A lei que conserta:

1. **Todo personagem que fala tem um campo `voz` OBRIGATÓRIO e DETALHADO**, com âncoras:
   **sexo + idade + timbre + ritmo**. Ex.: `"woman around 50, warm low-pitched voice, calm natural pace, native prosody"`.
2. **A MESMA string, byte-idêntica, entra no bloco `[VOICE]` de TODAS as cenas daquele
   personagem**, do primeiro ao último clipe do ad ou da VSL. Nunca reescreva, nunca "melhore"
   no meio — qualquer variação na descrição é convite pro gerador trocar a voz.
3. Vale em TODOS os modos e modelos: veo lite, Omni Flash r2v e t2v, cena falada e insert com
   voz off ("Off-camera narration...", mesma voz) — a voz é do PERSONAGEM, não da cena.
4. Na VSL: o `[VOICE]` fixo da expert se repete verbatim em todas as cenas dela (só a tag de
   emoção da cena varia; a descrição-base nunca).
5. O `scripts/gerar_specs.py` agora COBRA isso sozinho: **reprova** persona que fala sem `voz`
   e **avisa** quando a voz não tem âncora de sexo+idade.
