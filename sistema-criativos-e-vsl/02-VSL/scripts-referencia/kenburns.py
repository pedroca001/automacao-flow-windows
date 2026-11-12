# kenburns.py — Ken Burns SEM TREMOR: frames renderizados no PIL com janela em coordenadas FLOAT.
#
# POR QUÊ: o zoompan do ffmpeg move a janela de crop em PIXEL INTEIRO — em zoom lento isso
# vira um tremor visível (reprovado repetidamente em produção real). O PIL aceita box float
# no resize (sub-pixel real) + resample Lanczos => movimento liso.
# Zoom LINEAR de propósito: velocidade constante, sem "pulso" de easing.
#
# Se você PRECISAR de zoompan (ex.: zoom sobre vídeo): supersample 6x antes
# (scale=W*6:-2) + zoom lento. 2x ainda treme; 6x fica liso.
#
# Uso típico (insert de print/página editorial virando clipe de 5s):
#   from kenburns import ken_burns, ken_burns_seq
#   ken_burns("print_estudo.png", "insert_10.mp4", secs=5.0)
#   ken_burns_seq(["tela1.png","tela2.png","tela3.png"], "app_tour.mp4", secs=8.0)
#
# Lembrete do doc 04: arte com TEXTO que recebe ken burns precisa de ~78px de margem
# interna (safe area), senão o movimento come header/rodapé.

import os
import subprocess
import tempfile

from PIL import Image


def ken_burns(img_path, out_mp4, secs, W=1080, H=1920, z0=1.0, z1=1.14, fps=24,
              anchor=(0.5, 0.42), pan=(0.0, 0.0)):
    """anchor = centro do zoom em fração da imagem; pan = deslocamento total (frações) ao longo do clipe."""
    src = Image.open(img_path).convert("RGB")
    # cobre o canvas (equivalente a force_original_aspect_ratio=increase + crop central)
    sw, sh = src.size
    esc = max(W / sw, H / sh)
    base = src.resize((max(W, int(sw * esc + 0.5)), max(H, int(sh * esc + 0.5))), Image.LANCZOS)
    bw, bh = base.size
    n = max(2, int(secs * fps))
    tmp = tempfile.mkdtemp(prefix="kb_")
    for i in range(n):
        p = i / (n - 1)
        z = z0 + (z1 - z0) * p            # linear = velocidade constante
        cw, ch = W / z, H / z             # janela em FLOAT — o segredo do movimento liso
        cx = bw * (anchor[0] + pan[0] * p)
        cy = bh * (anchor[1] + pan[1] * p)
        x0 = min(max(cx - cw / 2, 0.0), bw - cw)
        y0 = min(max(cy - ch / 2, 0.0), bh - ch)
        frame = base.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch))
        frame.save(f"{tmp}/f{i:05d}.png", compress_level=1)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-framerate", str(fps),
                    "-i", f"{tmp}/f%05d.png",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-r", str(fps), out_mp4],
                   check=True)
    for f in os.listdir(tmp):
        os.remove(f"{tmp}/{f}")
    os.rmdir(tmp)
    return out_mp4


def ken_burns_seq(imgs, out_mp4, secs, W=1080, H=1920, fps=24, xfade=0.4):
    """Slideshow: ken burns em cada imagem + crossfade entre elas (direções de zoom alternadas)."""
    per = (secs + xfade * (len(imgs) - 1)) / len(imgs)
    parts = []
    tmp = tempfile.mkdtemp(prefix="kbs_")
    zs = [(1.0, 1.13), (1.12, 1.0), (1.0, 1.15)]  # alterna in/out — cada imagem respira diferente
    for i, im in enumerate(imgs):
        z0, z1 = zs[i % len(zs)]
        p = f"{tmp}/p{i}.mp4"
        ken_burns(im, p, per, W, H, z0, z1, fps)
        parts.append(p)
    cur = parts[0]
    t = per
    for i, nxt in enumerate(parts[1:], 1):
        out = f"{tmp}/acc{i}.mp4"
        off = t - xfade
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", cur, "-i", nxt,
                        "-filter_complex",
                        f"[0:v][1:v]xfade=transition=fade:duration={xfade}:offset={off:.3f},format=yuv420p[v]",
                        "-map", "[v]", "-r", str(fps), "-c:v", "libx264", "-pix_fmt", "yuv420p", out],
                       check=True)
        cur = out
        t = off + per
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", cur, "-t", f"{secs:.2f}",
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", out_mp4], check=True)
    return out_mp4
