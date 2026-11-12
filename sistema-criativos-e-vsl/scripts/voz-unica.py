#!/usr/bin/env python3
# VOZ ÚNICA — troca a locução de um vídeo multi-cena por UMA voz só de TTS.
# (Cada clipe do gerador vem com a própria voz — vídeo de 3 cenas sai com 3 narradoras.
#  Este script gera a locução fora do gerador e substitui a faixa inteira.)
#
# 🔴 SÓ EM VÍDEO SEM ROSTO. Com avatar em quadro, trocar o áudio dessincroniza a boca.
# ⚠️ RELEGENDE DEPOIS. A legenda queimada sai da transcrição, e o áudio mudou.
#
# Uso:
#   pip install edge-tts        (TTS neural gratuito, sem chave)
#   python3 voz-unica.py --video final.mp4 --cenas cenas.json --out final-voz.mp4 \
#                        [--voz en-US-EmmaNeural]
#
# cenas.json — os MESMOS instantes de corte da montagem (em segundos, no vídeo montado):
#   [ {"texto": "fala da cena 1", "fim": 6.5},
#     {"texto": "fala da cena 2", "fim": 13.2},
#     {"texto": "fala da cena 3"} ]          ← última cena: "fim" opcional (= fim do vídeo)
#
# Leis embutidas (cada uma custou um vídeo):
#   - Escolha a voz pela VELOCIDADE natural, não pelo timbre (EmmaNeural precisa de ~+4%
#     de ajuste; outras chegam a +34% e soam apressadas). Mantenha a MESMA voz em todos
#     os vídeos da página — ela vira parte da identidade.
#   - O ajuste vai nos DOIS sentidos: acelera até +30%, DESACELERA até -18%. Só acelerar
#     deixa buraco de silêncio entre cenas (já deu 1,58s de buraco = reprovação).
#   - O silêncio das pontas do TTS sai ANTES de medir a duração, senão o cálculo mente.
#   - O que sobra de tempo vira respiro distribuído entre entrada e saída da cena.
#   - Calibre do roteiro: ~18-20 palavras por 6s de segmento. Fora disso o script avisa.
#   - 🔴 TRAVA: se os cortes não baterem com a duração do vídeo, ABORTA. O log de
#     montagem mostra o valor PEDIDO do corte, não o aplicado — copiar às cegas soma
#     mais que o vídeo e cada cena entra atrasada sem nada acusar.

import json, os, sys, argparse, subprocess, tempfile

ATEMPO_MAX = 1.30   # +30%: acima disso soa apressado → encurte o roteiro da cena
ATEMPO_MIN = 0.82   # -18%: abaixo disso arrasta → alongue o roteiro da cena
TOLERANCIA_CORTES = 0.20  # s de diferença aceita entre último corte e duração do vídeo

def sh(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"ERRO: {' '.join(cmd[:3])}...\n{r.stderr[-800:]}")
    return r

def dur(path):
    r = sh(["ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "csv=p=0", path])
    return float(r.stdout.strip())

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True)
    ap.add_argument("--cenas", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--voz", default="en-US-EmmaNeural")
    a = ap.parse_args()

    cenas = json.load(open(a.cenas))
    vdur = dur(a.video)

    # fronteiras absolutas → duração de cada segmento
    fins = [c.get("fim") for c in cenas]
    if fins[-1] is None: fins[-1] = vdur
    if None in fins: sys.exit("ERRO: só a ÚLTIMA cena pode omitir o campo 'fim'.")
    if any(fins[i] >= fins[i+1] for i in range(len(fins)-1)):
        sys.exit("ERRO: os 'fim' precisam ser crescentes.")
    # 🔴 a trava do log que mente
    if abs(fins[-1] - vdur) > TOLERANCIA_CORTES:
        sys.exit(f"ABORT: cortes somam {fins[-1]:.2f}s mas o vídeo tem {vdur:.2f}s "
                 f"(>{TOLERANCIA_CORTES}s). O log de corte mostra o valor PEDIDO, não o "
                 f"aplicado — meça os cortes reais no vídeo montado e corrija o cenas.json.")
    fins[-1] = vdur

    tmp = tempfile.mkdtemp(prefix="voz-unica-")
    seg_wavs, ini = [], 0.0
    for i, c in enumerate(cenas):
        alvo = fins[i] - ini
        palavras = len(c["texto"].split())
        # 1) TTS da cena
        mp3 = os.path.join(tmp, f"c{i}.mp3")
        sh(["edge-tts", "--voice", a.voz, "--text", c["texto"], "--write-media", mp3])
        # 2) tira o silêncio das PONTAS antes de medir (senão a medida mente)
        raw = os.path.join(tmp, f"c{i}-raw.wav")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", mp3, "-af",
            "silenceremove=start_periods=1:start_threshold=-45dB,areverse,"
            "silenceremove=start_periods=1:start_threshold=-45dB,areverse",
            "-ar", "44100", "-ac", "2", raw])
        tdur = dur(raw)
        # 3) ajuste nos DOIS sentidos, com teto e piso
        atempo = tdur / alvo
        aviso = ""
        if atempo > ATEMPO_MAX:
            atempo, aviso = ATEMPO_MAX, f"⚠️ roteiro LONGO pra cena ({palavras} palavras em {alvo:.1f}s) — corte palavras"
        elif atempo < ATEMPO_MIN:
            atempo, aviso = ATEMPO_MIN, f"⚠️ roteiro CURTO pra cena ({palavras} palavras em {alvo:.1f}s) — alongue a fala"
        ajustado = os.path.join(tmp, f"c{i}-fit.wav")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", raw,
            "-af", f"atempo={atempo:.4f}", ajustado])
        fdur = dur(ajustado)
        # 4) respiro distribuído: metade antes, metade depois; corta exato no alvo
        folga = max(0.0, alvo - fdur)
        seg = os.path.join(tmp, f"c{i}-seg.wav")
        sh(["ffmpeg", "-y", "-loglevel", "error", "-i", ajustado, "-af",
            f"adelay={int(folga/2*1000)}|{int(folga/2*1000)},apad,atrim=0:{alvo:.3f}", seg])
        seg_wavs.append(seg)
        print(f"cena {i+1}: {palavras} palavras · alvo {alvo:.2f}s · tts {tdur:.2f}s · "
              f"ajuste {'+' if atempo>=1 else ''}{(atempo-1)*100:.0f}% · respiro {folga:.2f}s  {aviso}")
        ini = fins[i]

    # 5) concat + troca da faixa (vídeo intocado)
    lista = os.path.join(tmp, "lista.txt")
    open(lista, "w", encoding="utf-8").write("".join("file '" + os.path.abspath(w).replace("\\", "/").replace("'", "'\\''") + "'\n" for w in seg_wavs))
    voz = os.path.join(tmp, "voz.wav")
    sh(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
        "-i", lista, "-c", "copy", voz])
    sh(["ffmpeg", "-y", "-loglevel", "error", "-i", a.video, "-i", voz,
        "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-shortest", a.out])
    print(f"\nOK: {a.out} ({dur(a.out):.2f}s, vídeo {vdur:.2f}s)")
    print("Lembretes: RELEGENDAR (o áudio mudou) · conferir buracos de silêncio <1,0s · "
          "só vídeo SEM ROSTO.")

if __name__ == "__main__":
    main()
