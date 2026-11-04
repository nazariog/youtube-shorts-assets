"""Gera timeline.json (cenas, legendas e batidas) a partir de transcript.json.

transcript.json vem do faster-whisper (modelo "small", word_timestamps=True)
sobre Audio.wav. Os limites de cena ficam no meio das pausas reais da fala.
"""
import json
import re
from pathlib import Path

HERE = Path(__file__).parent
DURATION = 48.36

# Início de cada cena (segundos), no centro das pausas entre as falas:
# 6.51-7.00 | 16.59-17.13 | 29.41-29.92 | 35.70-36.14
BOUNDS = [0.0, 6.75, 16.86, 29.66, 35.92]

# Palavras que ganham cor de destaque quando ativas
EMPHASIS = {
    "bubble", "red", "$600", "ghost", "delusional", "disaster", "exit",
    "trillion", "billion", "billions", "gold", "dip", "crash", "incinerated",
    "math", "hole", "zero",
}

# Altura (centro, em px de 1920, coordenadas da CENA sem zoom) da legenda ao
# longo do vídeo. O motor converte pelo zoom da câmera. Cada trecho coloca a
# legenda numa faixa livre ou sobre algo que NÃO está sendo comentado naquele
# momento. As trocas acontecem na mudança de legenda (sem deslizar).
CAPTION_Y = [
    {"t": 0.00,  "scene": 0, "y": 1455, "fs": 92},  # topo dos racks; banner "WARNING LIGHTS" e balão livres
    {"t": 6.70,  "scene": 1, "y": 845,  "fs": 92},  # entre o cartão $1T+ e os racks (notas decorativas); título, cartão, racks e buraco livres
    {"t": 16.85, "scene": 2, "y": 471,  "fs": 78},  # faixa estreita entre o título e os prédios (fonte menor)
    {"t": 21.52, "scene": 2, "y": 1010, "fs": 92},  # "hoarding chips… electricity": estrada entre prédios e chips; chips e medidor livres
    {"t": 29.75, "scene": 3, "y": 1300, "fs": 92},  # "valuations… dot-com": sobre as notas (ainda não comentadas); gráfico e fornalha livres
    {"t": 32.20, "scene": 3, "y": 880,  "fs": 92},  # "free cash flow… hardware costs": sobre o gráfico (já comentado); notas e fornalha livres
    {"t": 36.00, "scene": 4, "y": 520,  "fs": 80},  # faixa entre o título e os dois mundos
]

STOPWORDS = {"the", "a", "an", "and", "of", "to", "is", "are", "that", "in", "at", "on",
             "or", "it's", "this", "by", "for", "with", "into", "how", "so", "but", "over"}

# Momentos de impacto (zoom punch) e subconjunto com batida grave no áudio
BEATS = [2.82, 5.78, 10.54, 12.96, 19.70, 23.80, 25.16, 31.20, 33.68, 39.96, 44.52, 47.64]
THUMPS = [2.82, 5.78, 12.96, 19.70, 39.96, 44.52]


def snap_to_speech(out):
    """O Whisper às vezes marca o início de uma palavra dentro de uma pausa.
    Palavra não começa em silêncio: move o início para o fim da pausa
    (silences.json vem de ffmpeg silencedetect, -40 dB, >= 0,12 s)."""
    sil = json.loads((HERE / "silences.json").read_text())
    for tk in out:
        for a, b in sil:
            inside = a + 0.02 < tk["s"] < b and b - tk["s"] <= 0.7 and b < tk["e"] + 0.5
            # palavra que começa antes da pausa e atravessa uma pausa longa
            spans = tk["s"] < a and tk["e"] > b - 0.1 and b - a >= 0.3 and a - tk["s"] <= 0.4
            if inside or spans:
                print(f'  ajuste: {tk["w"]} {tk["s"]:.2f} -> {b:.2f}')
                tk["s"] = round(b, 3)
                tk["e"] = max(tk["e"], round(b + 0.1, 3))
                break
    return out


def tokens():
    out = []
    for seg in json.loads((HERE / "transcript.json").read_text(encoding="utf-8")):
        for w in seg["words"]:
            raw = w["w"].strip()
            core = re.sub(r"[^\w$'\-?%]", "", raw)
            if not core:
                continue
            if core.lower() == "comm":  # "dot-com" mal transcrito
                core = "dot-com"
            out.append({
                "w": core.upper(),
                "key": core.lower().strip("?"),
                "s": round(w["s"], 3),
                "e": round(w["e"], 3),
                "brk": raw[-1] in ".,?!",
            })
    out = snap_to_speech(out)
    # "10" + "lane" -> "10-LANE"
    merged = []
    for tk in tokens_iter(out):
        merged.append(tk)
    return merged


def tokens_iter(out):
    i = 0
    while i < len(out):
        cur = out[i]
        if cur["key"] == "10" and i + 1 < len(out) and out[i + 1]["key"] == "lane":
            nxt = out[i + 1]
            yield {"w": "10-LANE", "key": "10-lane", "s": cur["s"], "e": nxt["e"], "brk": nxt["brk"]}
            i += 2
        else:
            yield cur
            i += 1


def chunk(tks):
    chunks, cur = [], []

    def close(carry_stopword=True):
        """Fecha a legenda; palavras de ligação no fim vão para a próxima."""
        nonlocal cur
        carry = []
        if carry_stopword and len(cur) > 1 and cur[-1]["key"] in STOPWORDS:
            carry = [cur.pop()]
        if cur:
            chunks.append(cur)
        cur = carry

    for i, tk in enumerate(tks):
        cur.append(tk)
        chars = sum(len(x["w"]) for x in cur)
        nxt = tks[i + 1] if i + 1 < len(tks) else None
        gap = (nxt["s"] - tk["e"]) if nxt else 9
        hard = tk["brk"] or gap > 0.35  # pontuação ou pausa: fecha de verdade
        if hard:
            close(carry_stopword=False)
        elif len(cur) >= 3 or (len(cur) == 2 and chars > 13) or chars > 17:
            close()
    close(carry_stopword=False)

    result = []
    for i, ch in enumerate(chunks):
        s = ch[0]["s"]
        nxt_s = chunks[i + 1][0]["s"] if i + 1 < len(chunks) else DURATION
        hide = min(nxt_s, ch[-1]["e"] + 0.45)
        if i == len(chunks) - 1:  # última legenda fica até o último quadro
            hide = DURATION + 1
        result.append({
            "s": s,
            "hide": round(hide, 3),
            "words": [{"w": x["w"], "s": x["s"], "em": x["key"] in EMPHASIS} for x in ch],
        })
    return result


def main():
    tl = {
        "duration": DURATION,
        "fps": 30,
        "bounds": BOUNDS,
        "beats": BEATS,
        "thumps": THUMPS,
        "caption_y": CAPTION_Y,
        "chunks": chunk(tokens()),
    }
    (HERE / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in tl["chunks"]:
        print(f'{c["s"]:6.2f} -> {c["hide"]:6.2f}  ' + " ".join(w["w"] for w in c["words"]))


if __name__ == "__main__":
    main()
