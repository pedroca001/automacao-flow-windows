# VERSAO-ATU08: rev2-fix-vazamento-x  (colheita aborta SÓ a chamada com token; as outras passam)
# DRIVER DO FLOW — referência (sem clique, sem screenshot, sem roubar o foco).
# Roda DENTRO do browser-harness, na ABA LOGADA do Flow que esteja num projeto:
#   SPEC=specs/AD-01.json PHASE=masters browser-harness < scripts/flow_driver.py
# Fases: masters | scenes | submit | poll | retry     (leia 01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md)
#
# ⚠️ ATUALIZAÇÃO SET/2026 — o Flow mudou de plataforma. Antes era um app com API REST; agora é
# um front que fala por RPC (batchexecute) em flow.google.com. Este driver JÁ está no protocolo novo.
# O que mudou por dentro: as chamadas vão por batchexecute; os tokens de sessão são lidos AO VIVO da
# própria página (não há mais cookie/Bearer manual); o poll e o download usam a URL assinada que a
# própria resposta devolve. O que NÃO mudou: a interface de fases, o SPEC, o state.json e a filosofia
# (a requisição nasce dentro da aba logada). 🔴 ATUALIZAÇÃO nº2 (SET/2026): o Google pôs reCAPTCHA e o
# token do app parou de valer quando mintado direto — agora ele é COLHIDO da própria UI (ver o bloco
# "COLHEITA DE TOKEN" e 01-CRIATIVOS/06-DRIVER-SEM-CLIQUE.md).
#
# O QUE ESTE ARQUIVO É: a mecânica pura de falar com o Flow de dentro da aba logada.
# O QUE ELE NÃO É: o cérebro criativo. Os prompts vêm PRONTOS no spec.
#
# SPEC esperado:
# {
#   "personas": { "<key>": {"prompt_img": "<prompt do frame-âncora>",
#                           "master_mediaId": "<opcional: reusar frame já existente>"} },
#   "itens": [ { "id": "AD-01",
#                "cenas": [ {"n": 1, "persona_key": "<key ou ''>",
#                            "prompt_img":   "<prompt do frame desta cena>",
#                            "prompt_video": "<prompt i2v desta cena, com a fala embutida>"} ] } ]
# }
# ESTADO: <SPEC>.state.json — idempotente. Re-rodar qualquer fase PULA o que já está feito.

import json, time, os, re
try:
    import fcntl
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from flow_platform import locks as fcntl
import urllib.parse as _urllib

SPEC_PATH  = os.environ["SPEC"]
PHASE      = os.environ.get("PHASE", "poll")
STATE_PATH = SPEC_PATH + ".state.json"
LOCK_PATH  = os.environ.get("FLOW_LOCK", os.path.expanduser("~/.flow_lane.lock"))
# opcional: se você mantém VÁRIAS abas de projeto abertas, aponte a certa por id.
WANT_PROJ  = os.environ.get("FLOW_PROJECT", "")

# ── LANE LOCK ────────────────────────────────────────────────────────────────
# A sessão CDP do harness é GLOBAL. Dois scripts tocando a aba ao mesmo tempo trocam
# a aba um do outro e cruzam respostas. Quem chega segundo espera. Liberado no exit.
_LOCK = open(LOCK_PATH, "a")
print("aguardando lane do Flow...", flush=True)
fcntl.flock(_LOCK, fcntl.LOCK_EX)
print("lane adquirida", flush=True)

spec  = json.load(open(SPEC_PATH))
state = json.load(open(STATE_PATH)) if os.path.exists(STATE_PATH) else {"personas": {}, "cenas": {}}
def save(): json.dump(state, open(STATE_PATH, "w"), indent=1)

# ── MODELO DE VÍDEO (escolha do cliente, com fallback automático) ─────────────
# O sistema roda QUALQUER modelo do Flow, não só o de custo zero. Duas formas de escolher:
#   FLOW_QUALIDADE=gratis|lite|omni|fast   (apelido amigável — o mais fácil)
#   FLOW_VIDEO_MODEL=<string interna>       (controle total: cola a string exata capturada no DevTools,
#                                            ex.: um modelo "Quality" ou qualquer outro; ver 09-OMNI-FLASH.md)
# Se as duas vierem, FLOW_VIDEO_MODEL vence. Default = 'gratis' (0 créditos, EXIGE Google AI Ultra).
# 🔴 FALLBACK: se a conta NÃO tiver o modelo escolhido (ex.: 'gratis'/low_priority sem Ultra), o Flow
# responde PUBLIC_ERROR_MODEL_* e o driver cai SOZINHO pro 'veo_3_1_r2v_lite' (pago, toda conta tem) —
# a produção não para por causa do plano da conta.
_QMAP = {
    "gratis": "veo_3_1_r2v_lite_low_priority",    # 0 créditos — fila de baixa prioridade (só com Ultra)
    "lite":   "veo_3_1_r2v_lite",                 # padrão pago — existe em qualquer conta com Flow
    "omni":   "abra_r2v_8s",                      # Omni 1.1 Flash (qualidade acima, consome mais)
    "fast":   "veo_3_1_r2v_fast_portrait_ultra",  # Veo 3.1 Fast, vertical 9:16
}
VMODEL = (os.environ.get("FLOW_VIDEO_MODEL", "").strip()
          or _QMAP.get(os.environ.get("FLOW_QUALIDADE", "gratis").strip().lower(), _QMAP["gratis"]))
VMODEL_FALLBACK = "veo_3_1_r2v_lite"
print("modelo de video:", VMODEL)

# ── ABA: grudar na aba do Flow (num projeto) SEM ativar (nunca roubar o foco) ──
def attach_sem_focar(target_id):
    from browser_harness.helpers import cdp, _send
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"]
    _send({"meta": "set_session", "session_id": sid, "target_id": target_id})
    return sid

alvo = None
for t in list_tabs():
    u = t.get("url") or ""
    if "flow.google.com/project/" in u and (not WANT_PROJ or WANT_PROJ in u):
        alvo = t; break
if not alvo:
    print("ABORT: abra o Flow e ENTRE num projeto (URL flow.google.com/project/...) antes de rodar")
    raise SystemExit
sid = attach_sem_focar(alvo["targetId"])
print("aba:", alvo.get("url"))

# ── GUARDA: sessão + grecaptcha vivos nesta aba ──────────────────────────────
chk = json.loads(js(r"""
(function(){ const W=window.WIZ_global_data||{};
 let sk=''; for(const s of document.querySelectorAll('script[src*="recaptcha"]')){const m=s.src.match(/[?&]render=([^&]+)/);if(m){sk=m[1];break;}}
 const proj=(location.href.match(/project\/([0-9a-fA-F\-]+)/)||[])[1]||'';
 return JSON.stringify({at:!!W.SNlM0e, fsid:!!W.FdrFJe, bl:!!W.cfb2h, sk:!!sk,
   grc:!!(window.grecaptcha&&window.grecaptcha.enterprise), proj:proj}); })()
""") or "{}")
if not all([chk.get("at"), chk.get("fsid"), chk.get("bl"), chk.get("sk"), chk.get("grc"), chk.get("proj")]):
    print("ABORT: sessao/projeto incompletos nesta aba:", chk); raise SystemExit
print("projeto:", chk["proj"])

# ── NÚCLEO DO PROTOCOLO (injetado uma vez) ───────────────────────────────────
# Cada operação escreve numa global e o Python lê. Sem clique. Token fresco por chamada.
# A "receita" do protocolo novo, em uma linha: monta a chamada batchexecute com um token fresco
# do grecaptcha, identificadores únicos por chamada, e envia por XHR de dentro da própria página.
CORE = r"""
window.__flowcore = (function(){
  const W = window.WIZ_global_data||{};
  const at=()=>W.SNlM0e, fsid=W.FdrFJe, bl=W.cfb2h;
  let SK=''; for(const s of document.querySelectorAll('script[src*="recaptcha"]')){const m=s.src.match(/[?&]render=([^&]+)/);if(m){SK=m[1];break;}}
  const PROJ=(location.href.match(/project\/([0-9a-fA-F\-]+)/)||[])[1]||'';
  const U=()=>crypto.randomUUID().toUpperCase();
  const SEED=()=>Math.floor(Math.random()*2147483647);
  const CTX=(tk)=>[null,22,null,null,null,PROJ,null,null,null,null,[tk,1]];
  const RID=()=>Math.floor(1000000+Math.random()*8000000);
  // 🔴 ATUALIZAÇÃO SET/2026 (2): o Google pôs reCAPTCHA no Flow. Mintar o token direto
  // (grecaptcha.enterprise.execute) passou a devolver UNUSUAL_ACTIVITY em TODA geração. O reCAPTCHA
  // fingerprinta o CALLSITE: só o token nascido na CLOSURE DO APP passa. Por isso o Python COLHE
  // esse token da própria UI (intercepta a chamada do app, extrai o token e ABORTA — nada gera) e o
  // injeta em window.__HTOKEN antes de cada geração. Uso único por chamada. Detalhes: 06-DRIVER-SEM-CLIQUE.md.
  const tok=async(a)=>window.__HTOKEN;
  const clean=(t)=>(t||'').replace(/\\+u([0-9a-fA-F]{4})/g,(m,h)=>String.fromCharCode(parseInt(h,16))).replace(/\\+\//g,'/');
  async function batch(rpc, inner){
    const url='/_/AiSandboxAngularFrontend/data/batchexecute?rpcids='+rpc+'&source-path=%2Fproject%2F'+PROJ
      +'&bl='+encodeURIComponent(bl)+'&f.sid='+encodeURIComponent(fsid)+'&hl=pt&_reqid='+RID()+'&rt=c';
    const body='f.req='+encodeURIComponent(JSON.stringify([[[rpc,JSON.stringify(inner),null,"generic"]]]))+'&at='+encodeURIComponent(at())+'&';
    return await new Promise((res)=>{const x=new XMLHttpRequest();x.open('POST',url,true);
      x.setRequestHeader('X-Same-Domain','1');x.setRequestHeader('Content-Type','application/x-www-form-urlencoded;charset=utf-8');
      x.withCredentials=true;x.onload=()=>res({s:x.status,t:x.responseText||''});x.onerror=()=>res({s:0,t:'onerror'});x.send(body);});
  }
  const uuids=(t)=>Array.from(new Set(clean(t).match(/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/g)||[]));
  function diag(t){return {unusual:t.indexOf('UNUSUAL_ACTIVITY')!==-1, e13:/\[13\]/.test(t), e3:/,\[3\]/.test(t), xsrf:t.indexOf('xsrf')!==-1};}
  // gera imagem (ref=null -> t2i ; ref=mediaId -> i2i que trava a identidade). Retorna {ok, mediaId}
  async function genImg(prompt, ref){
    const tk=await tok('IMAGE_GENERATION');
    const refSlot = ref ? [[ref,null,null,null,1]] : null;
    const FIELDS=[null,null,refSlot,SEED(),2,"GEM_PIX_2",null,CTX(tk),[[[prompt]]],null,null,null,U(),U()];
    const r=await batch('ogiZ0b',[null,[FIELDS],1,CTX(tk),[U()]]);
    const d=diag(r.t); const id=uuids(r.t)[0]||'';
    return {ok: r.s===200 && !!id && !d.unusual && !d.e3 && !d.e13, mediaId:id, ...d, raw:r.t.slice(0,220)};
  }
  // submete video i2v. Retorna {ok, videoId} — videoId = 2o uuid do response (o que se pola)
  // O MODELO vem de window.__VMODEL (o Python resolve por env; ver bloco "MODELO DE VÍDEO"). Default
  // = lite low priority (custo zero, exige Ultra). modelErr = a conta não tem esse modelo -> o Python
  // cai pro veo_3_1_r2v_lite (pago) sozinho.
  async function submitVid(prompt, imgId){
    const tk=await tok('VIDEO_GENERATION');
    const MODEL = window.__VMODEL || "veo_3_1_r2v_lite_low_priority";
    const inner=[[[[null,null,[[[prompt]]]],[[null,imgId]],MODEL,1,null,[null,null,null,null,U(),U()]]],CTX(tk),[U(),1]];
    const r=await batch('MZZa6b',inner); const d=diag(r.t); const ids=uuids(r.t);
    const modelErr = r.t.indexOf('PUBLIC_ERROR_MODEL_')!==-1;
    return {ok: r.s===200 && ids.length>=2 && !d.unusual && !d.e3, videoId: ids[1]||'', modelErr, ...d, raw:r.t.slice(0,220)};
  }
  // poll universal (imagem ou video) por mediaId. tipo='image'|'video'. Retorna {pronto, url, falhou}
  async function pollAsset(mediaId, tipo){
    const r=await batch('as29s',[mediaId]); const c=clean(r.t);
    // 🔴 a resposta pode trazer URLs de OUTROS assets; a certa e a que contem o PROPRIO mediaId.
    // Sem URL do proprio id = ainda nao pronto (fallback "primeira URL" baixaria o video alheio).
    const url=(c.match(new RegExp('https?://flow-content\\.google/'+tipo+'/'+mediaId+'[^"\\s\\\\]*'))||[])[0]||'';
    return {pronto: !!url, url, falhou: c.indexOf('Media not found')!==-1, raw:r.t.slice(0,160)};
  }
  return {genImg, submitVid, pollAsset};
})();
"""
js(CORE)
if js("window.__flowcore ? 'ok' : ''") != "ok":
    print("ABORT: falha ao injetar o core"); raise SystemExit

# ── COLHEITA DE TOKEN (ATUALIZAÇÃO SET/2026 nº2) ─────────────────────────────
# O Google pôs reCAPTCHA no Flow: mintar o token direto = UNUSUAL_ACTIVITY. Só o token nascido na
# CLOSURE do app passa. Solução: interceptar a chamada de geração do próprio app (Fetch), ler o token
# fresco do corpo, e ABORTAR a chamada (nada gera, o token fica válido) — e usar esse token na nossa
# geração. A ACTION do token casa com o MODO do composer (Image=ogiZ0b / Video=MZZa6b), então o modo
# é setado por FASE antes de colher. Cada colheita deixa um tile "Failed" no projeto (só cosmético).
from browser_harness.helpers import cdp, drain_events

def _clique(x, y):
    for tp in ("mousePressed", "mouseReleased"):
        cdp("Input.dispatchMouseEvent", type=tp, x=x, y=y, button="left", clickCount=1, session_id=sid)

def colher_token():
    # 🔴 O clique em "Start generation" dispara VÁRIAS chamadas batchexecute; só UMA carrega o token
    # (a geração de verdade). ABORTAR essa (nada gera) e DEIXAR PASSAR as outras. Abortar "a primeira que
    # aparece" é frágil: se a de geração não for a 1a, ela VAZA no Fetch.disable e o Flow gera um "vídeo de x".
    cdp("Fetch.enable", patterns=[{"urlPattern": "*batchexecute*", "requestStage": "Request"}], session_id=sid)
    drain_events()
    js(r"""(function(){const pm=document.querySelector('.ProseMirror');if(pm)pm.focus();return 1;})()""")
    cdp("Input.insertText", text="x", session_id=sid)
    time.sleep(0.6)
    b = json.loads(js(r"""(function(){const bt=[...document.querySelectorAll('button')].find(x=>/Start generation|Iniciar gera/i.test(x.getAttribute('aria-label')||''));if(!bt)return '{}';const r=bt.getBoundingClientRect();return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),dis:!!bt.disabled});})()""") or "{}")
    if not b or b.get("dis"):
        cdp("Fetch.disable", session_id=sid); return None
    _clique(b["x"], b["y"])
    token = None; fim = time.time() + 25
    while time.time() < fim and token is None:
        time.sleep(0.3)
        for e in drain_events():
            if e.get("method") != "Fetch.requestPaused": continue
            rid = e["params"]["requestId"]
            body = e["params"]["request"].get("postData", "")
            if not body:
                try: body = cdp("Fetch.getRequestPostData", requestId=rid, session_id=sid).get("postData", "")
                except Exception: body = ""
            toks = re.findall(r'0[cC][A-Za-z0-9_\-]{100,}', _urllib.unquote_plus(body or ""))
            if toks:
                cdp("Fetch.failRequest", requestId=rid, errorReason="Aborted", session_id=sid)  # a de GERAÇÃO -> aborta
                token = toks[0]; break
            else:
                try: cdp("Fetch.continueRequest", requestId=rid, session_id=sid)  # não é geração -> deixa passar
                except Exception: pass
    cdp("Fetch.disable", session_id=sid)
    js(r"""(function(){const b=[...document.querySelectorAll('button')].find(x=>/Clear prompt|Apagar/i.test(x.getAttribute('aria-label')||''));if(b)b.click();return 1;})()""")
    return token

def inject_token(tries=3):
    for _ in range(tries):
        t = colher_token()
        if t:
            js("window.__HTOKEN=" + json.dumps(t)); return True
        time.sleep(1)
    return False

def _abre_settings():
    for _ in range(5):
        if js(r"""(function(){const leafs=[...document.querySelectorAll('*')].filter(x=>x.children.length===0);const has=t=>leafs.some(e=>(e.textContent||'').trim()===t);return (has('Image')||has('Imagem'))&&(has('Video')||has('Vídeo'));})()"""):
            return True
        js(r"""(function(){const b=[...document.querySelectorAll('button')].find(x=>/Settings trigger|Gatilho de config/i.test(x.getAttribute('aria-label')||''));if(b)b.click();return 1;})()""")
        time.sleep(1.2)
    return False

def set_mode(mode):  # 'Image' (ogiZ0b) | 'Video' (MZZa6b). Casa a action do token com o RPC da fase.
    if not _abre_settings(): print("WARN: menu de settings nao abriu (modo", mode + ")"); return
    rx = "^(Image|Imagem)$" if mode == "Image" else "^(Video|Vídeo)$"
    g = json.loads(js(r"""(function(){const e=[...document.querySelectorAll('*')].find(x=>x.children.length===0&&new RegExp(%R%).test((x.textContent||'').trim()));if(!e)return '{}';const r=(e.closest('button')||e).getBoundingClientRect();return JSON.stringify({x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2),ok:r.width>0});})()""".replace("%R%", json.dumps(rx))) or "{}")
    if not g.get("ok"): print("WARN: modo", mode, "nao achado no menu"); return
    _clique(g["x"], g["y"]); time.sleep(1.0)
    cdp("Input.dispatchKeyEvent", type="keyDown", key="Escape", session_id=sid)
    cdp("Input.dispatchKeyEvent", type="keyUp", key="Escape", session_id=sid); time.sleep(0.5)
    print("composer em modo", mode)

# ── PONTES Python -> core (cada uma escreve global, Python lê) ────────────────
def _run(js_call, var, tries=90, dt=2):
    js(f"window.{var}=null; (async()=>{{ try{{ window.{var}=JSON.stringify(await {js_call}); }}catch(e){{ window.{var}=JSON.stringify({{ok:false,err:String(e)}}); }} }})(); '1'")
    for _ in range(tries):
        time.sleep(dt)
        v = js(f"window.{var}")
        if v: return json.loads(v)
    return {"ok": False, "err": "timeout"}

def gen_img(prompt, ref=None):
    if not inject_token(): return {"ok": False, "err": "colheita de token falhou (modo Image)"}
    r = _run(f"window.__flowcore.genImg({json.dumps(prompt)},{json.dumps(ref)})", "__gi", 40, 2)
    if not r.get("ok"): return r
    # a imagem só é animável DEPOIS de pronta — poll até a URL /image/ aparecer
    for _ in range(30):
        p = _run(f"window.__flowcore.pollAsset({json.dumps(r['mediaId'])},'image')", "__pi", 3, 1)
        if p.get("pronto"): r["url"] = p["url"]; break
        time.sleep(3)
    return r

def submit_vid(prompt, img):
    if not inject_token(): return {"ok": False, "err": "colheita de token falhou (modo Video)"}
    js("window.__VMODEL=" + json.dumps(VMODEL))
    r = _run(f"window.__flowcore.submitVid({json.dumps(prompt)},{json.dumps(img)})", "__sv", 30, 1)
    # 🔴 fallback: a conta não tem o modelo escolhido (ex.: 'gratis'/low_priority sem Ultra) -> lite pago
    if (not r.get("ok")) and r.get("modelErr") and VMODEL != VMODEL_FALLBACK:
        print(f"   modelo '{VMODEL}' indisponivel nesta conta -> caindo pro '{VMODEL_FALLBACK}'")
        if inject_token():
            js("window.__VMODEL=" + json.dumps(VMODEL_FALLBACK))
            r = _run(f"window.__flowcore.submitVid({json.dumps(prompt)},{json.dumps(img)})", "__sv", 30, 1)
    return r

def poll_vid(video_id):
    return _run(f"window.__flowcore.pollAsset({json.dumps(video_id)},'video')", "__pv", 3, 1)

# ── FASES ────────────────────────────────────────────────────────────────────
if PHASE == "masters":
    set_mode("Image")  # colheita de token de IMAGEM casa com ogiZ0b
    for key, p in spec.get("personas", {}).items():
        st = state["personas"].setdefault(key, {})
        if p.get("master_mediaId"):
            st["mediaId"] = p["master_mediaId"]; print(key, "USA EXISTENTE"); save(); continue
        if st.get("mediaId"): print(key, "SKIP"); continue
        r = gen_img(p["prompt_img"])
        if r.get("ok"): st["mediaId"] = r["mediaId"]; st["url"] = r.get("url", ""); print(key, "MASTER OK")
        else: print(key, "FALHOU:", r.get("raw", r.get("err", ""))[:150])
        save(); time.sleep(1)

elif PHASE == "scenes":
    set_mode("Image")  # cenas i2i tambem sao imagem (ogiZ0b)
    for item in spec["itens"]:
        for c in item["cenas"]:
            cid = f'{item["id"]}_{c["n"]}'
            st = state["cenas"].setdefault(cid, {})
            if st.get("img"): continue                       # idempotente
            pk = c.get("persona_key", "")
            ref = state["personas"].get(pk, {}).get("mediaId") if pk else None  # i2i trava a identidade
            # 🔴 GUARDA (nunca gerar rosto aleatório): cena que PEDE persona mas cujo master NÃO está
            # no state não pode virar t2i puro — o Flow inventaria uma pessoa diferente, em silêncio.
            # Causa clássica: apagar o state.json (que guarda o master) ou pular a fase 'masters'.
            # LEI: sempre rode PHASE=masters ANTES de scenes, e nunca apague o state com masters feitos.
            if pk and not ref:
                st["img_erro"] = f"persona '{pk}' sem master no state — rode PHASE=masters ANTES (e nao apague o state.json com masters ja feitos)"
                print(cid, "PULADO (sem rosto de referencia):", st["img_erro"]); save(); continue
            r = gen_img(c["prompt_img"], ref)
            if r.get("ok"):
                st["img"] = r["mediaId"]; st["img_url"] = r.get("url", ""); print(cid, "IMG OK")
            else:
                st["img_erro"] = r.get("raw", r.get("err", ""))[:120]; print(cid, "IMG FALHOU:", st["img_erro"])
            save(); time.sleep(1)

elif PHASE == "submit":
    # 🚦 só rode depois do GATE DE FRAMES. Frame ruim submetido = clipe ruim garantido.
    set_mode("Video")  # colheita de token de VIDEO casa com MZZa6b (r2v)
    for item in spec["itens"]:
        for c in item["cenas"]:
            cid = f'{item["id"]}_{c["n"]}'
            st = state["cenas"].setdefault(cid, {})
            if st.get("video") or not st.get("img"): continue
            r = submit_vid(c["prompt_video"], st["img"])
            if r.get("ok"): st["video"] = r["videoId"]; print(cid, "SUB OK")
            else: st["sub_erro"] = r.get("raw", r.get("err", ""))[:120]; print(cid, "SUB FALHOU:", st["sub_erro"])
            save(); time.sleep(1)

elif PHASE == "poll":
    pend = {cid: st["video"] for cid, st in state["cenas"].items()
            if st.get("video") and not st.get("done") and not st.get("failed")}
    if not pend:
        print("nada pendente")   # ⚠️ 'nada pendente' ≠ sucesso: confira os failed no state
    else:
        for cid, vid in pend.items():
            p = poll_vid(vid)
            if p.get("pronto"):
                state["cenas"][cid]["done"] = True; state["cenas"][cid]["video_url"] = p["url"]; print(cid, "PRONTO")
            elif p.get("falhou"):
                state["cenas"][cid]["failed"] = True; print(cid, "FALHOU")
            else:
                print(cid, "gerando...")
        save()
        d = sum(1 for s in state["cenas"].values() if s.get("done"))
        f = sum(1 for s in state["cenas"].values() if s.get("failed"))
        pp = sum(1 for s in state["cenas"].values() if s.get("video") and not s.get("done") and not s.get("failed"))
        print(f"prontos:{d} falhas:{f} pendentes:{pp}")

elif PHASE == "retry":
    # Falha aleatória do Veo é rotina (~10-30%/rodada). Isto libera as falhadas pra ressubmeter.
    # A MESMA cena falhando 2-3x NÃO é azar: é conteúdo (nome próprio, celebridade, filtro). Reescrever.
    n = 0
    for cid, st in state["cenas"].items():
        if st.get("failed"): st.pop("failed"); st.pop("video", None); n += 1
        if st.get("sub_erro"): st.pop("sub_erro"); n += 1
        if st.get("img_erro"): st.pop("img_erro"); n += 1
    save(); print(f"{n} itens liberados — rode a fase que faltou de novo")

else:
    print("PHASE invalida. Use: masters | scenes | submit | poll | retry")
