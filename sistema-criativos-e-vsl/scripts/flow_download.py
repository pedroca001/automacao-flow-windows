# DOWNLOAD DOS CLIPES — pela rota media.getMediaUrlRedirect, usando o NAME da mídia.
# Roda DENTRO do browser-harness:
#   FLOW_PROJECT=<id> SPEC=specs/AD-01.json OUT=clips browser-harness < scripts/flow_download.py
#
# 🔴 HISTÓRIA DAS ROTAS (pra ninguém cair no buraco de novo):
#   - A rota antiga media.fetchMedia (base64 in-page) MORREU em ago/2026: devolve
#     400 INVALID_ARGUMENT pra qualquer mediaKey. Se o seu download parou com esse
#     erro, é isso — não é a sua sessão, não é o seu id.
#   - A rota viva é media.getMediaUrlRedirect com o MESMO identificador que o poll
#     já usa (o "op" gravado no state pelo driver). Ela responde com um redirect
#     pra URL assinada do vídeo — é seguir o redirect e gravar o arquivo.
#   - A auth aqui é por COOKIE de sessão, e o script pega os cookies do SEU Chrome
#     logado via CDP, sozinho. Nenhum passo manual, nenhum cookie copiado na mão.
#     (A lei "requisição nasce dentro da aba" vale pro SUBMIT, por causa do
#     reCAPTCHA. Download não tem captcha — cookie de sessão basta.)

import json, os, time, urllib.request, urllib.parse
try:
    import fcntl
except ImportError:
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
    from flow_platform import locks as fcntl

SPEC_PATH = os.environ["SPEC"]
PROJECT   = os.environ["FLOW_PROJECT"]
OUT       = os.environ.get("OUT", "clips")
LOCK_PATH = os.environ.get("FLOW_LOCK", os.path.expanduser("~/.flow_lane.lock"))
os.makedirs(OUT, exist_ok=True)

# mesma lane do driver: download e submit NUNCA disputam a aba
_LOCK = open(LOCK_PATH, "a")
print("aguardando lane do Flow...", flush=True)
fcntl.flock(_LOCK, fcntl.LOCK_EX)
print("lane adquirida", flush=True)

def attach_sem_focar(target_id):
    from browser_harness.helpers import cdp, _send
    sid = cdp("Target.attachToTarget", targetId=target_id, flatten=True)["sessionId"]
    _send({"meta": "set_session", "session_id": sid, "target_id": target_id})
    return sid

achou = False
for t in list_tabs():
    if PROJECT in (t.get("url") or ""):
        attach_sem_focar(t["targetId"]); achou = True; break
if not achou:
    print("ABORT: aba do projeto", PROJECT, "nao esta aberta"); raise SystemExit

# cookies da sessão logada, direto do Chrome (inclui os HttpOnly) — zero passo manual
from browser_harness.helpers import cdp
_cook  = cdp("Network.getCookies", urls=["https://labs.google/"])["cookies"]
COOKIE = "; ".join(f'{c["name"]}={c["value"]}' for c in _cook)
if "session-token" not in COOKIE:
    print("ABORT: sessao do Flow nao encontrada nos cookies — logue na aba e repita")
    raise SystemExit

def baixar(name, out):
    url = ("https://labs.google/fx/api/trpc/media.getMediaUrlRedirect?name="
           + urllib.parse.quote(name, safe=""))
    req = urllib.request.Request(url, headers={
        "Cookie": COOKIE,
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)",
    })
    try:
        # urllib segue o redirect sozinho — a resposta final já é o vídeo
        with urllib.request.urlopen(req, timeout=300) as r, open(out, "wb") as f:
            while True:
                chunk = r.read(1 << 20)
                if not chunk: break
                f.write(chunk)
    except Exception as e:
        print("  ERRO download:", str(e)[:160]); return False
    ok = os.path.exists(out) and os.path.getsize(out) > 200000
    # <200KB = HTML de erro / sessão expirada, não clipe → renovar login e repetir
    print(f"  {os.path.basename(out)}: {os.path.getsize(out)//1024}KB",
          "OK" if ok else "PEQUENO DEMAIS (falha — sessao expirada?)")
    if not ok and os.path.exists(out): os.remove(out)
    return ok

spec  = json.load(open(SPEC_PATH))
state = json.load(open(SPEC_PATH + ".state.json"))
tot = ok_n = 0
for item in spec["itens"]:
    for c in item["cenas"]:
        cid = f'{item["id"]}_{c["n"]}'
        e = state.get("cenas", {}).get(cid, {})
        if not (e.get("op") and e.get("done")): continue          # só baixa o que o poll deu SUCCESSFUL
        out = os.path.join(OUT, f"{cid}.mp4")
        if os.path.exists(out) and os.path.getsize(out) > 200000: continue   # idempotente
        tot += 1; print(cid, "baixando...")
        if baixar(e["op"], out): ok_n += 1
        time.sleep(1)
print(f"DOWNLOAD FIM: {ok_n}/{tot} baixados nesta rodada")
# ⚠️ tamanho NÃO prova conteúdo. O gate de 3 camadas (size + SSIM do frame-0 + whisper vs roteiro)
#    está em 01-CRIATIVOS/05-QA-E-LEIS.md — é ele que pega clipe cruzado.
