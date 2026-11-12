# -*- coding: utf-8 -*-
# gate_clipes.py — o gate PÓS-DOWNLOAD, 3 camadas por clipe. Roda depois do flow_download.py, antes da montagem.
#   1. tamanho > 200KB           (arquivo de 14 bytes/HTML = sessão expirada, não é vídeo)
#   2. SSIM frame-0 × frame-base  (< 0,50 = clipe CRUZADO — veio o vídeo de outra cena/ad)
#   3. whisper × fala do spec     (dice < 0,60 = fala errada/colisão; e "lixo na cabeça" = sílaba fantasma antes da frase)
# Normaliza número por extenso ↔ dígito antes de comparar (whisper escreve "30" onde o roteiro diz "trinta";
# sem isso, clipe perfeito reprova). Resultado em GATE-CLIPES.json (a montagem lê pra cortar cabeça).
#
# Uso (na pasta da leva): python3 gate_clipes.py            → todos os ads com clipes em clips/
#                          python3 gate_clipes.py AD-01 AD-02
# Env: LEVA=/pasta (default: pasta atual) · WHISPER_MODEL=/caminho/ggml-small.bin (default: procura em ~/whisper, ~/tools/whisper, ./tools/whisper)
#      LANG_FALA=pt (default: idioma do spec) · SEM_WHISPER=1 (pula a camada 3)
import json, os, re, sys, glob, subprocess, unicodedata, tempfile

LEVA = os.environ.get("LEVA", os.getcwd())
CL, FR = os.path.join(LEVA, "clips"), os.path.join(LEVA, "frames")
REPORT = os.path.join(LEVA, "GATE-CLIPES.json")
rep = json.load(open(REPORT)) if os.path.exists(REPORT) else {}
TMP = tempfile.mkdtemp(prefix="gate_")

def acha_whisper():
    c = [os.environ.get("WHISPER_MODEL")] + [os.path.expanduser(p) for p in (
        "~/whisper/ggml-small.bin", "~/tools/whisper/ggml-small.bin", "./tools/whisper/ggml-small.bin",
        "~/whisper.cpp/models/ggml-small.bin", "~/whisper/ggml-base.bin", "~/tools/whisper/ggml-base.bin")]
    for p in c:
        if p and os.path.exists(p): return p
    return None
WHISPER = None if os.environ.get("SEM_WHISPER") else acha_whisper()
if not os.environ.get("SEM_WHISPER") and not WHISPER:
    print("⚠️  modelo whisper não encontrado (WHISPER_MODEL=/caminho/ggml-small.bin) — camada 3 (fala) será PULADA")

# números por extenso (pt/es/en) → dígito, dos dois lados
NUM = {"um":"1","uma":"1","dois":"2","duas":"2","tres":"3","quatro":"4","cinco":"5","seis":"6","sete":"7","oito":"8",
       "nove":"9","dez":"10","onze":"11","doze":"12","treze":"13","quatorze":"14","catorze":"14","quinze":"15",
       "dezesseis":"16","dezessete":"17","dezoito":"18","dezenove":"19","vinte":"20","trinta":"30","quarenta":"40",
       "cinquenta":"50","sessenta":"60","setenta":"70","oitenta":"80","noventa":"90","cem":"100","cento":"100","mil":"1000",
       "uno":"1","dos":"2","cuatro":"4","siete":"7","ocho":"8","nueve":"9","diez":"10","veinte":"20","treinta":"30",
       "cuarenta":"40","cincuenta":"50","cien":"100",
       "one":"1","two":"2","three":"3","four":"4","five":"5","six":"6","seven":"7","eight":"8","nine":"9","ten":"10",
       "twenty":"20","thirty":"30","forty":"40","fifty":"50","sixty":"60","hundred":"100","thousand":"1000"}

def norm(s):
    s = unicodedata.normalize("NFD", s or "").encode("ascii", "ignore").decode().lower()
    return [NUM.get(w, w) for w in re.sub(r"[^a-z0-9 ]", " ", s).split()]

def dice(a, b):
    A = set(zip(a, a[1:])) or set((w,) for w in a)
    B = set(zip(b, b[1:])) or set((w,) for w in b)
    if not A or not B: return 0.0
    return 2 * len(A & B) / (len(A) + len(B))

def ssim_f0(clip, ref):
    f0 = os.path.join(TMP, "f0.png")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",clip,"-vframes","1",f0],capture_output=True)
    r = subprocess.run(["ffmpeg","-loglevel","info","-y","-i",f0,"-i",ref,
                        "-filter_complex","[1:v][0:v]scale2ref[r][m];[m][r]ssim","-f","null","-"],
                       capture_output=True, text=True)
    m = re.search(r"All:(\d+\.?\d*)", r.stderr)
    return float(m.group(1)) if m else None

def whisper_txt(clip, lang):
    wav = os.path.join(TMP, "qa.wav")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",clip,"-ar","16000","-ac","1",wav],capture_output=True)
    r = subprocess.run(["whisper-cli","-m",WHISPER,"-l",lang,"-nt","-f",wav],capture_output=True,text=True)
    return r.stdout.strip().replace("\n", " ")

alvo = sys.argv[1:]
sus, checados = [], 0
specs = [s for s in sorted(glob.glob(os.path.join(LEVA, "specs", "*.json"))) if not s.endswith(".state.json")]
if not specs: sys.exit(f"nenhum spec em {LEVA}/specs/")
for sp in specs:
    spec = json.load(open(sp))
    for item in spec["itens"]:
        ad = item["id"]
        if alvo and ad not in alvo: continue
        lang = os.environ.get("LANG_FALA") or item.get("idioma", "pt")
        for c in item["cenas"]:
            cid = f'{ad}_{c["n"]}'
            clip = os.path.join(CL, f"{cid}.mp4")
            if not os.path.exists(clip): continue
            checados += 1
            e = rep.setdefault(cid, {})
            e["size"] = os.path.getsize(clip)
            if e["size"] < 200000:
                e["verdict"] = "SIZE_FAIL"; sus.append(cid); print(f"{cid}: SIZE_FAIL ({e['size']} bytes) — sessão expirada? baixe de novo"); continue
            if "ssim" not in e:
                ref = os.path.join(FR, f"{cid}.jpg")
                e["ssim"] = ssim_f0(clip, ref) if os.path.exists(ref) else None
            fala = (c.get("fala") or "").strip()
            if fala and WHISPER and "dice" not in e:
                e["whisper"] = whisper_txt(clip, lang)
                e["dice"] = round(dice(norm(fala), norm(e["whisper"])), 3)
                # lixo na CABEÇA: em que posição do whisper a abertura do roteiro começa (offset ≥2 = sílaba fantasma antes)
                S, W = norm(fala)[:6], norm(e["whisper"])
                best = (0, -1.0)
                for k in range(0, min(7, max(1, len(W) - 1))):
                    d = dice(S, W[k:k + 6])
                    if d > best[1]: best = (k, d)
                e["ini_offset"], e["ini_score"] = best[0], round(best[1], 3)
            bad_ssim = e.get("ssim") is not None and e["ssim"] < 0.5
            bad_dice = bool(fala) and "dice" in e and e["dice"] < 0.60
            bad_ini = bool(fala) and "dice" in e and e["dice"] >= 0.60 and e.get("ini_offset", 0) >= 2
            e["verdict"] = "FAIL_SSIM" if bad_ssim else "FAIL_FALA" if bad_dice else "FAIL_INICIO" if bad_ini else "OK"
            if e["verdict"] != "OK":
                sus.append(cid)
                print(f"{cid}: {e['verdict']} ssim={e.get('ssim')} dice={e.get('dice')}")
                if bad_dice or bad_ini: print(f"   roteiro: {fala[:90]}\n   whisper: {e.get('whisper','')[:90]}")
                if bad_ssim: print("   -> frame-0 não bate com o frame-base: clipe CRUZADO. Marque pra retry (PHASE=retry) e re-baixe.")
                if bad_dice: print("   -> fala errada/inventada: regerar SÓ esta cena (retry).")
                if bad_ini: print("   -> lixo na CABEÇA do clipe: a montagem corta a cabeça sozinha (lê este relatório); sem re-render")
            json.dump(rep, open(REPORT, "w"), indent=1)
n_ok = sum(1 for k, v in rep.items() if v.get("verdict") == "OK")
print(f"\nGATE: {n_ok} OK · {len(sus)} reprovados de {checados} checados agora -> {sus}")
print(f"relatório: {REPORT}")
