# -*- coding: utf-8 -*-
# montar_vsl.py — MONTAGEM DE VSL DE REFERÊNCIA que EXECUTA O PLANO DE EDIÇÃO (02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md §4).
#
# Antes desta versão o pacote dizia "a orquestração da montagem você escreve" — e o Claude de um dono escreveu a
# orquestração MÍNIMA (concatenar clipes): 5 minutos de expert parada. Este script é o mínimo que passa a valer:
# ele lê o plano (JSON) e aplica, na ordem do doc 05:
#   0. normaliza cada clipe (1080x1920/24fps/aac 48k) + trim por whisper (fim da última palavra + 0,25s)
#   1. PUNCH-IN automático em todo plano falado > 4,6s que não recebeu outro efeito (zoom fixo 1,12 na 2ª metade)
#   2. efeitos por cena, declarados no plano:
#        cutaway  {"tipo":"cutaway","src":"broll/b03.mp4"}                → B-roll cobre o início do clipe falado (X=min(5,2, max(2,0, dur−2,4))), crossfade 0,20 nas pontas, áudio da fala inteiro
#        insert   {"tipo":"insert","png":"inserts/estudo.png","dur":5}   → still → ken burns PIL 5s → entra como cutaway
#        par      {"tipo":"par","antes":"a.png","depois":"d.png"}          → slide 5s (2,2 → wipeleft 0,8 → 2,0), mudo, como cutaway
#        flash    {"tipo":"flash","png":"antes.png","t":0.0,"dur":0.8}    → foto full-screen 0,8s dentro do clipe (t = onde entra), áudio intocado
#        split    {"tipo":"split","broll":["b1.mp4","b2.mp4"]}            → B-roll topo 40% + divisor 6px + expert 60%, B-roll em loop, áudio da expert
#        rvm      {"tipo":"rvm","bg":"inserts/estudo.png"}                → expert recortada (RobustVideoMatting → verde → chromakey) MENOR, no canto direito, sobre a prova com zoom lento
#        zoom     {"tipo":"zoom","z0":1.0,"z1":1.06}                       → zoom in/out lento sobre o clipe (supersample 2x, zoompan d=1) — só nas cenas cheias da intro
#   3. concat por filtro (nunca demuxer) + xfade 0,25s onde o plano marca "xfade": true na cena (transição de bloco)
#   4. legendas ASS (Arial 66 amarela, MarginV 220) com o TEXTO DO ROTEIRO e o TIMING do whisper (legendas_ass.py)
#   5. overlays PNG com enable='between(t,a,b)' (preço/nome/bônus/CTA)
#   6. QA objetivo: silêncio (-37dB, >1,0s), v×a ≤ 1,5s, e o gate de ritmo (scripts/medir_ritmo.py)
#
# Uso:  python3 02-VSL/scripts-referencia/montar_vsl.py vsls/VSL-X.plano-edicao.json [saida.mp4]
#       (rode na pasta da VSL; caminhos do plano são relativos a ela)
# Env:  WHISPER_MODEL=~/whisper/ggml-base.bin · FFMPEG=/caminho/ffmpeg-com-libass · RVM_DIR=~/RobustVideoMatting (só pra "rvm")
#       PUNCH_IN=0 desliga o punch-in · SEM_LEGENDA=1 · SEM_QA=1
# Requisitos: ffmpeg/ffprobe (libass pra legenda), whisper-cli, python3 + Pillow. RVM só se o plano usar "rvm".
#
# Formato do plano — ver exemplo-plano-edicao.json ao lado. Idempotente: work/ guarda cada etapa; apague work/ pra refazer tudo.
import json, os, re, sys, glob, subprocess, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kenburns as KB
import legendas_ass as LA

W, H, FPS = 1080, 1920, 24
PUNCH_MIN, PUNCH_Z = 4.6, 1.12
CUT_MAX, CUT_MIN_REST, XC = 5.2, 2.4, 0.20

from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from flow_platform import filter_path
FF = os.environ.get("FFMPEG", "ffmpeg")
PUNCH_IN = os.environ.get("PUNCH_IN", "1") != "0"

def acha_whisper():
    for p in [os.environ.get("WHISPER_MODEL")] + [os.path.expanduser(x) for x in ("~/whisper/ggml-base.bin", "~/tools/whisper/ggml-base.bin", "./tools/whisper/ggml-base.bin", "~/whisper/ggml-small.bin", "~/whisper.cpp/models/ggml-base.bin")]:
        if p and os.path.exists(p): return p
WHISPER = acha_whisper()

def run(c):
    r = subprocess.run(c, capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(" ".join(str(x) for x in c[:5]) + " :: " + r.stderr[-700:])
def dur(p, sel=None):
    c = ["ffprobe","-v","error"] + (["-select_streams", sel] if sel else []) + ["-show_entries", "stream=duration" if sel else "format=duration", "-of","csv=p=0", p]
    o = subprocess.run(c, capture_output=True, text=True).stdout.strip().split("\n")[0]
    try: return float(o or 0)
    except ValueError: return 0.0
def dims(p):
    o = subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",p],capture_output=True,text=True).stdout.strip()
    w, h = o.split(",")[:2]; return int(w), int(h)
FIT = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"

def whisper_blocks(wav, lang):
    if not WHISPER: return []
    subprocess.run(["whisper-cli","-m",WHISPER,"-l",lang,"-osrt","-of",wav[:-4],"-f",wav],capture_output=True)
    return LA.parse_srt(wav[:-4] + ".srt") if os.path.exists(wav[:-4] + ".srt") else []

# ── 0. normalizar + trim ─────────────────────────────────────────────────────────
def normalizar_trim(src, out, lang, tem_fala, pad=0.25):
    if os.path.exists(out): return out
    total = dur(src); corte = None
    if tem_fala and WHISPER:
        wav = out[:-4] + ".w.wav"
        subprocess.run(["ffmpeg","-loglevel","error","-y","-i",src,"-ar","16000","-ac","1",wav],capture_output=True)
        b = whisper_blocks(wav, lang)
        if b: corte = min(total, b[-1]["end"] + pad)
    cmd = ["ffmpeg","-loglevel","error","-y","-i",src]
    if corte and corte < total - 0.05: cmd += ["-t", f"{corte:.2f}"]
    run(cmd + ["-vf", FIT, "-r", str(FPS), "-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-ar","48000","-ac","2", out])
    return out

# ── 1. punch-in ─────────────────────────────────────────────────────────────────
def punch_in(path, z=PUNCH_Z):
    d = dur(path)
    if d < PUNCH_MIN: return False
    mid = d / 2; cw, ch = int(W/z//2*2), int(H/z//2*2)
    tmp = path[:-4] + ".punch.mp4"
    fc = (f"[0:v]trim=0:{mid:.2f},setpts=PTS-STARTPTS[a];"
          f"[0:v]trim={mid:.2f},setpts=PTS-STARTPTS,crop={cw}:{ch}:(iw-{cw})/2:(ih-{ch})*0.30,scale={W}:{H},setsar=1[b];"
          f"[a][b]concat=n=2:v=1:a=0,format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-i",path,"-filter_complex",fc,"-map","[v]","-map","0:a","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",tmp])
    os.replace(tmp, path); return True

# ── 2. efeitos ─────────────────────────────────────────────────────────────────
def cutaway(src_visual, alvo, out, slide_dur=None):
    """B-roll/insert/par cobre o INÍCIO do clipe falado com crossfade nas duas pontas; o áudio da fala é o do clipe inteiro."""
    da = dur(alvo)
    X = min(slide_dur or CUT_MAX, max(2.0, da - CUT_MIN_REST))
    if X + XC >= da: X = max(1.0, da - CUT_MIN_REST)
    HEAD = 0.30
    fc = (f"[1:v]trim=0:{HEAD:.2f},setpts=PTS-STARTPTS,{FIT}[hv];"
          f"[0:v]trim=0:{X+XC:.2f},setpts=PTS-STARTPTS,{FIT}[bv];"
          f"[1:v]trim={X:.2f},setpts=PTS-STARTPTS,{FIT}[av];"
          f"[hv][bv]xfade=transition=fade:duration={XC}:offset={HEAD-XC:.2f}[hb];"
          f"[hb][av]xfade=transition=fade:duration={XC}:offset={X:.2f},format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-stream_loop","-1","-i",src_visual,"-i",alvo,"-filter_complex",fc,"-map","[v]","-map","1:a","-t",f"{da:.2f}","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",out])
    return out

def insert_kb(png, out, secs=5.0):
    if not os.path.exists(out): KB.ken_burns(png, out, secs, W, H, 1.0, 1.14, FPS)
    return out

def slide_par(a_png, b_png, out):
    if os.path.exists(out): return out
    fit = f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},setsar=1,fps={FPS}"
    fc = f"[0:v]{fit}[v0];[1:v]{fit}[v1];[v0][v1]xfade=transition=wipeleft:duration=0.8:offset=2.2,format=yuv420p[v]"
    run(["ffmpeg","-loglevel","error","-y","-loop","1","-t","3","-i",a_png,"-loop","1","-t","2.8","-i",b_png,"-filter_complex",fc,"-map","[v]","-t","5","-an","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p",out])
    return out

def flash(alvo, png, out, t=0.0, d=0.8):
    """foto full-screen por d segundos dentro do clipe falado, a partir de t; áudio intocado."""
    fc = (f"[1:v]{FIT}[f];[0:v][f]overlay=enable='between(t,{t:.2f},{t+d:.2f})',format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-i",alvo,"-loop","1","-i",png,"-filter_complex",fc,"-map","[v]","-map","0:a","-shortest","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",out])
    return out

def split(alvo, brolls, out, top_h=768, div=6):
    """B-roll topo 40% + divisor branco + expert embaixo 60%; B-roll em loop pela duração da fala; áudio da expert."""
    da = dur(alvo); bot_h = H - top_h - div
    lst = out[:-4] + ".txt"
    with open(lst, "w") as f:
        for _ in range(8):
            for b in brolls: f.write(f"file '{os.path.abspath(b).replace(chr(92), '/')}'\n")
    fc = (f"[0:v]fps={FPS},scale={W}:-2,crop={W}:{top_h}:0:(ih-{top_h})*0.45,setsar=1[top];"
          f"[1:v]fps={FPS},scale=-2:{int(H*1.18)},crop={W}:{bot_h}:(iw-{W})/2:(ih-{bot_h})*0.18,setsar=1[bot];"
          f"color=white:s={W}x{div}:d={da:.2f}:r={FPS}[dv];[top][dv]vstack=2[tv];[tv][bot]vstack=2,format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-f","concat","-safe","0","-i",lst,"-i",alvo,"-filter_complex",fc,"-map","[v]","-map","1:a","-t",f"{da:.2f}","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",out])
    return out

def rvm(alvo, bg_png, out):
    """expert recortada MENOR no canto direito sobre a prova (prova visível inteira) — RVM_DIR obrigatório."""
    green = out[:-4] + ".green.mp4"
    if not os.path.exists(green):
        rvm_dir = os.environ.get("RVM_DIR")
        if not rvm_dir: raise RuntimeError("efeito rvm pede RVM_DIR=~/RobustVideoMatting (doc 04a)")
        run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), "rvm_matte.py"), alvo, green])
    da = dur(alvo); frames = int(da * FPS) + FPS
    fc = (f"[0:v]scale={W*2}:-2,zoompan=z='min(1.0+0.0004*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/6-(ih/zoom/6)':d={frames}:s={W}x{H}:fps={FPS}[bg];"
          f"[1:v]chromakey=0x00ff00:0.24:0.08,despill=type=green,scale=490:-2[fg];"
          f"[bg][fg]overlay=x=W-w-6:y=H-h:shortest=1,format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-loop","1","-t",f"{da:.2f}","-i",bg_png,"-i",green,"-filter_complex",fc,"-map","[v]","-map","1:a","-t",f"{da:.2f}","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",out])
    return out

def zoom_lento(alvo, out, z0=1.0, z1=1.06):
    """zoom in/out sobre VÍDEO: supersample 2x + zoompan d=1 (1 frame de saída por frame de entrada). Áudio intocado."""
    n = max(2, int(dur(alvo) * FPS))
    fc = (f"[0:v]scale={W*2}:-2,zoompan=z='{z0}+({z1}-{z0})*on/{n}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d=1:s={W}x{H}:fps={FPS},format=yuv420p[v]")
    run(["ffmpeg","-loglevel","error","-y","-i",alvo,"-filter_complex",fc,"-map","[v]","-map","0:a","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",out])
    return out

# ── main ────────────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 2: sys.exit("uso: python3 montar_vsl.py plano-edicao.json [saida.mp4]")
    plano = json.load(open(sys.argv[1]))
    saida = sys.argv[2] if len(sys.argv) > 2 else plano.get("saida", "VSL_final.mp4")
    lang = plano.get("idioma", "pt")
    WK = plano.get("work", "work"); os.makedirs(WK, exist_ok=True)
    cenas = sorted(plano["cenas"], key=lambda c: float(c["n"]))
    if not WHISPER: print("⚠️  whisper não encontrado (WHISPER_MODEL=…): sem trim por fala e legenda com timing por duração")
    segs, falas, cortadas = [], [], set(plano.get("cortadas", []))
    n_efeitos, n_punch = 0, 0
    for c in cenas:
        n = c["n"]
        if n in cortadas: continue
        base = os.path.join(WK, f"cena_{n}.mp4")
        normalizar_trim(c["clip"], base, lang, bool(c.get("fala")))
        cur = base
        efeitos = c.get("efeitos") or []
        cobre = False    # algum efeito já deu estímulo? então sem punch-in
        for k, e in enumerate(efeitos):
            t = e["tipo"]; out = os.path.join(WK, f"cena_{n}_e{k}_{t}.mp4")
            if not os.path.exists(out):
                if t == "cutaway": cutaway(e["src"], cur, out, e.get("dur"))
                elif t == "insert": cutaway(insert_kb(e["png"], os.path.join(WK, f"ins_{n}_{k}.mp4"), e.get("dur", 5.0)), cur, out, e.get("dur", 5.0))
                elif t == "par": cutaway(slide_par(e["antes"], e["depois"], os.path.join(WK, f"par_{n}_{k}.mp4")), cur, out, 5.0)
                elif t == "flash": flash(cur, e["png"], out, e.get("t", 0.0), e.get("dur", 0.8))
                elif t == "split": split(cur, e["broll"] if isinstance(e["broll"], list) else [e["broll"]], out)
                elif t == "rvm": rvm(cur, e["bg"], out)
                elif t == "zoom": zoom_lento(cur, out, e.get("z0", 1.0), e.get("z1", 1.06))
                else: raise RuntimeError(f"cena {n}: efeito desconhecido '{t}'")
                print(f"  cena {n}: {t}")
            cur = out; n_efeitos += 1
            if t in ("cutaway", "insert", "par", "split", "rvm", "zoom"): cobre = True
        if PUNCH_IN and c.get("fala") and not cobre and not c.get("sem_punch"):
            fin = os.path.join(WK, f"cena_{n}_p.mp4")
            if not os.path.exists(fin):
                run(["ffmpeg","-loglevel","error","-y","-i",cur,"-c","copy",fin])
                if punch_in(fin): print(f"  cena {n}: punch-in")
            cur = fin
            n_punch += 1
        segs.append((cur, bool(c.get("xfade"))))
        if c.get("fala"): falas.append(c["fala"])
    if not segs: sys.exit("nenhuma cena")
    # 3. concat por filtro (+ xfade 0,25 onde marcado)
    cat = os.path.join(WK, "cat.mp4"); n = len(segs)
    ins = sum([["-i", s] for s, _ in segs], [])
    fc = "".join(f"[{i}:v]fps={FPS},scale={W}:{H},setsar=1,format=yuv420p,settb=AVTB[v{i}];[{i}:a]aresample=48000,aformat=channel_layouts=stereo[a{i}];" for i in range(n))
    if not any(x for _, x in segs):
        fc += "".join(f"[v{i}][a{i}]" for i in range(n)) + f"concat=n={n}:v=1:a=1[v][a]"
    else:   # xfade só nas fronteiras marcadas; o resto concat seco. Implementação simples: acumula par a par.
        vcur, acur, tcur = "v0", "a0", dur(segs[0][0])
        for i in range(1, n):
            di = dur(segs[i][0])
            if segs[i][1]:
                off = max(0.0, tcur - 0.25)
                fc += f"[{vcur}][v{i}]xfade=transition=fade:duration=0.25:offset={off:.3f},settb=AVTB[vx{i}];[{acur}][a{i}]acrossfade=d=0.25[ax{i}];"
                tcur = off + di
            else:
                fc += f"[{vcur}][{acur}][v{i}][a{i}]concat=n=2:v=1:a=1[vx{i}][ax{i}];"
                tcur += di
            vcur, acur = f"vx{i}", f"ax{i}"
        fc += f"[{vcur}]format=yuv420p[v];[{acur}]anull[a]"
    run(["ffmpeg","-loglevel","error","-y"] + ins + ["-filter_complex", fc, "-map","[v]","-map","[a]","-r",str(FPS),"-c:v","libx264","-pix_fmt","yuv420p","-c:a","aac","-ar","48000",cat])
    D = dur(cat); print(f"concat: {D:.1f}s · {len(segs)} cenas · {n_efeitos} efeitos · {n_punch} punch-ins")
    # 4. legendas
    cur = cat
    if not os.environ.get("SEM_LEGENDA") and falas:
        wav = os.path.join(WK, "final.wav"); run(["ffmpeg","-loglevel","error","-y","-i",cat,"-ar","16000","-ac","1",wav])
        b = whisper_blocks(wav, lang)
        if b:
            ass = os.path.join(WK, "legendas.ass"); LA.write_ass(LA.chunk_events(b, " ".join(falas)), ass, "916")
            leg = os.path.join(WK, "cat_leg.mp4")
            run([FF,"-loglevel","error","-y","-i",cat,"-vf",f"ass={filter_path(ass)}","-c:a","copy","-c:v","libx264","-pix_fmt","yuv420p",leg]); cur = leg
        else: print("⚠️  sem whisper — legenda pulada")
    # 5. overlays
    ovs = plano.get("overlays") or []
    if ovs:
        parts, cur_lbl = [], "0:v"
        for k, o in enumerate(ovs):
            parts.append(f"[{cur_lbl}][{k+1}:v]overlay=x={o.get('x','(W-w)/2')}:y={o.get('y',1120)}:enable='between(t,{o['ini']},{o['fim']})'[o{k}]"); cur_lbl = f"o{k}"
        parts.append(f"[{cur_lbl}]format=yuv420p[v]")
        ovf = os.path.join(WK, "cat_ov.mp4")
        run(["ffmpeg","-loglevel","error","-y","-i",cur] + sum([["-i", o["png"]] for o in ovs], []) + ["-filter_complex", ";".join(parts), "-map","[v]","-map","0:a","-c:v","libx264","-pix_fmt","yuv420p","-c:a","copy",ovf]); cur = ovf
    run(["ffmpeg","-loglevel","error","-y","-i",cur,"-c","copy",saida])
    print(f"FINAL {dur(saida):.1f}s → {saida}")
    # 6. QA objetivo
    if not os.environ.get("SEM_QA"):
        r = subprocess.run(["ffmpeg","-i",saida,"-af","silencedetect=noise=-37dB:d=1.0","-f","null","-"],capture_output=True,text=True)
        sil = re.findall(r"silence_start: ([\d.]+)", r.stderr)
        dv, da = dur(saida, "v:0"), dur(saida, "a:0")
        print(f"QA: silêncios >1s: {len(sil)} {sil[:5]} · vídeo {dv:.1f}s × áudio {da:.1f}s (diff {abs(dv-da):.2f}s)")
        if sil or abs(dv - da) > 1.5: print("🔴 REPROVADO no QA objetivo — corrija antes de mostrar")
        mr = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scripts", "medir_ritmo.py")
        if os.path.exists(mr): subprocess.run([sys.executable, mr, saida], env={**os.environ, "MODO": "vsl"})

if __name__ == "__main__":
    main()
