# legendas_ass.py — legendas queimadas no padrão validado (público 45+, blocos de 3-4 palavras).
#
# O método (doc 05):
#   1. whisper-cli transcreve o ÁUDIO FINAL da VSL com timestamps (modelo base serve pra legenda;
#      QA de fala usa o small — o base mente em texto fino).
#   2. As palavras do whisper são alinhadas com as palavras do ROTEIRO via difflib.SequenceMatcher:
#      a GRAFIA oficial vem do roteiro, o TEMPO vem do whisper — melhor dos dois mundos.
#   3. Os eventos saem em blocos de 3-4 palavras (nunca frase inteira) e viram um .ass.
#   4. ffmpeg com libass queima: ffmpeg -i final.mp4 -vf "ass=legendas.ass" ... (se o seu ffmpeg
#      veio sem libass, use um build estático com libass só pra queima).
#
# Estilos validados:
#   9:16 (1080x1920): Arial 66, outline 3, MarginV 220, AMARELA  -> write_ass(eventos, out, "916")
#   3:4  (1080x1440): Arial 54, outline 3, MarginV 104           -> write_ass(eventos, out, "34")

import re

HEADERS = {
    "916": """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,66,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,30,30,220,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""",
    "34": """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1440
WrapStyle: 1

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,54,&H0000FFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,3,1,2,24,24,104,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
""",
}
# Nota: &H0000FFFF em ASS = AMARELO (formato &HAABBGGRR). Pra branco, use &H00FFFFFF.


def parse_srt(path):
    """Lê o .srt do whisper -> [{'start': s, 'end': s, 'text': str}, ...]"""
    blocks = []
    content = open(path, encoding="utf-8").read().strip()
    for block in content.split("\n\n"):
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue
        m = re.match(r"(\d+):(\d+):(\d+)[.,](\d+)\s*-->\s*(\d+):(\d+):(\d+)[.,](\d+)", lines[1])
        if not m:
            continue
        h1, m1, s1, ms1, h2, m2, s2, ms2 = map(int, m.groups())
        blocks.append({
            "start": h1 * 3600 + m1 * 60 + s1 + ms1 / 1000.0,
            "end": h2 * 3600 + m2 * 60 + s2 + ms2 / 1000.0,
            "text": " ".join(lines[2:]),
        })
    return blocks


def chunk_events(srt_blocks, roteiro_texto, max_palavras=4):
    """Alinha whisper x roteiro e devolve eventos de 3-4 palavras com a grafia do ROTEIRO."""
    import difflib

    # palavras do whisper com tempo estimado (duração do bloco rateada por tamanho da palavra)
    wwords = []
    for b in srt_blocks:
        ws = b["text"].split()
        if not ws:
            continue
        total = sum(len(w) for w in ws)
        t = b["start"]
        for w in ws:
            d = (len(w) / total) * (b["end"] - b["start"]) if total else 0
            wwords.append({"word": w, "start": t, "end": t + d})
            t += d

    mwords = roteiro_texto.split()
    times = [{"word": w, "start": 0.0, "end": 0.0} for w in mwords]
    sm = difflib.SequenceMatcher(None,
                                 [w["word"].lower().strip(".,!?") for w in wwords],
                                 [w.lower().strip(".,!?") for w in mwords])
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if op in ("equal", "replace") and i2 > i1 and j2 > j1:
            t0, t1 = wwords[i1]["start"], wwords[i2 - 1]["end"]
            span = (t1 - t0) / (j2 - j1)
            for k, j in enumerate(range(j1, j2)):
                times[j]["start"] = t0 + k * span
                times[j]["end"] = t0 + (k + 1) * span

    # blocos de até max_palavras
    events = []
    for i in range(0, len(times), max_palavras):
        grp = [t for t in times[i:i + max_palavras] if t["end"] > 0]
        if not grp:
            continue
        events.append({"start": grp[0]["start"], "end": grp[-1]["end"],
                       "text": " ".join(t["word"] for t in grp)})
    return events


def _ts(t):
    h = int(t // 3600); m = int(t % 3600 // 60); s = t % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def write_ass(events, out_path, canvas="916"):
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(HEADERS[canvas])
        for e in events:
            f.write(f"Dialogue: 0,{_ts(e['start'])},{_ts(e['end'])},Default,,0,0,0,,{e['text']}\n")
    return out_path


if __name__ == "__main__":
    import sys
    # uso: python3 legendas_ass.py final.wav.srt roteiro_texto.txt legendas.ass [916|34]
    srt, rot, out = sys.argv[1], sys.argv[2], sys.argv[3]
    canvas = sys.argv[4] if len(sys.argv) > 4 else "916"
    evs = chunk_events(parse_srt(srt), open(rot, encoding="utf-8").read())
    write_ass(evs, out, canvas)
    print(f"{len(evs)} eventos -> {out}")
