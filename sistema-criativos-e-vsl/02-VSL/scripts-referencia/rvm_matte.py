# rvm_matte.py — RobustVideoMatting: gera versão do clipe com FUNDO VERDE puro (pra chroma key no ffmpeg).
#
# Pré-requisitos (uma vez):
#   git clone https://github.com/PeterL1n/RobustVideoMatting  (defina RVM_DIR apontando pra ela)
#   baixar o peso rvm_mobilenetv3.pth pra dentro dessa pasta (link no README do repo)
#   pip install torch numpy
#
# Uso:
#   RVM_DIR=~/tools/rvm python3 rvm_matte.py <in.mp4> <out_green.mp4>
#
# Como funciona: decodifica o vídeo frame a frame via ffmpeg (rawvideo), passa cada frame
# pela rede de matting (com estado recorrente entre frames = borda estável, sem "fervilhar"),
# compõe foreground*alpha + VERDE*(1-alpha) e re-encoda mantendo o áudio original.
# Em Mac roda no MPS (GPU Apple); em PC com NVIDIA, troque 'mps' por 'cuda'. ~1min por clipe de 8s.
#
# Depois, a recomposição típica no ffmpeg (pessoa recortada MENOR no canto direito,
# fundo-prova aparecendo INTEIRO — regra do doc 04):
#   ffmpeg -y -loop 1 -t DUR -i fundo_prova.png -i out_green.mp4 -filter_complex "
#     [0:v]scale=2160:-2,zoompan=z='min(1.0+0.0004*on,1.06)':x='iw/2-(iw/zoom/2)':y='ih/6-(ih/zoom/6)':d=FRAMES:s=1080x1920:fps=24[bg];
#     [1:v]chromakey=0x00ff00:0.24:0.08,despill=type=green,scale=490:-2[fg];
#     [bg][fg]overlay=x=W-w-6:y=H-h:shortest=1,format=yuv420p[v]" \
#     -map "[v]" -map 1:a -t DUR -c:v libx264 -pix_fmt yuv420p -c:a aac cena_final.mp4

import os
import subprocess
import sys

RVM_DIR = os.path.expanduser(os.environ.get("RVM_DIR", "~/tools/rvm"))
sys.path.insert(0, RVM_DIR)

import numpy as np
import torch
from model import MattingNetwork  # do repo RobustVideoMatting

IN, OUT = sys.argv[1], sys.argv[2]

m = MattingNetwork("mobilenetv3").eval()
m.load_state_dict(torch.load(os.path.join(RVM_DIR, "rvm_mobilenetv3.pth"), map_location="cpu"))
dev = "mps" if torch.backends.mps.is_available() else ("cuda" if torch.cuda.is_available() else "cpu")
m = m.to(dev)

# dimensões/fps do clipe de entrada
probe = subprocess.run(
    ["ffprobe", "-v", "error", "-select_streams", "v:0",
     "-show_entries", "stream=width,height,r_frame_rate", "-of", "csv=p=0", IN],
    capture_output=True, text=True).stdout.strip().split(",")
W, H = int(probe[0]), int(probe[1])
num, den = probe[2].split("/")
fps = float(num) / float(den)

# decodificador (frames crus) e encodador (recompõe + copia o áudio do original)
dec = subprocess.Popen(
    ["ffmpeg", "-loglevel", "error", "-i", IN, "-f", "rawvideo", "-pix_fmt", "rgb24", "-"],
    stdout=subprocess.PIPE)
enc = subprocess.Popen(
    ["ffmpeg", "-y", "-loglevel", "error",
     "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(fps), "-i", "-",
     "-i", IN, "-map", "0:v", "-map", "1:a?",
     "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p",
     "-c:a", "copy", OUT],
    stdin=subprocess.PIPE)

rec = [None] * 4  # estado recorrente da rede — NÃO zerar entre frames (é ele que estabiliza a borda)
n = 0
GREEN = np.zeros((H, W, 3), dtype=np.float32)
GREEN[:, :, 1] = 1.0  # verde 100% puro = chroma key perfeito depois

with torch.no_grad():
    while True:
        raw = dec.stdout.read(W * H * 3)
        if len(raw) < W * H * 3:
            break
        img = np.frombuffer(raw, np.uint8).reshape(H, W, 3).astype(np.float32) / 255.0
        src = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(dev)
        fgr, pha, *rec = m(src, *rec, downsample_ratio=0.25)
        f = fgr[0].permute(1, 2, 0).cpu().numpy()
        a = pha[0, 0].cpu().numpy()[..., None]
        comp = f * a + GREEN * (1 - a)
        enc.stdin.write((comp * 255).clip(0, 255).astype(np.uint8).tobytes())
        n += 1

enc.stdin.close()
enc.wait()
dec.wait()
print("frames:", n, "->", OUT)
