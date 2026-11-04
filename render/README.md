# Render do Short "AI Bubble"

Gera `ai-bubble-short.mp4` (1080×1920, 30 fps, 48,36 s) a partir de
`ai-bubble-storyboard-completo.html` e `Audio.wav`.

## Como os tempos foram definidos

`Audio.wav` foi transcrito com faster-whisper (modelo `small`, tempo por palavra,
resultado em `transcript.json`). Os cortes de cena ficam no meio das 4 pausas
reais da narração (checadas com `silencedetect`):

| Cena | Início | Fala |
|---|---|---|
| 1 Gancho | 0,00 s | "This isn't an AI boom… flashing red" |
| 2 Matemática | 6,75 s | "Ignore the hype… $600 billion revenue hole" |
| 3 Autoestrada | 16,86 s | "Imagine building a 10 lane superhighway… money back" |
| 4 Tese de mercado | 29,66 s | "valuations… dot-com crash levels… hardware costs" |
| 5 Debate | 35,92 s | "the technology is revolutionary… buying the dip or running for the exit?" |

As transições começam 0,30 s antes de cada fala, para a nova cena já estar na
tela quando a frase começa. Para mudar cortes, legendas ou batidas, edite
`prep_timeline.py` e rode de novo.

## Posição das legendas

A legenda muda de altura ao longo do vídeo para não cobrir o que a fala está
explicando (lista `CAPTION_Y` em `prep_timeline.py`, em coordenadas da cena;
o motor converte pelo zoom da câmera). Ela fica na zona segura do Shorts
(abaixo do topo e acima da interface inferior do YouTube) e as trocas de
posição só acontecem em pausas da fala. `silences.json` (ffmpeg
`silencedetect`) é usado para impedir que uma palavra comece dentro de uma
pausa, já que o Whisper às vezes marca o início até 0,6 s antes da voz.

## Reproduzir

```bash
pip install playwright imageio-ffmpeg numpy && playwright install chromium
python prep_timeline.py   # transcript.json -> timeline.json
python mix_audio.py       # narração + whoosh/batidas -> ../../work/mixed_audio.wav
python render.py          # quadros (Chromium) + MP4 em ../ai-bubble-short.mp4
```

O desenho das cenas é o código original do storyboard, extraído sem alterações
por `render.py`. `engine.js` adiciona a montagem peça por peça, câmera,
transições, retalhos de papel e legendas. Impact e Arial foram trocadas por
Anton e Arimo (licença OFL, pasta `fonts/`).
