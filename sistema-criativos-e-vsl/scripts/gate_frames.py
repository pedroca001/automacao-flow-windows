# -*- coding: utf-8 -*-
# gate_frames.py — baixa os FRAMES gerados (masters e cenas) e monta GRADES pra você conferir ANTES do submit.
# É o gate que evita gastar geração de vídeo em cima de frame errado (rosto trocado, objeto fantasma, texto pintado).
#
# Uso (na pasta da leva, onde está specs/):
#   python3 gate_frames.py masters   → frames/GRADE-MASTERS.jpg  (todos os rostos-âncora lado a lado)
#   python3 gate_frames.py scenes    → frames/GRADE-<AD>.jpg      (uma linha por ad, uma coluna por cena)
#   LEVA=/outra/pasta python3 gate_frames.py scenes
# Depois: abra a grade e peça pro Claude descrever CADA quadro contra o que o prompt pediu (é o "gate visual").
# Os frames individuais ficam em frames/<AD>_<n>.jpg — o gate_clipes.py usa eles como referência (SSIM).
import json, os, subprocess, sys, glob

LEVA = os.environ.get("LEVA", os.getcwd())
FR = os.path.join(LEVA, "frames"); os.makedirs(FR, exist_ok=True)
modo = sys.argv[1] if len(sys.argv) > 1 else "masters"

def dl(url, out):
    if os.path.exists(out) and os.path.getsize(out) > 10000: return True
    subprocess.run(["curl", "-sL", "-m", "60", "-o", out, url], capture_output=True)
    ok = os.path.exists(out) and os.path.getsize(out) > 10000
    if not ok and os.path.exists(out): os.remove(out)
    return ok

def grade(imgs, out, cols):
    n = len(imgs)
    lay = "|".join(f"{(i % cols) * 270}_{(i // cols) * 480}" for i in range(n))
    fc = "".join(f"[{i}:v]scale=270:480:force_original_aspect_ratio=increase,crop=270:480[v{i}];" for i in range(n))
    fc += "".join(f"[v{i}]" for i in range(n)) + (f"xstack=inputs={n}:layout={lay}[o]" if n > 1 else "null[o]")
    r = subprocess.run(["ffmpeg", "-loglevel", "error", "-y"] + sum([["-i", i] for i in imgs], []) +
                       ["-filter_complex", fc, "-map", "[o]", out], capture_output=True, text=True)
    if r.returncode != 0: print("  grade falhou:", r.stderr[-200:])
    return out

specs = sorted(glob.glob(os.path.join(LEVA, "specs", "*.json")))
specs = [s for s in specs if not s.endswith(".state.json")]
if not specs: sys.exit(f"nenhum spec em {LEVA}/specs/ (rode gerar_specs.py antes)")

if modo == "masters":
    imgs, vistos = [], set()
    for sp in specs:
        stp = sp + ".state.json"
        if not os.path.exists(stp): continue
        st = json.load(open(stp))
        for k, v in st.get("personas", {}).items():
            if k in vistos or not v.get("fife"): continue
            vistos.add(k)
            out = os.path.join(FR, f"master_{k}.jpg")
            print(k, "OK" if dl(v["fife"], out) else "download FALHOU")
            if os.path.exists(out): imgs.append(out)
    if imgs: print("GRADE:", grade(imgs, os.path.join(FR, "GRADE-MASTERS.jpg"), 6))
    else: print("nenhum master no state ainda — rode PHASE=masters no driver")
else:
    for sp in specs:
        stp = sp + ".state.json"
        if not os.path.exists(stp): continue
        spec = json.load(open(sp)); st = json.load(open(stp))
        for item in spec["itens"]:
            ad = item["id"]; imgs = []
            for c in item["cenas"]:
                cid = f"{ad}_{c['n']}"; e = st.get("cenas", {}).get(cid, {})
                if not e.get("img_fife"): print(f"{cid}: SEM FRAME ainda"); continue
                out = os.path.join(FR, f"{cid}.jpg")
                if dl(e["img_fife"], out): imgs.append(out)
                else: print(f"{cid}: download FALHOU")
            if imgs: print(f"GRADE {ad}: {len(imgs)} frames ->", grade(imgs, os.path.join(FR, f"GRADE-{ad}.jpg"), len(imgs)))
