# -*- coding: utf-8 -*-
# montar_leva.py — a MONTAGEM FINAL de cada ad, clipe a clipe → finais/<AD>.mp4 (1080x1920, 24fps, yuv420p).
#
# Pipeline por ad (a Parte 2 do 01-CRIATIVOS/04-PIPELINE-TECNICO.md, em código):
#   1. trim por whisper (corta o silêncio/fade fantasma depois da última palavra; corta a CABEÇA se o gate acusou lixo)
#   2. concat por FILTRO (normaliza fps/tamanho/SAR — o demuxer congela vídeo depois da cena 1)
#   3. legendas ASS queimadas com o texto do ROTEIRO (whisper só dá o TIMING), blocos de 3-4 palavras, terço inferior
#   4. faixa de headline no topo (banner.py, cor alterna a cada 3 ads) · 5. CTA animado nos últimos 10s
#   6. crop leve da marca-d'água (opcional, CROP_WM=1) · 7. 1080x1920 · 8. varredura de integridade (moov atom)
#
# DINÂMICA (Atualização 04 — docs 01-CRIATIVOS/07 e 08), tudo LIGADO por padrão e desligável por env:
#   • PUNCH-IN jump-cut: clipe do corpo > 4,6s ganha a 2ª metade com zoom 1,12 (corte visual sem trocar conteúdo, ritmo de VSL editada à mão).
#     O gancho (clipe 1) fica inteiro. PUNCH_IN=0 desliga · PUNCH_MIN=4.6 · PUNCH_Z=1.12
#   • GANCHO por mecânica (spec.itens[].gancho.mecanica, escrito pelo gerar_specs.py):
#     SPLIT = clipe 1 (pessoa, topo 1080x1150) + clipe 0 (insert, base 1080x770) empilhados, áudio da pessoa
#     INSERT_PRIMEIRO = clipe 0 cortado em ~1,6s (áudio a 25%) e depois o clipe 1 · ACAO/ESTRANHO = o clipe 1 é o gancho
#   • CORTE POR FALA: gap entre palavras > 0,55s aparado pra ~0,30s (whisper por palavra) + silêncio > 0,3s a -25dB removido em loop.
#     É o que separa "gente falando" de "IA esperando o próximo prompt". SEM_APARAR=1 desliga.
#   Spec antigo (sem gancho, sem tipo) continua montando exatamente como antes (+ punch-in e corte por fala, se não desligar).
#
# Uso (na pasta da leva, com specs/ e clips/ prontos):  python3 montar_leva.py            → todos
#                                                       python3 montar_leva.py AD-01 AD-05
# Env: LEVA=/pasta · WHISPER_MODEL=/caminho/ggml-base.bin (ou small) · FFMPEG=/caminho/ffmpeg-com-libass
#      MIN_DUR=60 (aviso se o final ficar abaixo; em orgânico use MIN_DUR=15) · SEM_LEGENDA=1 · SEM_CTA=1 · SEM_HEADLINE=1 · CROP_WM=1
#      PUNCH_IN=0 · PUNCH_MIN=4.6 · SEM_APARAR=1
# Overrides de corte por clipe (quando o whisper clipa a última palavra): trim_overrides.json {"AD-01_3": 6.9}
# Requisitos: ffmpeg COM libass (ffmpeg -filters | grep ass), ffprobe, whisper-cli, python3 + Pillow.
import json, os, re, sys, glob, subprocess, difflib, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import banner as B

LEVA = os.environ.get("LEVA", os.getcwd())
CL, WK, FIN = (os.path.join(LEVA, d) for d in ("clips", "work", "finais"))
for d in (WK, FIN): os.makedirs(d, exist_ok=True)

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from flow_platform import filter_path
FF = os.environ.get("FFMPEG", "ffmpeg")
MIN_DUR = float(os.environ.get("MIN_DUR", "60"))
GATE = os.path.join(LEVA, "GATE-CLIPES.json")
gate = json.load(open(GATE)) if os.path.exists(GATE) else {}
OVR = os.path.join(LEVA, "trim_overrides.json")
overrides = json.load(open(OVR)) if os.path.exists(OVR) else {}
TMP = tempfile.mkdtemp(prefix="montar_")
PUNCH_IN = os.environ.get("PUNCH_IN", "1") != "0"
PUNCH_MIN = float(os.environ.get("PUNCH_MIN", "4.6"))
PUNCH_Z = float(os.environ.get("PUNCH_Z", "1.12"))
APARAR = not os.environ.get("SEM_APARAR")

def acha_whisper():
    c = [os.environ.get("WHISPER_MODEL")] + [os.path.expanduser(p) for p in (
        "~/whisper/ggml-base.bin", "~/tools/whisper/ggml-base.bin", "./tools/whisper/ggml-base.bin",
        "~/whisper/ggml-small.bin", "~/tools/whisper/ggml-small.bin", "./tools/whisper/ggml-small.bin",
        "~/whisper.cpp/models/ggml-base.bin")]
    for p in c:
        if p and os.path.exists(p): return p
    return None
WHISPER = acha_whisper()
# pro corte por FALA (timestamps por palavra) o modelo SMALL é bem mais preciso que o BASE; usa o small se estiver ao lado do base
WHISPER_FALA = (WHISPER.replace("ggml-base", "ggml-small") if WHISPER and "ggml-base" in WHISPER and os.path.exists(WHISPER.replace("ggml-base", "ggml-small")) else WHISPER)

def run(c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(" ".join(c[:4]) + " :: " + r.stderr[-600:])
def dur(p):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],
                                capture_output=True, text=True).stdout.strip() or 0)
def integro(p):
    r = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p],capture_output=True,text=True)
    return r.returncode == 0 and float(r.stdout.strip() or 0) > 1
def tem_libass():
    r = subprocess.run([FF,"-hide_banner","-filters"],capture_output=True,text=True)
    return " ass " in r.stdout or "subtitles" in r.stdout

def srt_blocks(srt):
    out = []
    if not os.path.exists(srt): return out
    for blk in open(srt, encoding="utf-8").read().strip().split("\n\n"):
        ls = blk.strip().split("\n")
        if len(ls) < 3: continue
        m = re.match(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)[.,](\d+)", ls[1])
        if not m: continue
        h1,m1,s1,ms1,h2,m2,s2,ms2 = map(int, m.groups())
        out.append({"start": h1*3600+m1*60+s1+ms1/1000, "end": h2*3600+m2*60+s2+ms2/1000, "text": " ".join(ls[2:])})
    return out

def whisper_srt(wav, lang):
    if not WHISPER: return []
    subprocess.run(["whisper-cli","-m",WHISPER,"-l",lang,"-osrt","-of",wav[:-4],"-f",wav],capture_output=True)
    return srt_blocks(wav[:-4] + ".srt")

def fala_ini_fim(clip, lang):
    """primeiro e último instante de fala (whisper) — pra cortar cabeça e cauda."""
    wav = os.path.join(TMP, "c.wav")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",clip,"-ar","16000","-ac","1",wav],capture_output=True)
    b = whisper_srt(wav, lang)
    return (b[0]["start"], b[-1]["end"]) if b else (None, None)

def alinha_legenda(blocks, frases, max_chars=22):
    """texto do ROTEIRO com o TIMING do whisper (difflib palavra a palavra); blocos de ~3-4 palavras."""
    ww = []
    for bl in blocks:
        ws = bl["text"].split()
        if not ws: continue
        d = bl["end"] - bl["start"]; chars = sum(len(w) for w in ws) or 1; t = bl["start"]
        for w in ws:
            wd = len(w) / chars * d; ww.append({"word": w, "start": t, "end": t + wd}); t += wd
    md = " ".join(frases).split()
    if not md: return []
    mt = [{"word": w, "start": 0, "end": 0} for w in md]
    if ww:
        sm = difflib.SequenceMatcher(None, [w["word"].lower().strip(".,!?") for w in ww], [w.lower().strip(".,!?") for w in md])
        for op, i1, i2, j1, j2 in sm.get_opcodes():
            if op in ("equal", "replace") and i2 > i1 and j2 > j1:
                s, e = ww[i1]["start"], ww[i2-1]["end"]; n = j2 - j1
                for k, j in enumerate(range(j1, j2)):
                    mt[j]["start"] = s + k/n*(e-s); mt[j]["end"] = s + (k+1)/n*(e-s)
        for i in range(len(mt)):
            if mt[i]["start"] == 0 and mt[i]["end"] == 0:
                prev = next((mt[k]["end"] for k in range(i-1, -1, -1) if mt[k]["end"] > 0), 0)
                nxt = next((mt[k]["start"] for k in range(i+1, len(mt)) if mt[k]["start"] > 0), ww[-1]["end"])
                mt[i]["start"], mt[i]["end"] = prev, nxt
    else:
        for i, m in enumerate(mt): m["start"], m["end"] = i * 0.4, (i+1) * 0.4
    ev, cur, ln = [], [], 0
    for m in mt:
        if cur and ln + len(m["word"]) + 1 > max_chars:
            ev.append(cur); cur, ln = [m], len(m["word"])
        else:
            cur.append(m); ln += len(m["word"]) + (1 if len(cur) > 1 else 0)
    if cur: ev.append(cur)
    return [{"start": c[0]["start"], "end": max(c[-1]["end"], c[0]["start"] + 0.35), "text": " ".join(w["word"] for w in c)} for c in ev]

# ── DINÂMICA: punch-in · gancho · corte por fala ─────────────────────────────────
def dims(p):
    o = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p],capture_output=True,text=True).stdout.strip()
    w, h = o.split(",")[:2]; return int(w), int(h)
def stream_dur(p, sel):
    o = subprocess.run(["ffprobe","-v","error","-select_streams",sel,"-show_entries","stream=duration","-of","csv=p=0",p],capture_output=True,text=True).stdout.strip()
    try: return float(o.split("\n")[0] or 0)
    except ValueError: return 0.0

def punch_in(path, z=PUNCH_Z, min_dur=PUNCH_MIN):
    """jump-cut das VSLs editadas à mão: 2ª metade com zoom fixo (não animado = não treme). Áudio intocado. Idempotente por marca no nome."""
    d = dur(path)
    if d < min_dur: return False
    mid = d / 2; W, H = dims(path)
    cw, ch = int(W/z//2*2), int(H/z//2*2)
    tmp = path[:-4] + ".punch.mp4"
    fc = (f"[0:v]trim=0:{mid:.2f},setpts=PTS-STARTPTS[a];"
          f"[0:v]trim={mid:.2f},setpts=PTS-STARTPTS,crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})*0.30,scale={W}:{H},setsar=1[b];"
          f"[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-i",path,"-filter_complex",fc,"-map","[v]","-map","0:a","-r","24",
         "-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",tmp])
    os.replace(tmp, path); return True

def gancho_split(pessoa, insert, out, top_h=1150):
    """SPLIT: pessoa em cima (crop do topo), insert embaixo (crop central), áudio da pessoa; o insert faz loop se for mais curto."""
    bot_h = 1920 - top_h; d = dur(pessoa)
    fc = (f"[0:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,crop=1080:{top_h}:0:0,setsar=1,fps=24[t];"
          f"[1:v]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,crop=1080:{bot_h}:0:{(1920-bot_h)//2},setsar=1,fps=24[b];"
          f"[t][b]vstack=inputs=2,format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-i",pessoa,"-stream_loop","-1","-i",insert,"-filter_complex",fc,
         "-map","[v]","-map","0:a","-t",f"{d:.2f}","-r","24","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-ac","2",out])

def gancho_insert_primeiro(insert, pessoa, out, dur_insert=1.6, vol=0.25):
    """INSERT_PRIMEIRO: ~1,6s do insert (som ambiente baixo) e a pessoa entra já falando."""
    fc = (f"[0:v]trim=0:{dur_insert:.2f},setpts=PTS-STARTPTS,scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1,fps=24[v0];"
          f"[0:a]atrim=0:{dur_insert:.2f},asetpts=PTS-STARTPTS,volume={vol},aresample=48000,aformat=channel_layouts=stereo[a0];"
          f"[1:v]scale=1080:1920,setsar=1,fps=24[v1];[1:a]aresample=48000,aformat=channel_layouts=stereo[a1];"
          f"[v0][a0][v1][a1]concat=n=2:v=1:a=1[v][a]")
    run(["ffmpeg","-loglevel","error","-y","-i",insert,"-i",pessoa,"-filter_complex",fc,"-map","[v]","-map","[a]",
         "-r","24","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",out])

def gaps_silencio(p, noise="-25dB", th=0.30):
    r = subprocess.run(["ffmpeg","-i",p,"-af",f"silencedetect=noise={noise}:d={th}","-f","null","-"],capture_output=True,text=True)
    st = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    en = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    total = dur(p)
    return [(s, en[i] if i < len(en) else total) for i, s in enumerate(st)]

def gaps_fala(p, lang, max_gap=0.55, keep=0.30):
    """gaps entre PALAVRAS (whisper -ml 1) maiores que max_gap → intervalos a cortar mantendo `keep` de respiro; apara cabeça muda e cauda muda."""
    if not WHISPER: return []
    wav = os.path.join(TMP, "gf.wav")
    subprocess.run(["ffmpeg","-loglevel","error","-y","-i",p,"-ar","16000","-ac","1",wav],capture_output=True)
    subprocess.run(["whisper-cli","-m",WHISPER_FALA,"-l",lang,"-ml","1","-osrt","-of",wav[:-4],"-f",wav],capture_output=True)
    segs = [(b["start"], b["end"]) for b in srt_blocks(wav[:-4] + ".srt")]
    if len(segs) < 2: return []
    total = dur(p); cortes = []
    if segs[0][0] > max_gap: cortes.append((0.05, segs[0][0] - keep))
    for (a0, a1), (b0, b1) in zip(segs, segs[1:]):
        if b0 - a1 > max_gap: cortes.append((a1 + keep/2, b0 - keep/2))
    if total - segs[-1][1] > 0.6: cortes.append((segs[-1][1] + 0.35, total - 0.02))
    return [(a, b) for a, b in cortes if b - a > 0.05]

def cortar_intervalos(src, out, cortes):
    total = dur(src); keeps, cur = [], 0.0
    for a, b in sorted(cortes):
        if a - cur > 0.03: keeps.append((cur, a))
        cur = max(cur, b)
    if total - cur > 0.03: keeps.append((cur, total))
    if not keeps: raise RuntimeError("todos os trechos seriam removidos")
    parts, labels = [], []
    for i, (a, b) in enumerate(keeps):
        parts.append(f"[0:v]trim={a:.3f}:{b:.3f},setpts=PTS-STARTPTS[v{i}];[0:a]atrim={a:.3f}:{b:.3f},asetpts=PTS-STARTPTS[a{i}];")
        labels.append(f"[v{i}][a{i}]")
    fc = "".join(parts) + "".join(labels) + f"concat=n={len(keeps)}:v=1:a=1[v][a]"
    run(["ffmpeg","-y","-loglevel","error","-i",src,"-filter_complex",fc,"-map","[v]","-map","[a]","-r","24",
         "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-b:a","192k",out])

def aparar(cat, lang, base):
    """1) gaps de FALA (whisper por palavra) → 2) silêncio real (-25dB, >0,3s) em loop até limpar (máx 6). Nunca mata a montagem: avisa e segue."""
    cur = cat
    try:
        gf = gaps_fala(cur, lang)
        if gf:
            nxt = base + "_f.mp4"; cortar_intervalos(cur, nxt, gf); cur = nxt
            print(f"  corte por fala: {len(gf)} gap(s) aparado(s) (-{sum(b-a for a,b in gf):.2f}s)")
        for passo in range(6):
            gs = gaps_silencio(cur)
            if not gs: break
            total = dur(cur)
            cortes = [(s + 0.12, min(e - 0.05, total)) for s, e in gs if min(e - 0.05, total) > s + 0.12]
            if not cortes: break
            nxt = base + f"_g{passo}.mp4"; cortar_intervalos(cur, nxt, cortes); cur = nxt
            print(f"  silêncio: {len(cortes)} gap(s) aparado(s) (-{sum(b-a for a,b in cortes):.2f}s)")
        sobra = gaps_silencio(cur)
        if sobra: print(f"  ⚠️ ainda há {len(sobra)} silêncio(s) >0,3s a -25dB em {os.path.basename(cur)} — ouça: {[(round(a,1),round(b,1)) for a,b in sobra[:4]]}")
    except Exception as ex:
        print(f"  ⚠️ aparar falhou ({str(ex)[:120]}) — seguindo com o concat sem aparar")
    return cur

def ass_time(t): return f"{int(t//3600)}:{int(t%3600//60):02d}:{t%60:05.2f}"
ASS_HDR = ("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nWrapStyle: 1\n\n[V4+ Styles]\n"
  "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
  "Style: Default,Arial,58,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,560,1\n\n[Events]\n"
  "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")

alvo = sys.argv[1:]
specs = [s for s in sorted(glob.glob(os.path.join(LEVA, "specs", "*.json"))) if not s.endswith(".state.json")]
if not specs: sys.exit(f"nenhum spec em {LEVA}/specs/")
if not os.environ.get("SEM_LEGENDA") and not tem_libass():
    sys.exit("❌ o ffmpeg em uso não tem libass (legenda queimada). Instale um ffmpeg com libass (brew install ffmpeg / apt install ffmpeg) "
             "ou aponte FFMPEG=/caminho/ffmpeg-com-libass, ou rode com SEM_LEGENDA=1.")
if not WHISPER: print("⚠️  whisper não encontrado (WHISPER_MODEL=…): trim e timing da legenda ficam por duração fixa")

feitos, pulados = [], []
for idx, sp in enumerate(specs):
    spec = json.load(open(sp))
    for item in spec["itens"]:
        ad = item["id"]
        if alvo and ad not in alvo: continue
        lang = item.get("idioma", "pt")
        final = os.path.join(FIN, f"{ad}.mp4")
        if os.path.exists(final) and integro(final): print(ad, "SKIP (já montado — apague finais/ pra refazer)"); continue
        faltam = [c["n"] for c in item["cenas"] if not (os.path.exists(os.path.join(CL, f"{ad}_{c['n']}.mp4")) and os.path.getsize(os.path.join(CL, f"{ad}_{c['n']}.mp4")) > 200000)]
        if faltam: pulados.append((ad, f"faltam clipes {faltam}")); print(ad, "FALTAM CLIPES:", faltam); continue
        try:
            mec = (item.get("gancho") or {}).get("mecanica", "").upper()
            cenas = sorted(item["cenas"], key=lambda c: float(c["n"]))          # o insert do gancho é n=0 e vem primeiro
            # 1) trim por clipe (+ punch-in no corpo)
            segs, trimados = [], {}
            for c in cenas:
                cid = f'{ad}_{c["n"]}'; raw = os.path.join(CL, f"{cid}.mp4"); t = os.path.join(WK, f"{cid}.mp4")
                if not os.path.exists(t):
                    total = dur(raw); ini, fim = fala_ini_fim(raw, lang) if c.get("fala") else (None, None)
                    cabeca = 0.0
                    if gate.get(cid, {}).get("verdict") == "FAIL_INICIO" and ini and ini > 0.35:
                        cabeca = max(0.0, ini - 0.15); print(f"  {cid}: cortando {cabeca:.2f}s de lixo na cabeça")
                    corte = overrides.get(cid) or max(2.2, min(total, (fim or total - 0.5) + 0.22))
                    cmd = ["ffmpeg","-loglevel","error","-y"] + (["-ss", f"{cabeca:.2f}"] if cabeca else []) + ["-i", raw]
                    if corte < total - 0.05: cmd += ["-t", f"{corte - cabeca:.2f}"]
                    run(cmd + ["-r","24","-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
                               "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-ac","2",t])
                    # punch-in: só no CORPO (gancho = clipe 1 fica inteiro; insert do gancho n=0 também), só em quem fala
                    if PUNCH_IN and float(c["n"]) >= 2 and c.get("fala") and punch_in(t): print(f"  {cid}: punch-in")
                trimados[float(c["n"])] = t
            # 1b) gancho por mecânica (doc 07): monta o clipe 1 final a partir do clipe 1 (pessoa) e do clipe 0 (insert)
            if mec in ("SPLIT", "INSERT_PRIMEIRO") and 0.0 in trimados and 1.0 in trimados:
                g = os.path.join(WK, f"{ad}_gancho.mp4")
                if not os.path.exists(g):
                    (gancho_split if mec == "SPLIT" else gancho_insert_primeiro)(*((trimados[1.0], trimados[0.0]) if mec == "SPLIT" else (trimados[0.0], trimados[1.0])), g)
                    print(f"  gancho {mec} montado")
                segs = [g] + [trimados[k] for k in sorted(trimados) if k >= 2]
            else:
                if mec in ("SPLIT", "INSERT_PRIMEIRO"): print(f"  ⚠️ {ad}: gancho {mec} mas falta o clipe 0 ou 1 — montando em sequência")
                segs = [trimados[k] for k in sorted(trimados)]
            # 2) concat por filtro
            cat = os.path.join(WK, f"{ad}_cat.mp4"); n = len(segs)
            fc = "".join(f"[{i}:v]fps=24,scale=1080:1920,setsar=1,format=yuv420p[v{i}];[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}];" for i in range(n))
            fc += "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
            run(["ffmpeg","-loglevel","error","-y"] + sum([["-i", s] for s in segs], []) +
                ["-filter_complex", fc, "-map","[v]","-map","[a]","-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac",cat])
            # 2b) corte por fala + silêncio (a fluidez das VSLs) — antes da legenda, então nada precisa ser deslocado
            if APARAR: cat = aparar(cat, lang, os.path.join(WK, f"{ad}_cat"))
            D = dur(cat)
            dv, da = stream_dur(cat, "v:0"), stream_dur(cat, "a:0")
            if dv and da and abs(dv - da) > 1.5: print(f"  ⚠️ {ad}: vídeo ({dv:.1f}s) e áudio ({da:.1f}s) divergem {abs(dv-da):.1f}s (>1,5s)")
            if D < MIN_DUR: print(f"  ⚠️ {ad}: {D:.0f}s < {MIN_DUR:.0f}s (MIN_DUR) — cheque trims/roteiro antes de subir")
            # 3) legendas (texto do ROTEIRO)
            ass = None
            if not os.environ.get("SEM_LEGENDA"):
                wav = os.path.join(WK, f"{ad}.wav")
                run(["ffmpeg","-loglevel","error","-y","-i",cat,"-ar","16000","-ac","1",wav])
                ev = alinha_legenda(whisper_srt(wav, lang), [c["fala"] for c in cenas if c.get("fala")])
                ass = os.path.join(WK, f"{ad}.ass")
                with open(ass, "w", encoding="utf-8") as f:
                    f.write(ASS_HDR)
                    for e in ev: f.write(f"Dialogue: 0,{ass_time(e['start'])},{ass_time(e['end'])},Default,,0,0,0,,{e['text']}\n")
            # 4) headline + 5) CTA — grafo de overlays montado passo a passo
            estilo = item.get("header_estilo") or B.cor_da_leva(idx)
            bg, tx = B.CORES.get(estilo, B.CORES["vermelho/branco"])
            ins, passos = [], []          # passos: (indice_do_input, "x=..:y=..[:enable=..]")
            if item.get("headline") and not os.environ.get("SEM_HEADLINE"):
                ins.append(B.faixa_png(item["headline"], bg, tx, os.path.join(WK, f"{ad}_hl.png")))
                passos.append((len(ins), "x=0:y=0"))
            if not os.environ.get("SEM_CTA"):
                cta = item.get("cta") or "TOQUE E ASSISTA"; T = max(0.0, D - 10.0)
                ins.append(B.pill_png(cta, os.path.join(WK, f"{ad}_p1.png"), 1.0));  passos.append((len(ins), f"x=(W-w)/2:y=1590:enable='gte(t,{T:.2f})*lt(mod(t,0.9),0.5)'"))
                ins.append(B.pill_png(cta, os.path.join(WK, f"{ad}_p2.png"), 1.07)); passos.append((len(ins), f"x=(W-w)/2:y=1583:enable='gte(t,{T:.2f})*gte(mod(t,0.9),0.5)'"))
                ins.append(B.seta_png(os.path.join(WK, f"{ad}_seta.png")));          passos.append((len(ins), f"x=(W-w)/2:y=1750:enable='gte(t,{T:.2f})*lt(mod(t,0.7),0.4)'"))
            cur, partes = "0:v", []
            for k, (ii, args) in enumerate(passos):
                partes.append(f"[{cur}][{ii}:v]overlay={args}[o{k}]"); cur = f"o{k}"
            crop = "crop=iw*0.94:ih*0.94,scale=1080:1920," if os.environ.get("CROP_WM") else ""
            partes.append(f"[{cur}]{crop}format=yuv420p[v]")
            fc = ";".join(partes)
            ov = os.path.join(WK, f"{ad}_ov.mp4")
            run(["ffmpeg","-loglevel","error","-y","-i",cat] + sum([["-i", i] for i in ins], []) +
                ["-filter_complex", fc, "-map","[v]","-map","0:a","-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",ov])
            # 6) legendas queimadas → final
            if ass:
                run([FF,"-y","-loglevel","error","-i",ov,"-vf",f"ass={filter_path(ass)}","-c:a","copy","-c:v","libx264","-pix_fmt","yuv420p",final])
            else:
                run(["ffmpeg","-y","-loglevel","error","-i",ov,"-c","copy",final])
            # 8) integridade
            if not integro(final): raise RuntimeError("final sem moov atom / ilegível (montagem morreu no meio)")
            print(f"{ad} FINAL {dur(final):.1f}s ✅  → {final}")
            feitos.append(ad)
        except Exception as ex:
            pulados.append((ad, str(ex)[:200])); print(f"{ad} ERRO: {str(ex)[:300]}")

print(f"\nMONTAGEM: {len(feitos)} prontos {feitos}")
for ad, m in pulados: print(f"  pendente {ad}: {m}")
# varredura final anti-corrupção (lei: montagem morta por timeout deixa MP4 de tamanho normal sem moov)
for f in sorted(glob.glob(os.path.join(FIN, "*.mp4"))):
    if not integro(f): print("CORROMPIDO:", f)
