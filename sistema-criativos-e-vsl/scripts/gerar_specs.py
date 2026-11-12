# -*- coding: utf-8 -*-
# gerar_specs.py — transforma a COPY APROVADA da leva (leva.json) nos SPEC.json que o driver consome.
#
# Uso:  python3 gerar_specs.py leva.json            → escreve specs/<ID>.json (um por ad) + relatório
#       python3 gerar_specs.py leva.json --so AD-03  → só um ad
#
# ENTRADA (leva.json) — o que o seu Claude escreve depois de a copy ser aprovada:
# {
#   "idioma": "pt",                                  ← idioma da FALA (pt, es, en, fr…)
#   "cta": "TOQUE E ASSISTA",                        ← texto da pílula de CTA (opcional)
#   "blocos_globais": { "REALISMO": "...", "POSERULE": "...", "TEXTRULE": "...", "NOFADE": "..." },  ← opcional; há defaults
#   "personas": {
#     "n1": { "descricao_visual": "a woman in her late 40s, dark curly hair, warm brown eyes, olive skin, cream linen blouse",
#             "cenario": "a bright home kitchen, morning light, blurred background",
#             "voz": "warm, calm, natural pace, slight smile in the voice" }
#   },
#   "itens": [
#     { "id": "AD-01", "headline": "ELA DESCOBRIU O ERRO QUE CUSTAVA CARO", "header_estilo": "vermelho/branco",
#       "gancho": {                                    ← 🔴 O GANCHO É ENTREGÁVEL SEPARADO (01-CRIATIVOS/07-GANCHOS-DE-CHOQUE.md). Vira o clipe 1.
#          "mecanica": "SPLIT",                        ←   SPLIT | INSERT_PRIMEIRO | ACAO | ESTRANHO  (distribua as 4 pela leva)
#          "persona": "n1",
#          "acao_visual": "she tips a whole shoebox of small plain white boxes into an open bin, dozens tumbling mid-air, ...",
#          "insert_visual": "macro: a tall glass of fizzing amber tonic on the marble, foam rising over the rim",   ← só SPLIT / INSERT_PRIMEIRO (vira a cena n=0)
#          "gancho_fala": "Frase do segundo zero, dezesseis a vinte e seis palavras, que acompanha a ação sem descrevê-la." },
#       "cenas": [                                     ← o CORPO começa em n=2 (o 1 é o gancho). Cada cena tem um TIPO (01-CRIATIVOS/08-CRIATIVO-DINAMICO.md):
#         { "n": 2, "tipo": "T-close", "persona": "n1",  ←   T-close | T-aberto | T-3/4 | T-cta (falando, enquadramento varia) · D (demonstra) · I (insert sem rosto, voz off) · L (outro canto do cenário)
#           "acao": "she is already mid-gesture, lifting a glass jar toward the camera and turning it slowly",
#           "fala": "Eu descobri isso por acaso, e mudou tudo." },            ← opcional: "prompt_video_custom": "..." (substitui a acao no prompt de vídeo — diálogos/props)
#         { "n": 3, "tipo": "I", "persona": "n1", "acao": "macro on the counter: two glasses side by side, the left one murky, the right one crystal clear and fizzing", "fala": "A voz continua por cima do insert." }
#       ] }
#   ]
# }
# (Sem "gancho" e sem "tipo" o script ainda funciona — mas AVISA, porque leva sem gancho separado e sem tipo por cena sai parada.)
#
# SAÍDA (specs/AD-01.json) — o formato do flow_driver.py, mais os campos que gate/montagem usam:
#   personas.<key>.prompt_img · itens[].cenas[].prompt_img / prompt_video / persona_key / fala · itens[].headline …
#
# 🔴 AUTO-TESTES (o script REPROVA e não escreve nada se falhar):
#   - placeholder não substituído: {ASSIM} ou {{assim}} em qualquer campo (já custou 2 rodadas de re-roll)
#   - fala com travessão (—/–) → vira SÍLABA FANTASMA no gerador; use vírgula/ponto
#   - fala com < 8 palavras numa cena solo → o gerador descarta o áudio (cena muda) [aviso, não erro: funda com a vizinha]
#   - fala com 8-15 palavras → metade do clipe fica muda (a lei é 16-26) [aviso]
#   - fala com > 26 palavras → não cabe em 8s [aviso]  (alvo confortável: 16-22)
#   - persona citada que não existe · n repetido · id repetido → erro
#   - descrição visual da persona tem que ser BYTE-IDÊNTICA em todas as cenas (o script garante — é o que trava roupa/rosto)
#   - DINÂMICA (avisos, doc 08): 3 cenas seguidas do mesmo tipo · ad sem gancho · mecânicas de gancho mal distribuídas na leva ·
#     choque do gancho abaixo de 80% da leva · persona repetida em ads diferentes · prompt de gancho > 600 chars ou abrindo em "the NN-year-old"
import json, os, re, sys, unicodedata

DEFAULT_BLOCOS = {   # os 6 blocos globais — entram em TODO prompt de vídeo (e os 3 primeiros no de frame). Sobrescreva em leva.json > blocos_globais
    "POSERULE": ("The camera is propped and static, nobody is holding it: no selfie arm, no phone in hand. Both of the person's hands are "
                 "free and visible. Only ONE object is handled in this clip; everything else stays as background and is never picked up. "
                 "Every action has a visible destination inside the frame and a clear final state."),
    "TEXTRULE": ("No text, letters, captions, logos, watermarks, posters with words, screens, phone displays, recording indicators or "
                 "camera UI anywhere in the frame. All walls and surfaces are blank."),
    "REALISMO": ("Ultra-realistic smartphone footage: real skin texture with pores, no beauty filter, no CGI or advertising polish, "
                 "real lighting consistent with the scene, slight handheld-feel but stable."),
    "NOFADE":   ("Single continuous take. The action and the speech are already in motion at second zero. No fade in, no fade out, "
                 "no freeze frame, no slow-motion, no camera movement (locked-off static shot). Hard cut at the end."),
    "ANATOMY":  ("Correct human anatomy: exactly two hands with five fingers each, natural proportions, no extra limbs, "
                 "no deformed hands, face stays consistent for the whole clip."),
    "FRAME":    ("Full-bleed vertical 9:16 image edge to edge: no phone frame, no mockup, no letterboxing, no pillarboxing, "
                 "no blurred bands at the top or bottom, no smaller inset video."),
    "NEG":      ("no subtitles, no text, no watermark, no letterboxing, no blurred bands, no extra hands, no extra fingers, "
                 "no deformed hands, no object duplicating or multiplying, no morphing objects, no second phone, no mirror selfie."),
}
VOICE_TAG = "[VOICE]"

# ── DINÂMICA (docs 07 e 08) ─────────────────────────────────────────────────────
MECANICAS = ("SPLIT", "INSERT_PRIMEIRO", "ACAO", "ESTRANHO")
TIPOS = {   # o que cada tipo acrescenta ao prompt (enquadramento) — todo T/L força enquadramento NOVO, senão a âncora congela a pose
    "T-close":  "Tight close-up: her face and shoulders fill the whole frame. DIFFERENT FRAMING FROM THE REFERENCE, FRAMING AND POSE ARE NEW.",
    "T-aberto": "Wide shot: seen from the waist up, the whole setting visible around the person. DIFFERENT FRAMING FROM THE REFERENCE, FRAMING AND POSE ARE NEW.",
    "T-3/4":    "Three-quarter medium shot: the person stands at the left third of the frame turned toward the right, then looks into the lens. DIFFERENT FRAMING FROM THE REFERENCE, FRAMING AND POSE ARE NEW.",
    "T-cta":    "Medium shot, one arm fully extended pointing straight down at the bottom edge of the frame. DIFFERENT FRAMING FROM THE REFERENCE, FRAMING AND POSE ARE NEW.",
    "T":        "Medium shot. DIFFERENT FRAMING FROM THE REFERENCE, FRAMING AND POSE ARE NEW.",
    "D":        "The demonstration (hands and object) is the focus while the person keeps talking to the lens.",
    "I":        "Photorealistic insert frame, hands and objects only, no face, no person visible. Off-camera narration.",
    "L":        "Same person, same outfit, in a DIFFERENT spot of the same setting. DIFFERENT FRAMING FROM THE REFERENCE, FRAMING AND POSE ARE NEW.",
}
GANCHO_ANCORA = ("Photorealistic frame of the SAME person as the reference (same face, same hair, same outfit, same room), "
                 "but NEW PROPS AND A NEW ACTION are present and must be clearly visible in the frame. No on-screen text, no phone, no screen, no brand. ")
GANCHO_FIM = " FRAMING AND POSE ARE NEW, DIFFERENT FRAMING FROM THE REFERENCE. The props described above are the focus of the shot and must be plainly visible."
INSERT_HDR = "Photorealistic insert frame, hands and objects only, no face. No on-screen text, no phone, no screen, no brand. "
CHOQUE = ("brain","mannequin","tower","giant","huge","skull","dozens","hundred","pile","stack","bucket","crate","hourglass",
          "pyramid","cage","enormous","spill","overflow","flood","knock","scatter","wall of","covered in","packed with",
          "oversized","thousand","smash","pour over","drips over","inside a","tumbling","shoebox","taped","lying on the floor")

def die(msg): sys.exit("❌ gerar_specs: " + msg)

def checa_placeholder(txt, onde):
    if re.search(r"\{\{[^}]*\}\}|\{[A-Z_][A-Z0-9_]*\}", txt or ""):
        die(f"placeholder não substituído em {onde}: {txt[:80]}")

def palavras(s): return len(re.findall(r"\w+", s or "", re.U))

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"): die("uso: python3 gerar_specs.py leva.json [--so AD-01]   (formato do leva.json: cabeçalho deste arquivo · exemplo: scripts/exemplo-leva.json)")
    leva_path = sys.argv[1]
    so = sys.argv[sys.argv.index("--so") + 1] if "--so" in sys.argv else None
    leva = json.load(open(leva_path))
    base = os.path.dirname(os.path.abspath(leva_path))
    outdir = os.path.join(base, "specs"); os.makedirs(outdir, exist_ok=True)

    idioma = leva.get("idioma", "pt")
    blocos = dict(DEFAULT_BLOCOS); blocos.update(leva.get("blocos_globais", {}))
    personas = leva.get("personas", {})
    if not personas: die("leva.json sem personas")
    for k, p in personas.items():
        for campo in ("descricao_visual",):
            if not p.get(campo): die(f"persona {k} sem '{campo}'")
        for v in p.values(): checa_placeholder(str(v), f"persona {k}")
        if not p.get("cenario"): print(f"  ⚠️  persona {k} sem 'cenario' — o master TEM que levar cenário+roupa (senão saem 21 ads da mesma camisa no mesmo apartamento, doc 08 §2)")
        if not re.search(r"\b(blouse|shirt|dress|sweater|cardigan|jacket|coat|top|t-shirt|linen|silk|suit|hoodie|polo|scrubs|apron|uniform)\b", p["descricao_visual"], re.I):
            print(f"  ⚠️  persona {k}: descricao_visual sem ROUPA explícita — descreva a roupa (cor + tecido), é o que trava o figurino")

    # prompt do MASTER (frame-âncora) de cada persona — trava rosto/roupa pra leva inteira
    def prompt_master(p):
        return (f"Vertical 9:16 photo. {p['descricao_visual']}. {p.get('cenario', 'neutral bright indoor background')}. "
                f"Looking at the camera, natural relaxed expression, medium shot from the chest up. "
                f"{blocos['REALISMO']} {blocos['TEXTRULE']} {blocos['FRAME']}")

    ids, avisos, escritos = set(), [], []
    mecs, sem_choque, sem_gancho, personas_por_ad = [], [], [], {}
    for idx, item in enumerate(leva.get("itens", [])):
        ad = item.get("id") or die(f"item #{idx} sem id")
        if ad in ids: die(f"id repetido: {ad}")
        ids.add(ad)
        if so and ad != so: continue
        checa_placeholder(item.get("headline", ""), f"{ad}.headline")
        ns = set()
        cenas_out = []
        tipos_seq = []
        # ── GANCHO (doc 07): entregável separado → vira a cena 1 (pessoa) e, em SPLIT/INSERT_PRIMEIRO, a cena 0 (insert sem rosto)
        g = item.get("gancho")
        mec = ""
        if g:
            mec = (g.get("mecanica") or "").upper().strip()
            if mec not in MECANICAS: die(f"{ad}.gancho.mecanica '{mec}' — use uma de {MECANICAS}")
            gpk = g.get("persona") or next((c.get("persona") for c in item.get("cenas", []) if c.get("persona")), "")
            if not gpk or gpk not in personas: die(f"{ad}.gancho: persona '{gpk}' não existe (informe gancho.persona)")
            av = (g.get("acao_visual") or "").strip(); iv = (g.get("insert_visual") or "").strip(); gf = (g.get("gancho_fala") or "").strip()
            for campo, val in (("acao_visual", av), ("gancho_fala", gf)):
                if not val: die(f"{ad}.gancho sem '{campo}'")
                checa_placeholder(val, f"{ad}.gancho.{campo}")
            if mec in ("SPLIT", "INSERT_PRIMEIRO") and not iv: die(f"{ad}.gancho: mecânica {mec} exige 'insert_visual'")
            if re.search(r"[—–]", gf): die(f"{ad}.gancho_fala: travessão (sílaba fantasma). Use vírgula/ponto")
            if palavras(gf) < 8: avisos.append(f"{ad}.gancho_fala com {palavras(gf)} palavras (<8) — pode sair MUDA")
            elif palavras(gf) < 16: avisos.append(f"{ad}.gancho_fala com {palavras(gf)} palavras (<16) — metade do clipe fica muda; alvo 16-26")
            if palavras(gf) > 26: avisos.append(f"{ad}.gancho_fala com {palavras(gf)} palavras (>26) — não cabe em 8s")
            if re.match(r"^\s*(the|a|an)\s+\d+[- ]year[- ]old", av, re.I): avisos.append(f"{ad}.gancho.acao_visual abre redescrevendo a pessoa ('the NN-year-old…') — abra na AÇÃO (She/He + verbo); a âncora já sabe quem é (doc 07 §5)")
            if re.search(r"split screen|TOP:|BOTTOM:", av, re.I): avisos.append(f"{ad}.gancho.acao_visual tem instrução de MONTAGEM (split/TOP/BOTTOM) — isso é receita de ffmpeg, não de geração (doc 07 §5)")
            if not any(k in (av + " " + iv).lower() for k in CHOQUE): sem_choque.append(ad)
            mecs.append(mec)
            gp = personas[gpk]
            if mec == "SPLIT": av_full = av + " Medium shot, face fully in the upper half of the frame."
            else: av_full = av
            item.setdefault("cenas", [])
            if any(c.get("n") in (0, 1) for c in item["cenas"]): die(f"{ad}: com 'gancho', as cenas do corpo começam em n=2 (o 1 é o gancho, o 0 é o insert)")
            # cena 1 = pessoa (ancorada no master) — prompt curto, aberto na ação
            item["cenas"].insert(0, {"n": 1, "persona": gpk, "acao": av_full, "fala": gf, "_gancho": True})
            if mec in ("SPLIT", "INSERT_PRIMEIRO"):
                item["cenas"].insert(0, {"n": 0, "persona": gpk, "tipo": "I", "acao": iv, "fala": "", "_insert_gancho": True})
            gp_desc_len = len(av_full) + len(GANCHO_ANCORA) + len(GANCHO_FIM)
            if gp_desc_len > 700: avisos.append(f"{ad}.gancho: prompt de imagem com ~{gp_desc_len} chars (>700) — cabeçalho longo dispara UNSAFE_GENERATION; encurte a acao_visual (doc 07 §5)")
        else:
            sem_gancho.append(ad)
        for c in item.get("cenas", []):
            n = c.get("n")
            if n is None: die(f"{ad}: cena sem n")
            if n in ns: die(f"{ad}: cena n={n} repetida")
            ns.add(n)
            pk = c.get("persona", "") or ""
            if pk and pk not in personas: die(f"{ad} cena {n}: persona '{pk}' não existe em personas")
            acao = (c.get("acao") or "").strip()
            fala = (c.get("fala") or "").strip()
            if not acao: die(f"{ad} cena {n}: sem 'acao' (descrição visual em inglês)")
            checa_placeholder(acao, f"{ad} cena {n}.acao"); checa_placeholder(fala, f"{ad} cena {n}.fala")
            if re.search(r"[—–]", fala): die(f"{ad} cena {n}: travessão na fala (vira sílaba fantasma). Use vírgula/ponto: {fala[:60]}")
            if fala and palavras(fala) < 8: avisos.append(f"{ad} cena {n}: fala com {palavras(fala)} palavras (<8) — cena pode sair MUDA; funda com a vizinha")
            elif fala and palavras(fala) < 16 and not c.get("_gancho"): avisos.append(f"{ad} cena {n}: fala com {palavras(fala)} palavras (<16) — metade do clipe fica muda; alvo 16-26 (lei do SISTEMA.md)")
            if fala and palavras(fala) > 26: avisos.append(f"{ad} cena {n}: fala com {palavras(fala)} palavras (>26) — não cabe em 8s; corte ou divida a cena")
            if fala and re.search(r"\b[A-Z]{3,}\b", fala): avisos.append(f"{ad} cena {n}: CAIXA ALTA na fala ('{re.search(r'[A-Z]{3,}', fala).group(0)}') — o gerador soletra; capitalize normal")

            p = personas.get(pk, {})
            quem = p.get("descricao_visual", "")
            cenario = p.get("cenario", "")
            tipo = (c.get("tipo") or "").strip()
            if tipo and tipo not in TIPOS: die(f"{ad} cena {n}: tipo '{tipo}' desconhecido (use {', '.join(TIPOS)})")
            tipos_seq.append(tipo)
            if tipo == "I":   # insert sem rosto, voz off: a persona só empresta a VOZ; a imagem não leva a pessoa (nem a referência do master)
                quem = ""; persona_key_img = ""
                acao = INSERT_HDR + acao
            else:
                persona_key_img = pk
                if tipo: acao = f"{acao}. {TIPOS[tipo]}"
            # frame da cena (i2i com o master como referência quando há persona)
            if c.get("_gancho"):   # gancho: NÃO redescreve a pessoa (a âncora sabe quem é); abre na ação; força os props novos a aparecerem
                prompt_img = (GANCHO_ANCORA + acao.rstrip(".") + "." + GANCHO_FIM).strip()
            else:
                prompt_img = (f"Vertical 9:16 photo. {(quem + '. ') if quem else ''}{acao}. {(cenario + '. ') if cenario else ''}"
                              f"{blocos['REALISMO']} {blocos['TEXTRULE']} {blocos['FRAME']}").strip()
            # vídeo: ação + fala embutida + blocos. A fala vai por último, com o marcador de voz.
            voz = p.get("voz", "natural, clear voice")
            if fala and tipo == "I":   # insert sem rosto: a voz da persona continua por cima (voz off), ninguém aparece
                fala_blk = f' {VOICE_TAG} Off-camera narration in {idioma}, {voz}, no person visible on screen, no other voices: "{fala}"'
            elif fala:
                fala_blk = f' {VOICE_TAG} She/he speaks in {idioma}, {voz}, lips in sync, no other voices: "{fala}"'
            else:
                fala_blk = " No speech. Ambient sound only, no music."
            corpo = (c.get("prompt_video_custom") or "").strip() or acao   # vp_custom: quando você precisa controlar ação/falante na mão
            checa_placeholder(corpo, f"{ad} cena {n}.prompt_video_custom")
            pose = "" if tipo == "I" else blocos['POSERULE'] + " "     # insert sem rosto não leva regra de pose (fala de "mãos da pessoa visíveis")
            prompt_video = (f"{corpo}. {pose}{blocos['NOFADE']} {blocos['ANATOMY']} {blocos['FRAME']} "
                            f"{blocos['REALISMO']} {blocos['TEXTRULE']}{fala_blk} Negative: {blocos['NEG']}").strip()
            if len(prompt_video) > 2300: avisos.append(f"{ad} cena {n}: prompt_video com {len(prompt_video)} chars (>2300; os blocos globais já ocupam ~1650) — a acao está longa demais; corte")
            if len(acao) > 700: avisos.append(f"{ad} cena {n}: acao com {len(acao)} chars (>700) — cabeçalho longo dispara UNSAFE_GENERATION; alvo <600 (doc 07 §5)")
            cenas_out.append({"n": n, "persona_key": persona_key_img, "prompt_img": prompt_img, "prompt_video": prompt_video,
                              "fala": fala, "acao": acao, "tipo": tipo})
            if c.get("_gancho") or c.get("_insert_gancho"): tipos_seq.pop()   # gancho e insert do gancho não entram na contagem do CORPO
        if not cenas_out: die(f"{ad}: sem cenas")
        # ── checks de DINÂMICA por ad (doc 08)
        corpo = [t for t in tipos_seq if t]      # só as cenas do CORPO com tipo declarado (gancho e seu insert já saíram da lista)
        n_corpo = len([c for c in cenas_out if float(c["n"]) >= 2]) if g else len(cenas_out)
        if not corpo: avisos.append(f"{ad}: nenhuma cena com 'tipo' (T-close/T-aberto/T-3/4/T-cta/D/I/L) — sem tipo o corpo sai parado (doc 08 §3)")
        else:
            if len(corpo) < n_corpo: avisos.append(f"{ad}: {n_corpo - len(corpo)} cena(s) do corpo sem 'tipo' — declare o tipo em TODAS as cenas do corpo")
            base = [t.split("-")[0] for t in tipos_seq if t]
            for i in range(2, len(tipos_seq)):
                if tipos_seq[i] and tipos_seq[i] == tipos_seq[i-1] == tipos_seq[i-2]:
                    avisos.append(f"{ad}: 3 cenas seguidas do tipo {tipos_seq[i]} (cenas {i-1}-{i+1} do corpo) — nunca 3 quadros iguais seguidos (doc 08)"); break
            if "I" not in base: avisos.append(f"{ad}: nenhum insert (I) no corpo — o device/mecanismo/prova precisam aparecer sem rosto (doc 08 §3)")
            if not any(t.startswith("D") for t in corpo): avisos.append(f"{ad}: nenhuma demonstração (D) no corpo")
            if len(set(corpo)) < 3: avisos.append(f"{ad}: só {len(set(corpo))} tipos distintos no corpo — misture T/D/I/L")
        pks = tuple(sorted({c["persona_key"] for c in cenas_out if c["persona_key"]}))
        if pks in personas_por_ad: avisos.append(f"{ad}: mesma persona de {personas_por_ad[pks]} — 25 ads = 25 rostos/cenários (doc 08 §2)")
        else: personas_por_ad[pks] = ad
        spec = {
            "personas": {k: {"prompt_img": prompt_master(v)} for k, v in personas.items()
                         if k in {c["persona_key"] for c in cenas_out}},
            "itens": [{"id": ad, "headline": item.get("headline", ""),
                       "header_estilo": item.get("header_estilo", ""), "cta": item.get("cta", leva.get("cta", "TOQUE E ASSISTA")),
                       "idioma": idioma, "gancho": {"mecanica": mec} if mec else {}, "cenas": cenas_out}],
        }
        out = os.path.join(outdir, f"{ad}.json")
        json.dump(spec, open(out, "w"), ensure_ascii=False, indent=1)
        escritos.append(out)

    # auto-teste final: nenhum placeholder sobrou em NENHUM spec escrito
    for f in escritos:
        checa_placeholder(open(f).read(), os.path.basename(f))
    # ── checks de DINÂMICA da LEVA (docs 07/08)
    n_itens = len(escritos)
    if sem_gancho and n_itens: avisos.append(f"LEVA: {len(sem_gancho)}/{n_itens} ads SEM bloco 'gancho' ({', '.join(sem_gancho[:6])}{'…' if len(sem_gancho) > 6 else ''}) — o gancho é entregável separado (doc 07 §1); sem ele a cena 1 vira pessoa parada falando")
    if mecs:
        from collections import Counter
        cnt = Counter(mecs); dom = cnt.most_common(1)[0]
        if len(mecs) >= 4 and dom[1] > max(2, 0.5 * len(mecs)): avisos.append(f"LEVA: mecânica {dom[0]} domina ({dom[1]}/{len(mecs)}) — distribua as 4 (doc 07 §2). Contagem: {dict(cnt)}")
        if len(mecs) >= 4 and len(cnt) < 3: avisos.append(f"LEVA: só {len(cnt)} mecânica(s) de gancho usada(s) — use as 4. Contagem: {dict(cnt)}")
        if len(mecs) >= 3 and len(sem_choque) > 0.2 * len(mecs): avisos.append(f"LEVA: {len(sem_choque)}/{len(mecs)} ganchos sem elemento de CHOQUE detectável ({', '.join(sem_choque[:8])}) — leia-os: educado demais? (doc 07 §6; o detector erra pro lado seguro)")
    print(f"✅ {len(escritos)} spec(s) em {outdir}/")
    for a in avisos: print("  ⚠️ ", a)
    if not avisos: print("  (nenhum aviso)")

if __name__ == "__main__":
    main()
