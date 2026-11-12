# TEMPLATE DAS PÁGINAS — UPSELL E DOWNSELL

> Esqueletos HTML prontos e comentados das duas páginas da esteira. São HTML estático puro — hospede onde quiser. A única parte que depende da sua plataforma de checkout é o snippet de one-click no fim de cada página (seção 5). Substitua apenas os valores entre `[COLCHETES]`; a estrutura CSS já está calibrada.

---

## 1. As duas páginas, lado a lado

| | Página de UPSELL | Página de DOWNSELL |
|---|---|---|
| Vídeo | SIM — VSL 7-10 min (VTurb/Smartplayer) | NÃO |
| Conteúdo | Oculto em `#botao`, revelado pelo player no pitch | Tudo visível de cara |
| Headline | Só aparece com o reveal | Preço riscado É a headline |
| Copy | Longa (componentes + stack + garantia) | Curta (3-5 parágrafos) |
| Faixa de alerta | Cor forte, varia por etapa | "ESPERA — tem certeza?" |
| CTA | 2x (topo do reveal + final) | 1x, primeira dobra |

**Cor da faixa de alerta por etapa** (sinaliza progresso sem dizer nada): UP1 vermelho `#c0392b` → UP2 laranja `#d35400` → UP3 âmbar `#b7950b` → downsells sempre vermelho. Pessoa sente que está avançando num processo, não presa num loop de ofertas.

---

## 2. A mecânica do `#botao` oculto (o coração da página de upsell)

```
1. Todo o conteúdo abaixo do vídeo vive em <div id="botao" style="display:none">
2. A VSL sobe no VTurb (ou player equivalente com "smart display")
3. No painel do player: Elementos inteligentes → revelar elemento com ID "botao"
   → timestamp = o momento EXATO em que a VSL fala o preço (Beat 10)
4. Antes do pitch: a pessoa só vê o vídeo. Nada pra clicar, nada pra julgar.
5. No pitch: a página inteira "nasce" — botão, stack, garantia — junto com o preço falado.
```

Dica de produção: teste o reveal manualmente antes de subir tráfego — abra o console do navegador e rode `document.getElementById('botao').style.display='block'` pra conferir o layout revelado.

---

## 3. TEMPLATE — PÁGINA DE UPSELL (com VSL)

```html
<!DOCTYPE html>
<html lang="pt-BR"> <!-- troque o lang pro idioma do seu funil -->
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ESPERA — [NOME DO PRODUTO]</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{background:#f5f0e8;font-family:'Inter',sans-serif;color:#2a2a2a;font-size:18px;line-height:1.7}
    /* FAIXA DE ALERTA — troque a cor por etapa: UP1 #c0392b / UP2 #d35400 / UP3 #b7950b */
    .alert-bar{background:#c0392b;color:#fff;text-align:center;padding:14px 20px;font-size:15px;font-weight:700}
    .container{max-width:760px;margin:0 auto;padding:0 20px}
    .video-section{padding:40px 0 32px}
    .video-label{text-align:center;font-size:13px;font-weight:600;letter-spacing:.12em;text-transform:uppercase;color:#7a6a55;margin-bottom:16px}
    .video-wrapper{position:relative;width:100%;border-radius:4px;overflow:hidden;box-shadow:0 8px 32px rgba(44,74,62,.18)}
    h1,h2,h3{font-family:'Playfair Display',serif;color:#2c4a3e;line-height:1.25}
    .headline{font-size:clamp(28px,5vw,44px);font-weight:900;text-align:center;margin-bottom:12px}
    .subheadline{font-size:clamp(17px,2.5vw,21px);text-align:center;color:#4a3f30;font-style:italic;margin-bottom:36px}
    .divider{width:60px;height:3px;background:#27AF60;margin:32px auto;border-radius:2px}
    p{margin-bottom:20px;font-size:clamp(16px,2vw,19px)}
    .story-block{background:#ede8df;border-left:4px solid #2c4a3e;border-radius:0 6px 6px 0;padding:24px 28px;margin:32px 0}
    .story-block p{font-style:italic;color:#3a3028;margin-bottom:14px}
    .components-list{list-style:none;padding:0;margin:0 0 36px}
    .components-list li{display:flex;gap:16px;align-items:flex-start;padding:20px 0;border-bottom:1px solid #ddd5c4}
    .comp-icon{flex-shrink:0;width:44px;height:44px;background:#2c4a3e;color:#f5f0e8;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px}
    .comp-title{font-family:'Playfair Display',serif;font-size:clamp(17px,2.2vw,21px);font-weight:700;color:#2c4a3e;margin-bottom:6px}
    .comp-desc{font-size:clamp(15px,1.8vw,17px);color:#4a4040;margin-bottom:6px;line-height:1.6}
    .comp-value{font-size:14px;font-weight:700;color:#7a6a55;text-transform:uppercase}
    .value-stack{background:#2c4a3e;border-radius:8px;padding:32px 28px;margin:36px 0;color:#f5f0e8}
    .value-stack h3{color:#a8d5b5;font-size:clamp(18px,2.5vw,24px);margin-bottom:20px;text-align:center}
    .value-row{display:flex;justify-content:space-between;padding:10px 0;border-bottom:1px solid rgba(255,255,255,.12);font-size:clamp(14px,1.8vw,17px)}
    .value-row .item-name{color:#d0c9be}
    .value-row .item-price{font-weight:700;color:#a8d5b5}
    .value-total-row{display:flex;justify-content:space-between;padding:18px 0 0;margin-top:8px;border-top:2px solid rgba(255,255,255,.25)}
    .total-label{font-family:'Playfair Display',serif;font-size:clamp(17px,2.2vw,21px);font-weight:700;color:#fff}
    .total-original{font-size:15px;color:#a8d5b5;text-decoration:line-through;margin-right:10px}
    .total-price{font-family:'Playfair Display',serif;font-size:clamp(26px,4vw,38px);font-weight:900;color:#fff}
    .guarantee-block{display:flex;gap:20px;align-items:flex-start;background:#eaf4ee;border:2px solid #27AF60;border-radius:8px;padding:24px;margin:36px 0}
    .guarantee-icon{font-size:48px;flex-shrink:0}
    .guarantee-body h3{font-size:clamp(18px,2.2vw,22px);color:#1a6b41;margin-bottom:8px}
    .urgency-bar{background:#fff3cd;border:1px solid #e6c84a;border-radius:6px;padding:16px 20px;text-align:center;margin:24px 0;font-size:clamp(15px,1.8vw,17px);color:#7a5c10;font-weight:600}
    .closing-cta{padding:16px 0 60px;text-align:center}
    .closing-headline{font-size:clamp(22px,3.5vw,34px);font-weight:900;color:#2c4a3e;margin-bottom:12px}
    .closing-sub{font-size:clamp(15px,1.8vw,18px);color:#4a4040;margin-bottom:28px}
    .btn-accept{background:#2ECC70;padding:16px 28px;cursor:pointer;color:#fff;font-weight:700;border-radius:6px;border:none;font-size:20px}
    .link-decline{margin-top:1rem;cursor:pointer;font-size:16px;text-decoration:underline;color:#b8a898}
    @media(max-width:540px){.guarantee-block{flex-direction:column}.story-block{padding:18px}}
  </style>
</head>
<body>

  <!-- 1. FAIXA DE ALERTA — urgência + curiosidade, NÃO revela o produto -->
  <div class="alert-bar">🔴 [ex: "ESPERA — Seu pedido ainda não está completo. Assista à mensagem de [EXPERT] antes de fechar."]</div>

  <div class="container">

    <!-- 2. VSL — a única coisa visível até o pitch -->
    <div class="video-section">
      <p class="video-label">[ex: "Uma mensagem pessoal de [EXPERT]"]</p>
      <div class="video-wrapper">
        <vturb-smartplayer id="vid-[VTURB_PLAYER_ID]" style="display:block;width:100%;"></vturb-smartplayer>
        <script>var s=document.createElement("script");s.src="https://scripts.converteai.net/[VTURB_TOKEN]/players/[VTURB_PLAYER_ID]/v4/player.js";s.async=true;document.head.appendChild(s);</script>
      </div>
    </div>

    <!-- ══════ TUDO ABAIXO FICA OCULTO — o player revela #botao no pitch ══════ -->
    <div id="botao" style="display:none;">

      <!-- 3. CTA TOPO — nasce junto com o preço falado -->
      <div style="text-align:center;padding:32px 0 16px" id="[CONTAINER-CHECKOUT — ver seção 5]"
           data-upsell-url="[URL_SE_ACEITAR]"
           data-downsell-url="[URL_SE_RECUSAR]">
        <button class="btn-accept" id="[TRIGGER-ACEITAR — ver seção 5]">
          ✅ SIM — Adicionar [NOME DO UPSELL] ao Meu Pedido
        </button>
        <div class="link-decline" id="[TRIGGER-RECUSAR — ver seção 5]">
          [Formulação NEGATIVA — ex: "Não, obrigado. Prefiro continuar sem [benefício central]."]
        </div>
      </div>

      <!-- 4. HEADLINE + COPY -->
      <div style="padding:8px 0 40px">
        <div class="divider"></div>
        <h1 class="headline">[HEADLINE — "[Resultado] em [tempo] com [mecanismo]"]</h1>
        <p class="subheadline">[SUBHEADLINE]</p>

        <p>[PARÁGRAFO 1 — o problema novo que este upsell resolve]</p>
        <p>[PARÁGRAFO 2 — a consequência de não resolver]</p>

        <div class="story-block">
          <p>"[CITAÇÃO DO EXPERT ou história curta de cliente]"</p>
          <p>— [Nome], [idade/credencial]</p>
        </div>

        <p><strong>[FRASE DE TRANSIÇÃO — apresenta o produto]</strong></p>

        <div class="divider"></div>
        <h2 style="font-family:'Playfair Display',serif;font-size:clamp(22px,3.5vw,32px);font-weight:700;text-align:center;margin-bottom:20px">
          Apresentando: [NOME DO UPSELL]
        </h2>

        <!-- 5. COMPONENTES — 3-5 itens, cada um com valor individual -->
        <ul class="components-list">
          <li>
            <div class="comp-icon">1</div>
            <div>
              <div class="comp-title">[NOME DO ITEM 1]</div>
              <div class="comp-desc">[O que faz, como ajuda, resultado esperado]</div>
              <div class="comp-value">Valor: US$ [X]</div>
            </div>
          </li>
          <li>
            <div class="comp-icon">2</div>
            <div>
              <div class="comp-title">[NOME DO ITEM 2]</div>
              <div class="comp-desc">[Descrição]</div>
              <div class="comp-value">Valor: US$ [X]</div>
            </div>
          </li>
          <li>
            <div class="comp-icon">3</div>
            <div>
              <div class="comp-title">[NOME DO ITEM 3]</div>
              <div class="comp-desc">[Descrição]</div>
              <div class="comp-value">Valor: US$ [X]</div>
            </div>
          </li>
        </ul>

        <!-- 6. VALUE STACK — total riscado → preço de hoje -->
        <div class="value-stack">
          <h3>O Que Você Recebe Hoje</h3>
          <div class="value-row"><span class="item-name">[Item 1]</span><span class="item-price">US$ [X]</span></div>
          <div class="value-row"><span class="item-name">[Item 2]</span><span class="item-price">US$ [X]</span></div>
          <div class="value-row"><span class="item-name">[Item 3]</span><span class="item-price">US$ [X]</span></div>
          <div class="value-total-row">
            <span class="total-label">Seu Preço Hoje</span>
            <span style="text-align:right">
              <span class="total-original">US$ [TOTAL SOMADO]</span>
              <span class="total-price">US$ [PREÇO REAL]</span>
            </span>
          </div>
        </div>

        <div class="urgency-bar">[SCARCITY DE PÁGINA — ex: "Esta oferta aparece uma única vez. Quando você sair desta página, ela desaparece."]</div>

        <p>[COPY FINAL — a dor de ficar sem]</p>
        <p><strong>[FRASE DE FECHAMENTO marcante]</strong></p>

        <!-- 7. GARANTIA -->
        <div class="guarantee-block">
          <div class="guarantee-icon">🛡️</div>
          <div class="guarantee-body">
            <h3>Garantia de [X] Dias</h3>
            <p>[Mesma garantia do front ou maior — reembolso completo, sem perguntas]</p>
          </div>
        </div>
      </div>

      <!-- 8. CTA FINAL — clona o clique dos triggers do topo -->
      <div class="closing-cta">
        <h2 class="closing-headline">[HEADLINE FINAL]</h2>
        <p class="closing-sub">[SUBHEADLINE — urgência]</p>
        <div style="text-align:center">
          <button class="btn-accept" onclick="document.getElementById('[TRIGGER-ACEITAR]').click()">
            ✅ SIM — Quero por Apenas US$ [PREÇO]
          </button>
          <div class="link-decline" onclick="document.getElementById('[TRIGGER-RECUSAR]').click()">
            [DECLINE FINAL — mesma formulação negativa]
          </div>
        </div>
      </div>

    </div><!-- /#botao -->
  </div><!-- /container -->

  <!-- SNIPPET DA SUA PLATAFORMA DE CHECKOUT — ver seção 5 -->
</body>
</html>
```

---

## 4. TEMPLATE — PÁGINA DE DOWNSELL (sem vídeo, preço riscado)

```html
<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>ESPERA — Oferta Especial | [NOME DO PRODUTO]</title>
  <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700;900&family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    *,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
    body{background:#f5f0e8;font-family:'Inter',sans-serif;color:#2a2a2a;min-height:100vh}
    .alert-bar{background:#c0392b;color:#fff;text-align:center;padding:14px 20px;font-size:15px;font-weight:700;line-height:1.4}
    .wrapper{max-width:640px;margin:0 auto;padding:36px 24px 48px}
    .main-headline{font-family:'Playfair Display',serif;font-size:clamp(26px,5vw,40px);font-weight:900;color:#2c4a3e;text-align:center;line-height:1.2;margin-bottom:28px}
    .price-block{background:#fff;border:2px solid #2c4a3e;border-radius:10px;padding:20px 24px;text-align:center;margin-bottom:28px}
    .price-label{font-size:13px;font-weight:700;color:#666;text-transform:uppercase;letter-spacing:.1em;margin-bottom:10px}
    .price-row{display:flex;align-items:center;justify-content:center;gap:12px}
    .price-note{font-size:13px;color:#666;margin-top:8px}
    .copy-block{margin-bottom:24px}
    .copy-block p{font-size:16px;line-height:1.75;margin-bottom:14px}
    .bullets{background:#fff;border-left:4px solid #2ECC70;border-radius:0 8px 8px 0;padding:18px 20px;margin-bottom:28px}
    .bullets-title{font-family:'Playfair Display',serif;font-size:16px;font-weight:700;color:#2c4a3e;margin-bottom:12px}
    .bullets ul{list-style:none;padding:0}
    .bullets ul li{font-size:15px;line-height:1.55;padding:5px 0 5px 24px;position:relative}
    .bullets ul li::before{content:"✓";position:absolute;left:0;color:#2ECC70;font-weight:700}
    .btn-yes{display:block;width:100%;background:#2ECC70;color:#fff;font-size:18px;font-weight:700;padding:18px 24px;border:none;border-radius:6px;cursor:pointer;text-align:center;margin-bottom:16px}
    .btn-no{display:block;text-align:center;color:#999;font-size:14px;text-decoration:underline;cursor:pointer}
    .guarantee{text-align:center;font-size:13px;color:#666;line-height:1.5;padding-top:16px;border-top:1px solid #ddd6c8;margin-top:20px}
    @media(max-width:480px){.wrapper{padding:28px 18px 40px}}
  </style>
</head>
<body>

  <div class="alert-bar">🔴 ESPERA — Tem certeza que quer sair sem isso?</div>

  <div class="wrapper">

    <!-- O corte de preço É a headline -->
    <h1 class="main-headline">[ex: "Tudo bem. E se fosse US$ [PREÇO CORTADO]?"]</h1>

    <div class="price-block">
      <div class="price-label">Oferta única — apenas nesta página</div>
      <div class="price-row">
        <span style="text-decoration:line-through;color:#999;font-size:1.3rem;">US$ [PREÇO ORIGINAL]</span>
        <span style="font-size:2rem;font-weight:800;color:#2c4a3e;">US$ [PREÇO CORTADO]</span>
      </div>
      <div class="price-note">[ex: "50% off — nunca mais neste preço."]</div>
    </div>

    <!-- Copy curta: 3-5 parágrafos. Mesma oferta, só desconto. -->
    <div class="copy-block">
      <p>[ex: "Entendi. O preço era o problema. Então cortei pela metade."]</p>
      <p>[ex: "Mesmo conteúdo completo. Metade do preço. Porque não vou deixar US$ [X] ser o motivo de você ficar sem [RESULTADO]."]</p>
      <p>[ex: "Esta oferta desaparece quando você sair desta página. Não volta."]</p>
    </div>

    <div class="bullets">
      <div class="bullets-title">O que você recebe em [NOME DO UPSELL]:</div>
      <ul>
        <li>[Benefício 1]</li>
        <li>[Benefício 2]</li>
        <li>[Benefício 3]</li>
        <li>[Benefício 4]</li>
      </ul>
    </div>

    <div id="[CONTAINER-CHECKOUT — ver seção 5]"
         data-upsell-url="[URL_SE_ACEITAR]"
         data-downsell-url="[URL_SE_RECUSAR]">
      <button id="[TRIGGER-ACEITAR]" class="btn-yes">
        SIM — Quero por apenas US$ [PREÇO CORTADO]
      </button>
      <div id="[TRIGGER-RECUSAR]" class="btn-no">
        Não. Não quero esta oferta em nenhum preço.
      </div>
    </div>

    <div class="guarantee">
      <strong>Garantia de [X] dias.</strong> Se não funcionar, reembolso total. Sem perguntas.
    </div>

  </div>

  <!-- SNIPPET DA SUA PLATAFORMA DE CHECKOUT — ver seção 5 -->
</body>
</html>
```

---

## 5. Ligando na SUA plataforma de checkout (one-click)

O HTML acima é agnóstico. A plataforma entra em 3 pontos:

**Passo 1 — O script.** Toda plataforma com upsell one-click (Kiwify, Hotmart, Eduzz, Monetizze, CartPanda etc.) fornece um script de upsell. Cole-o antes do `</body>` de TODAS as páginas de upsell e downsell. Exemplo do padrão (cada plataforma tem o seu — consulte a doc dela):
```html
<script src="[URL do script de upsell da sua plataforma]"></script>
```

**Passo 2 — Os IDs.** A plataforma gera um identificador da oferta de upsell. Ele entra em 3 lugares do HTML: o `id` do container do checkout, o `id` do botão aceitar (trigger) e o `id` do link recusar (cancel trigger). O padrão de nomenclatura exato varia por plataforma — peça pro seu Claude ler a doc da sua e preencher os `[COLCHETES]`.

**Passo 3 — As URLs de navegação.**
- `data-upsell-url` (ou equivalente) = a página que abre SE ACEITAR
- `data-downsell-url` (ou equivalente) = a página que abre SE RECUSAR

O aceite é one-click: o cartão já foi capturado no front, a plataforma cobra sem redigitar nada.

## 6. O fluxo de navegação accept/decline

```
FRONT comprou
  │
  ▼
UP1 ── aceita ──► UP2
  └── recusa ──► DS1 ── aceita ──► UP2
                   └── recusa ──► UP2       (nunca prenda a pessoa: recusou 2x, avança)
UP2 ── aceita ──► UP3
  └── recusa ──► DS2 ── aceita ──► UP3
                   └── recusa ──► UP3
UP3 ── aceita ──► OBRIGADO
  └── recusa ──► DS3 ── aceita ──► OBRIGADO
                   └── recusa ──► OBRIGADO
```

Variante agressiva (cascata dupla, ver Esteira B em `3-ESTRUTURAS-MODELO.md`): cada recusa de downsell abre um SEGUNDO downsell ainda mais barato antes de avançar. Só pra públicos que toleram pressão.

Regras do fluxo:
- **Recusar nunca é beco sem saída** — sempre leva pro próximo passo, nunca pra página em branco.
- **A última recusa da esteira leva pra página de obrigado/acesso.** A pessoa comprou o front; ela SEMPRE termina bem recebida.
- **As páginas de upsell não devem ser indexáveis nem linkadas de lugar nenhum** — a scarcity "esta página não volta" precisa ser verdade.

## 7. Checklist final antes de subir tráfego

- [ ] Reveal do `#botao` configurado no player de CADA upsell, no timestamp do pitch
- [ ] Teste manual do reveal (console: `display='block'`) — layout ok no mobile
- [ ] Script da plataforma + IDs de oferta em todas as páginas
- [ ] URLs accept/decline conferidas página a página (o erro clássico é DS1 apontando pro lugar errado)
- [ ] Compra-teste de ponta a ponta: front → aceita UP1 → recusa UP2 → aceita DS2 → obrigado
- [ ] Preço riscado do downsell = preço real do upsell correspondente (coerência!)
- [ ] Faixa de alerta com cor da etapa certa
- [ ] Garantia presente e igual/maior que a do front em toda página
