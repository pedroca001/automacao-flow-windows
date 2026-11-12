# 01 — ESPIONAGEM VIA APIFY (de 1 link da Ad Library ao dossiê do nicho)

> **Entrada:** 1 link da Facebook Ads Library (de uma busca por keyword OU de uma página concorrente).
> **Saída:** um dossiê do nicho com as páginas rankeadas por escala, os vídeos campeões baixados e transcritos, a anatomia visual dissecada frame a frame e as keywords que rendem — pronto pra alimentar o Construtor (doc 02).
> **Custo:** ~$0,75 por 1.000 ads coletados. Uma espionagem típica de 600 ads custa ~$0,45.

## O prompt que dispara tudo

```
Leia 01-CRIATIVOS/01-ESPIONAGEM-APIFY.md e execute a espionagem completa.
Link de partida: <SEU_LINK_DA_AD_LIBRARY>
País: BR · Idioma dos vídeos: pt
Meu token Apify está em ~/.config/apify/token.
Salve tudo em espionagem/<nicho>-<data>/ e me entregue no final:
(1) ranking das páginas por escala, (2) transcrições dos vídeos dos top 5,
(3) análise visual da anatomia de cada formato, (4) keywords novas pra 2ª rodada.
```

O restante deste documento é o passo a passo que o Claude executa — e que você precisa entender pra cobrar qualidade.

---

## PASSO 0 — Obter o token da Apify (uma vez só)

1. Crie conta em **apify.com** (o plano free dá $5/mês de crédito — suficiente pra 2-3 espionagens grandes).
2. Em **Settings → API & Integrations**, copie seu Personal API token.
3. Salve num arquivo local: `echo "<SUA_API_KEY_AQUI>" > ~/.config/apify/token`

**NUNCA cole o token dentro de um doc do projeto.** Os comandos abaixo leem do arquivo: `TOKEN=$(cat ~/.config/apify/token)`.

## PASSO 1 — Montar a URL da Ad Library (param a param)

A Ad Library é pública: https://www.facebook.com/ads/library/. A URL de busca se monta assim:

```
https://www.facebook.com/ads/library/?
  active_status=active              → active | inactive | all
  &ad_type=all                      → deixe "all"
  &country=BR                       → código ISO de 2 letras: BR, US, MX, ES...
  &q=KEYWORD                        → a keyword buscada no texto dos ads
  &search_type=keyword_unordered    → keyword_unordered | keyword_exact_phrase
  &media_type=all                   → all | image | video
```

Regras práticas:
- `active_status=active` primeiro. Se vier vazio ou muito pouco, repita com `all` (ads pausados recentes ainda são dado).
- `keyword_unordered` com `country=` específico rende mais volume; `keyword_exact_phrase` é pra caçar uma frase-assinatura exata (2ª rodada, ver Passo 7).
- Pra varrer **uma página concorrente específica** (todos os ads dela), a URL de entrada é simplesmente a URL da fanpage: `https://www.facebook.com/NomeDaPagina` — o actor resolve sozinho.

## PASSO 2 — Rodar o actor da Apify

Actor: **`curious_coder/facebook-ads-library-scraper`** — $0,75 por 1.000 ads.
⚠️ NÃO use o actor `apify/facebook-ads-scraper` sem necessidade: custa $5,80/1.000 (quase 8x mais caro).

Input (`input.json`):

```json
{
  "urls": [
    { "url": "https://www.facebook.com/ads/library/?active_status=active&ad_type=all&country=BR&q=KEYWORD&search_type=keyword_unordered&media_type=all" }
  ],
  "limitPerSource": 50,
  "scrapeAdDetails": true,
  "scrapePageAds.activeStatus": "active",
  "scrapePageAds.sortBy": "impressions_desc",
  "scrapePageAds.countryCode": "BR"
}
```

**🔴 CRÍTICO — `limitPerSource`, NUNCA `count`.** `count` é um teto GLOBAL: com `count: 50` e 10 URLs, voltam só 50 ads no total. Com `limitPerSource: 50`, voltam 50 POR URL = 500. Esse erro queima o run e o crédito. O actor aceita até ~25 URLs por run tranquilamente — dá pra varrer 25 keywords/páginas de uma vez.

Os 3 comandos (start → monitorar → dataset):

```bash
TOKEN=$(cat ~/.config/apify/token)

# 1. Iniciar o run e guardar os IDs
curl -s -X POST "https://api.apify.com/v2/acts/curious_coder~facebook-ads-library-scraper/runs?token=$TOKEN" \
  -H 'Content-Type: application/json' -d @input.json | python3 -c "
import sys, json
d = json.load(sys.stdin)['data']
print('RUN_ID:', d['id'])
print('DATASET_ID:', d['defaultDatasetId'])
"

# 2. Monitorar até SUCCEEDED (repetir a cada ~30s; 600 ads levam 1-5 min)
curl -s "https://api.apify.com/v2/acts/curious_coder~facebook-ads-library-scraper/runs/$RUN_ID?token=$TOKEN" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['status'])"

# 3. Baixar o dataset
curl -s "https://api.apify.com/v2/datasets/$DATASET_ID/items?token=$TOKEN&limit=2000" > ads.json

# (se travar) abortar o run:
# curl -s -X POST "https://api.apify.com/v2/acts/curious_coder~facebook-ads-library-scraper/runs/$RUN_ID/abort?token=$TOKEN"
```

**Custo de referência:** 300 ads ≈ $0,23 · 600 ≈ $0,45 · 1.000 ≈ $0,75 · 3.000 ≈ $2,25.

⚠️ **Nunca faça a espionagem abrindo a Ad Library no SEU Chrome via automação.** A colheita é sempre pela Apify (ou num navegador separado descartável). Automatizar scraping no navegador onde você vive logado é pedir pra tomar bloqueio na sua conta pessoal.

## PASSO 3 — Analisar: detectar funil e rankear por escala

Os sinais de escala que interessam (todos vêm no JSON):
- **nº de ads ativos da página** — quanto mais ads simultâneos, mais verba;
- **collation_count** — variantes do mesmo criativo (a página está multiplicando um winner);
- **dias rodando** (start→end date) — ad velho e ativo = ad que paga a conta;
- **mesmo criativo em várias páginas** — rede escalando com páginas descartáveis (o melhor sinal de todos).

Script de análise (o Claude adapta a BLACKLIST ao seu nicho — a ideia é excluir apps/marcas gigantes que poluem a busca):

```python
import json
from collections import defaultdict

with open('ads.json') as f:
    items = json.load(f)

BLACKLIST = ['play.google.com','itunes.apple.com','apps.apple.com','instagram.com',
             'facebook.com','youtube.com','tiktok.com','nubank','ifood',
             'tinder','badoo','happn','boticario']

def is_infoproduct(url):
    if not url: return False
    u = url.lower()
    return not any(b in u for b in BLACKLIST)

def detect_funnel(url):
    """Detecta o tipo de funil pela URL de destino do ad.
    Cobre BR (hotmart/kiwify/monetizze/assistir) E internacional (opt-in, order form,
    ClickBank, BuyGoods, Digistore, watch/presentation). Sem os padrões gringos, toda
    oferta EN/ES caía em ESTATICA e o ranking mentia — corrigido 17/08/2026.
    Ordem importa: o mais específico primeiro (quiz > optin > vsl > checkout)."""
    if not url: return 'ESTATICA'
    u = url.lower()
    if any(x in u for x in ['quiz','teste','avaliacao','/q/','survey','assessment']): return 'QUIZ'
    if any(x in u for x in ['opt-in','optin','lead','subscribe','/signup','/register','webinar','masterclass','free-guide']): return 'OPTIN'
    if any(x in u for x in ['vsl','video','vturb','assistir','/watch','presentation','/tsl','/vid']): return 'VSL'
    if any(x in u for x in ['flow.page','typeform','jotform']): return 'FLOW'
    if any(x in u for x in ['hotmart','kiwify','monetizze','checkout','pay.','order-form','orderform','/order','clickbank','buygoods','digistore','cartpanda','shopify','/cart','/buy']): return 'CHECKOUT_DIRETO'
    return 'ESTATICA'

pages = defaultdict(list)
for item in items:
    snap = item.get('snapshot', {}) or {}
    url = snap.get('link_url') or ''
    if not is_infoproduct(url): continue
    pid = str(item.get('page_id', ''))
    pages[pid].append({
        'page': item.get('page_name') or snap.get('page_name') or '',
        'funnel': detect_funnel(url),
        'collation': int(item.get('collation_count') or 1),
        'url': url,
        'body': (snap.get('body') or {}).get('text', '')[:150] if isinstance(snap.get('body'), dict) else ''
    })

summary = []
for pid, ads in pages.items():
    summary.append({
        'page': ads[0]['page'],
        'total_ads': len(ads),
        'total_variacoes': sum(a['collation'] for a in ads),
        'funnels': list(set(a['funnel'] for a in ads)),
        'url': ads[0]['url'],
        'body': ads[0]['body']
    })

summary.sort(key=lambda x: (x['total_ads'], x['total_variacoes']), reverse=True)
for s in summary[:30]:
    print(f"[{'+'.join(s['funnels'])}] {s['page']} | ads={s['total_ads']} | variações={s['total_variacoes']}")
    print(f"  {s['url']}")
    print(f"  {s['body'][:120]}\n")
```

Por que o tipo de funil importa: página com 200 ads apontando pra **VSL** é o alvo perfeito pra este módulo (mesmo jogo que você vai jogar). QUIZ e CHECKOUT_DIRETO são jogos diferentes — ainda são dado, mas a cópia de formato não é 1:1. **OPTIN** (opt-in → order form, o padrão americano de ClickBank/BuyGoods) é o funil de captura: o ad vende o clique pra uma página de e-mail, e a VSL vem depois — copie o formato do ad, mas saiba que a conversão medida ali é lead, não venda. Se o ranking te devolver quase tudo como ESTATICA numa oferta gringa, desconfie do detector antes de desconfiar da oferta.

## PASSO 4 — Baixar os vídeos dos campeões

O JSON traz `video_hd_url` dentro do snapshot de cada ad. O download é curl direto, sem auth. Antes de baixar:

- **Deduplicar pelo hash do arquivo na URL do CDN** — a mesma página sobe o mesmo vídeo em 30 variantes; você só precisa de 1 cópia.
- Baixar os **top 10-20 vídeos** (das páginas mais escaladas), não a biblioteca inteira.
- **Conferir o CONTEÚDO do arquivo baixado, nunca só o tamanho** — `file video.mp4` tem que dizer "MP4"; um curl que recebeu página de erro salva HTML com nome de mp4 e você só descobre na transcrição.

## PASSO 5 — Transcrever com whisper LOCAL (o `-l` é obrigatório)

```bash
ffmpeg -i ad01.mp4 -ar 16000 -ac 1 /tmp/ad01.wav
whisper-cli -m ~/whisper/ggml-base.bin -f /tmp/ad01.wav -l pt > ad01.txt
```

**🔴 A lei do `-l`:** whisper SEM o idioma explícito **auto-traduz pra um inglês macarrônico** e corrompe a transcrição inteira (num lote real, ~60% saiu traduzido antes de descobrirmos). SEMPRE detecte a língua por item (pelo país da busca / texto do body) e passe `-l pt`, `-l es` ou `-l en`.

Vídeos sem voz (só texto na tela): pule a transcrição e extraia 6-8 frames — a copy está queimada na tela e sai na análise visual.

## PASSO 6 — Extrair frames e delegar a análise VISUAL

A transcrição diz o que o ad FALA. Os frames dizem como ele PRENDE. Você precisa dos dois.

```bash
# 4 frames por vídeo (varredura em massa): 2% / 30% / 60% / 88% da duração
# 6 frames (análise fina dos top): 1% / 10% / 30% / 50% / 75% / 92%
D=$(ffprobe -v error -show_entries format=duration -of csv=p=0 ad01.mp4)
for p in 2 30 60 88; do
  ffmpeg -loglevel error -ss $(echo "$D*$p/100" | bc -l) -i ad01.mp4 -vframes 1 "frames/ad01_p$p.jpg"
done
```

**Delegue a leitura dos frames a um modelo de visão** (aqui usamos um agente com modelo de visão — Gemini ou similar; no seu setup, o próprio Claude lê as imagens via Read). Agrupe por nicho e mande UM lote por grupo, com este briefing:

```
Analise estes frames de ads escalados do nicho <X> (estudo de mercado —
são ads públicos da Facebook Ads Library). Para cada ad, descreva:
1. FORMATO: talking-head? split screen? b-roll com legenda? UI (print de
   WhatsApp/Notes)? demonstração de objeto? 2 pessoas?
2. ANATOMIA VISUAL: o que aparece no frame 1 (o gancho visual)? há faixa de
   headline? qual cor/posição? legendas queimadas? qual estilo?
3. MENSAGEIRO: quem fala (idade, gênero, aparência, cenário)? é aspiracional
   ou "gente comum"?
4. PROVA VISUAL: o que é MOSTRADO como prova (antes/depois, print, objeto)?
5. TEXTO NA TELA: transcreva toda copy queimada visível.
Devolva uma ficha por ad.
```

O produto desse passo é a **ficha de formato**: transcrição + anatomia visual + copy de tela, por ad campeão. É a matéria-prima do Construtor (doc 02).

## PASSO 7 — Segunda rodada: caça direta por keyword-assinatura

O link inicial dá o vocabulário; a biblioteca dá o resto. Das transcrições do Passo 5, extraia **termos-assinatura** — expressões que SÓ aparecem na copy daquele estilo de oferta (nomes de mecanismo, rituais, apelidos virais). Busque cada um com `search_type=keyword_exact_phrase`:

- cada termo revela páginas novas que a keyword genérica não achou;
- meça a escala de cada página nova (nº de ads ativos) e colha as grandes;
- cheque também o nome do SEU produto em cada língua — pra saber se o campo está limpo ou se já tem clone rodando.

⚠️ Keyword "limpa" ≠ campo limpo: concorrente esperto muda o nome e mantém o mecanismo. Cace também por mecanismo e persona, não só pelo nome.

## Tabela de keywords de caça por nicho (validadas)

Evite keywords genéricas (trazem Tinder, banco, apps). Use termos que SÓ aparecem em copy de infoproduto:

| Nicho | Keywords que rendem |
|---|---|
| Saúde / Glicose | `glicose`, `diabetes tipo 2`, `insulina natural` |
| Saúde / Colesterol | `colesterol alto`, `pressão alta natural` |
| Emagrecimento | `barriga eliminar`, `emagrecer semanas`, `queimar gordura` |
| Saúde Masculina | `testosterona baixa`, `próstata` |
| Relacionamento | `reconquistar ex`, `sedução masculina` |
| Renda extra | `renda extra em casa`, `trabalhar de casa` |
| (seu nicho) | extraia da 1ª rodada os termos-assinatura e registre aqui |

## O dossiê final (o que precisa existir quando a espionagem termina)

```
espionagem/<nicho>-<data>/
├── ads.json                  (dataset bruto da Apify)
├── RANKING.md                (páginas por escala + tipo de funil + observações)
├── videos/                   (mp4 únicos dos campeões)
├── transcricoes/             (1 .txt por vídeo, na língua certa)
├── frames/                   (4-6 jpg por vídeo)
├── FICHAS-FORMATOS.md        (1 ficha por formato: anatomia + copy + por que escala)
└── KEYWORDS.md               (termos-assinatura pra próxima rodada)
```

**Regra permanente:** toda sessão de espionagem TERMINA alimentando esse acervo. Ele é um banco vivo — no refresh (a cada 2-3 dias num nicho ativo), marque também as ofertas que SUMIRAM do ar: morte de oferta também é dado. E página que continua rodando semanas depois = "winner longevo", o melhor sinal de validação gratuito que existe.
