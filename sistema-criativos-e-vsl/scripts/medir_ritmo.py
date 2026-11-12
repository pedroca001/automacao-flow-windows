# -*- coding: utf-8 -*-
# medir_ritmo.py — o GATE DE RITMO medido (02-VSL/06-EDICAO-DINAMICA-OBRIGATORIA.md §6 · 01-CRIATIVOS/08-CRIATIVO-DINAMICO.md).
# "Ficou dinâmico?" não se sente — se mede. Para cada MP4:
#   • trocas de estímulo por minuto (scene detect do ffmpeg). 🔴 LIMIAR CALIBRADO = 0,05: numa VSL aprovada, com 274 trocas CONTADAS
#     à mão (punch-ins + jump cuts + crossfades + B-roll), o detector deu 270 a 0,05 — e só 102 a 0,30 (punch-in e jump cut no mesmo
#     frame-base quase não mudam pixel). Não suba o limiar "pra ser mais rigoroso": você passa a reprovar edição boa.
#   • o MAIOR plano sem corte (e onde ele está) — é o "buraco" que o espectador sente
#   • silêncios (>1,0s a -37dB em VSL · >0,3s a -25dB em criativo)
#   • vídeo × áudio terminando juntos (>1,5s de diferença = reprovado)
#   • duração
# Uso:  python3 scripts/medir_ritmo.py vsls/VSL-X_final.mp4            → modo VSL   (régua: ≥12 trocas/min, maior plano ≤12s)
#       python3 scripts/medir_ritmo.py finais/                          → todos os .mp4 da pasta, modo CRIATIVO (≥10/min, maior plano ≤9s)
#       MODO=vsl|criativo · LIMIAR=0.05 · MIN_TROCAS=12 · MAX_PLANO=12 · JSON=1 (saída em JSON)
# Régua medida em produção aprovada: VSL de 15min31 = 17,4 trocas/min, maior plano 11,3s · criativos "os melhores até hoje" = 14-16/min, maior plano 7-8s.
# A régua de DESENHO continua sendo "nenhum plano >6-8s sem estímulo" (doc 06 §1); o gate medido é um pouco mais folgado porque o detector não vê tudo.
# Sai com código 1 se algum arquivo reprovar — dá pra usar como gate num .sh.
import os, re, sys, glob, json, subprocess

def dur(p, sel=None):
    c = ["ffprobe","-v","error"] + (["-select_streams", sel] if sel else []) + ["-show_entries", ("stream=duration" if sel else "format=duration"), "-of","csv=p=0", p]
    o = subprocess.run(c, capture_output=True, text=True).stdout.strip().split("\n")[0]
    try: return float(o or 0)
    except ValueError: return 0.0

def cortes(p, limiar):
    r = subprocess.run(["ffmpeg","-i",p,"-vf",f"select='gt(scene,{limiar})',showinfo","-f","null","-"], capture_output=True, text=True)
    return [float(t) for t in re.findall(r"pts_time:([\d.]+)", r.stderr)]

def silencios(p, noise, d):
    r = subprocess.run(["ffmpeg","-i",p,"-af",f"silencedetect=noise={noise}:d={d}","-f","null","-"], capture_output=True, text=True)
    st = [float(m) for m in re.findall(r"silence_start: ([\d.]+)", r.stderr)]
    en = [float(m) for m in re.findall(r"silence_end: ([\d.]+)", r.stderr)]
    return [(s, en[i] if i < len(en) else None) for i, s in enumerate(st)]

def medir(p, modo, limiar, min_trocas, max_plano):
    D = dur(p); dv, da = dur(p, "v:0"), dur(p, "a:0")
    ts = cortes(p, limiar)
    pontos = [0.0] + ts + [D]
    planos = [(pontos[i+1] - pontos[i], pontos[i]) for i in range(len(pontos) - 1)]
    maior = max(planos) if planos else (D, 0.0)
    por_min = len(ts) / (D / 60) if D else 0
    noise, d = ("-37dB", 1.0) if modo == "vsl" else ("-25dB", 0.3)
    sil = silencios(p, noise, d)
    av = abs(dv - da) if dv and da else 0.0
    motivos = []
    if por_min < min_trocas: motivos.append(f"só {por_min:.1f} trocas/min (mínimo {min_trocas})")
    if maior[0] > max_plano: motivos.append(f"maior plano sem corte = {maior[0]:.1f}s em {maior[1]:.0f}s (máximo {max_plano}s)")
    if sil: motivos.append(f"{len(sil)} silêncio(s) >{d}s a {noise} (1º em {sil[0][0]:.1f}s)")
    if av > 1.5: motivos.append(f"vídeo ({dv:.1f}s) e áudio ({da:.1f}s) divergem {av:.1f}s")
    return {"arquivo": p, "duracao": round(D, 1), "trocas": len(ts), "trocas_por_min": round(por_min, 1),
            "maior_plano_s": round(maior[0], 1), "maior_plano_em": round(maior[1], 1), "silencios": len(sil),
            "av_diff": round(av, 2), "aprovado": not motivos, "motivos": motivos,
            "planos_longos": [(round(d_, 1), round(t, 1)) for d_, t in sorted(planos, reverse=True)[:5] if d_ > max_plano]}

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("uso: python3 medir_ritmo.py <arquivo.mp4 | pasta/>   (env: MODO=vsl|criativo LIMIAR=0.05 MIN_TROCAS= MAX_PLANO= JSON=1)\n"
              "régua padrão: VSL ≥12 trocas/min e maior plano ≤12s · criativo ≥10/min e ≤9s · silêncio zero · vídeo×áudio ≤1,5s")
        sys.exit(0 if len(sys.argv) >= 2 else 1)
    alvo = sys.argv[1]
    arquivos = sorted(glob.glob(os.path.join(alvo, "*.mp4"))) if os.path.isdir(alvo) else [alvo]
    if not arquivos: sys.exit(f"nenhum .mp4 em {alvo}")
    modo = os.environ.get("MODO") or ("criativo" if os.path.isdir(alvo) else "vsl")
    limiar = float(os.environ.get("LIMIAR", "0.05"))
    min_trocas = float(os.environ.get("MIN_TROCAS", "12" if modo == "vsl" else "10"))
    max_plano = float(os.environ.get("MAX_PLANO", "12" if modo == "vsl" else "9"))
    res = [medir(p, modo, limiar, min_trocas, max_plano) for p in arquivos]
    if os.environ.get("JSON"): print(json.dumps(res, ensure_ascii=False, indent=1)); sys.exit(0 if all(r["aprovado"] for r in res) else 1)
    print(f"modo {modo} · limiar {limiar} · régua: ≥{min_trocas:g} trocas/min, maior plano ≤{max_plano:g}s\n")
    for r in res:
        v = "🟢 APROVADO" if r["aprovado"] else "🔴 REPROVADO"
        print(f"{v}  {os.path.basename(r['arquivo'])}  {r['duracao']}s · {r['trocas']} trocas ({r['trocas_por_min']}/min) · maior plano {r['maior_plano_s']}s em {r['maior_plano_em']}s · silêncios {r['silencios']} · v×a {r['av_diff']}s")
        for m in r["motivos"]: print(f"     - {m}")
        if r["planos_longos"]: print(f"     planos longos (s, onde): {r['planos_longos']}")
    n_rep = sum(1 for r in res if not r["aprovado"])
    print(f"\n{len(res) - n_rep}/{len(res)} aprovados." + ("" if not n_rep else " Reprovou = volta ao plano de edição (doc 06 §4 / doc 08 §6), não 'manda assim mesmo'."))
    sys.exit(1 if n_rep else 0)

if __name__ == "__main__":
    main()
