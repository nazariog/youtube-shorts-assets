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

STOPWORDS = {"the", "a", "an", "and", "of", "to", "is", "are", "that", "in", "at", "on",
             "or", "it's", "this", "by", "for", "with", "into", "how", "so", "but", "over"}

# Momentos de impacto (zoom punch) e subconjunto com batida grave no áudio
BEATS = [2.82, 5.78, 10.54, 12.96, 19.70, 23.80, 25.16, 31.20, 33.68, 39.96, 44.52, 47.64]
THUMPS = [2.82, 5.78, 12.96, 19.70, 39.96, 44.52]


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
        "chunks": chunk(tokens()),
    }
    (HERE / "timeline.json").write_text(json.dumps(tl, ensure_ascii=False, indent=1), encoding="utf-8")
    for c in tl["chunks"]:
        print(f'{c["s"]:6.2f} -> {c["hide"]:6.2f}  ' + " ".join(w["w"] for w in c["words"]))


if __name__ == "__main__":
    main()
