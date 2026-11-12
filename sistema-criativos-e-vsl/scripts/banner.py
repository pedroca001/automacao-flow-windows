# -*- coding: utf-8 -*-
# banner.py — os elementos de TELA que o gerador de vídeo NUNCA deve desenhar (ele erra texto):
#   faixa de headline no topo · pílula de CTA · seta · etiqueta lateral · etiqueta de preço · X vermelho
# Tudo em PIL, com QUEBRA DE LINHA POR LARGURA MEDIDA (textbbox) — nunca por contagem de caracteres
# (o "M" ocupa 3x o "I"; quebrar por caracteres = headline sangrando pra fora da faixa).
#
# Uso direto:  python3 banner.py faixa "SUA HEADLINE AQUI" vermelho/branco saida.png
#              python3 banner.py pill  "TOQUE E ASSISTA" saida.png
#              python3 banner.py seta saida.png · tag "TEXTO" saida.png · preco "R$ 97" saida.png · x saida.png
# Como módulo: import banner as B; B.faixa_png(texto, bg, txt, path)
#
# Fonte: usa Arial Black/Arial (macOS) ou DejaVu Sans Bold (Linux). Force com FONT_BOLD=/caminho.ttf FONT_REG=/caminho.ttf
# 🔴 Nunca digite glifos/símbolos (➔ ⬇ ✅) em fonte de sistema — muitas bold não têm e sai CAIXA VAZIA (tofu).
#    Símbolo = polígono em PIL (seta_png) ou não usa.
import os, sys
from PIL import Image, ImageDraw, ImageFont

def _acha_fonte(candidatos):
    for c in candidatos:
        if c and os.path.exists(c): return c
    return None

FONT_BOLD = _acha_fonte([os.environ.get("FONT_BOLD"),
    "/System/Library/Fonts/Supplemental/Arial Black.ttf", "/Library/Fonts/Arial Black.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial_Black.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/TTF/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/ariblk.ttf", "C:/Windows/Fonts/arialbd.ttf"])
FONT_REG = _acha_fonte([os.environ.get("FONT_REG"),
    "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
    "/usr/share/fonts/truetype/msttcorefonts/Arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/TTF/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf"]) or FONT_BOLD
if not FONT_BOLD:
    sys.exit("banner.py: nenhuma fonte bold encontrada. Instale DejaVu (Linux: apt install fonts-dejavu) "
             "ou aponte FONT_BOLD=/caminho/para/fonte-bold.ttf")

# paleta de faixa: (fundo, texto). ALTERNE a cada ~3 ads da leva pra leva não parecer um ad só no feed.
CORES = {
    "vermelho/branco":  ((200, 16, 16),  (255, 255, 255)),
    "amarelo/preto":    ((255, 208, 0),  (0, 0, 0)),
    "preto/branco":     ((12, 12, 12),   (255, 255, 255)),
    "branco/vermelho":  ((255, 255, 255),(200, 16, 16)),
    "verde/branco":     ((16, 122, 62),  (255, 255, 255)),
    "dourado/preto":    ((212, 175, 55), (10, 10, 10)),
    "azul/branco":      ((20, 60, 160),  (255, 255, 255)),
}
ORDEM_CORES = list(CORES.keys())
def cor_da_leva(indice_do_ad):
    """cor da faixa pelo índice do ad na leva (troca a cada 3)."""
    return ORDEM_CORES[(indice_do_ad // 3) % len(ORDEM_CORES)]

def _f(size, bold=True): return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)
def _w(d, s, f): bb = d.textbbox((0, 0), s, font=f); return bb[2] - bb[0], bb[3] - bb[1]

def faixa_png(texto, bg, txt, path, fsize=62, largura=1080, max_linhas=2):
    """Faixa de cor SÓLIDA borda a borda (não card flutuante), texto bold centralizado.
    Reduz a fonte até o texto caber em `max_linhas` de ~1000px medidos em pixels."""
    MAXW = largura - 80
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    while True:
        f = _f(fsize)
        larg = lambda s: probe.textbbox((0, 0), s, font=f)[2]
        linhas = [""]
        for w in texto.split():
            cand = (linhas[-1] + " " + w).strip()
            if larg(cand) <= MAXW or not linhas[-1]: linhas[-1] = cand
            else: linhas.append(w)
        if (len(linhas) <= max_linhas and max(larg(l) for l in linhas) <= MAXW) or fsize <= 36: break
        fsize -= 4
    lh = int(fsize * 1.3)
    H = 60 + lh * len(linhas)
    im = Image.new("RGBA", (largura, H), tuple(bg) + (255,)); d = ImageDraw.Draw(im)
    y = 30
    for ln in linhas:
        bb = d.textbbox((0, 0), ln, font=f)
        d.text(((largura - (bb[2] - bb[0])) // 2 - bb[0], y - bb[1]), ln, font=f, fill=tuple(txt) + (255,))
        y += lh
    im.save(path); return path

def pill_png(texto, path, scale=1.0, cor=(255, 208, 0)):
    """pílula de CTA (amarela por padrão) com triângulo de 'play' — usada piscando nos últimos 10s."""
    f = _f(int(56 * scale))
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw, th = _w(probe, texto, f)
    W, H = tw + int(120 * scale), th + int(56 * scale)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=H // 2, fill=tuple(cor) + (255,), outline=(0, 0, 0, 255), width=5)
    d.text((int(72 * scale), int(20 * scale)), texto, font=f, fill=(0, 0, 0, 255))
    ax, ay, s = int(30 * scale), H // 2, int(15 * scale)
    d.polygon([(ax, ay - s), (ax + int(1.6 * s), ay), (ax, ay + s)], fill=(0, 0, 0, 255))
    im.save(path); return path

def seta_png(path, cor=(255, 208, 0)):
    """seta pra baixo desenhada (polígono) — nunca o glifo ⬇."""
    im = Image.new("RGBA", (170, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.polygon([(55, 0), (115, 0), (115, 75), (160, 75), (85, 148), (10, 75), (55, 75)],
              fill=tuple(cor) + (255,), outline=(0, 0, 0, 255))
    im.save(path); return path

def tag_png(texto, cor, path, fsize=44, max_w=None):
    """etiqueta de canto pra split/comparação — vai na LATERAL, nunca sobre rosto.
    max_w: encolhe a fonte até caber (número cortado é pior que fonte menor)."""
    f = _f(fsize)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw, th = _w(probe, texto, f)
    while max_w and tw + 56 > max_w and fsize > 18:
        fsize -= 2; f = _f(fsize); tw, th = _w(probe, texto, f)
    W, H = tw + 56, th + 40
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=14, fill=tuple(cor) + (238,), outline=(255, 255, 255, 255), width=4)
    d.text((28, 14), texto, font=f, fill=(255, 255, 255, 255))
    im.save(path); return path

def etiqueta_preco(valor, cor, path, fsize=76):
    """etiqueta de preço grande (ex.: 'R$ 97' / '$19,99') com borda branca."""
    f = _f(fsize)
    probe = ImageDraw.Draw(Image.new("RGBA", (10, 10)))
    tw, th = _w(probe, valor, f)
    W, H = tw + 90, th + 60
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 0, W - 1, H - 1], radius=22, fill=tuple(cor) + (245,), outline=(255, 255, 255, 255), width=6)
    d.text((45, 24), valor, font=f, fill=(255, 255, 255, 255))
    im.save(path); return path

def x_vermelho(path, size=300):
    """X vermelho grosso (pra 'isso NÃO') — polígono, sem glifo."""
    im = Image.new("RGBA", (size, size), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    w = size // 7
    d.line([(w, w), (size - w, size - w)], fill=(220, 20, 20, 255), width=w)
    d.line([(size - w, w), (w, size - w)], fill=(220, 20, 20, 255), width=w)
    im.save(path); return path

if __name__ == "__main__":
    a = sys.argv[1:]
    if not a: sys.exit(__doc__ or "uso: banner.py faixa|pill|seta|tag|preco|x ...")
    if a[0] == "faixa":
        bg, tx = CORES.get(a[2], CORES["vermelho/branco"]); print(faixa_png(a[1], bg, tx, a[3]))
    elif a[0] == "pill": print(pill_png(a[1], a[2]))
    elif a[0] == "seta": print(seta_png(a[1]))
    elif a[0] == "tag": print(tag_png(a[1], (200, 16, 16), a[2]))
    elif a[0] == "preco": print(etiqueta_preco(a[1], (16, 122, 62), a[2]))
    elif a[0] == "x": print(x_vermelho(a[1]))
    else: sys.exit("subcomando desconhecido: " + a[0])
