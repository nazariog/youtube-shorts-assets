// Motor de animação do Short "AI Bubble".
// O marcador de cenas abaixo é substituído por render.py com o código de
// desenho original das cenas (extraído sem alterações do storyboard HTML).
(() => {
'use strict';
/*SCENES*/

const W = 1080, H = 1920, FPS = 30;
const T = window.TIMELINE;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const E = {
  outCubic: x => 1 - Math.pow(1 - x, 3),
  inOut: x => (x < .5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  outBack: x => { const c1 = 2.2, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
};

// ---------------------------------------------------------------- revelação
// Cada primitiva de nível mais alto (poly, card, text, rack...) vira uma
// "peça". As peças aparecem na ordem em que o storyboard as desenha, subindo
// e surgindo, como recortes de papel sendo colados na cena.
let depth = 0, opIndex = 0, mode = 'draw', reveal = null;
function opProgress(k) {
  const s = reveal.span * Math.pow(k / Math.max(1, reveal.N - 1), 0.92);
  return E.outCubic(clamp((reveal.tl - s) / 0.32));
}
function wrapOp(fn) {
  return function (...a) {
    if (depth > 0) return fn.apply(this, a);
    const k = opIndex++;
    let p = 1;
    if (mode === 'reveal') { p = opProgress(k); if (p <= 0) return; }
    depth++;
    ctx.save();
    if (p < 1) { ctx.globalAlpha *= clamp(p * 1.7); ctx.translate(0, (1 - p) * 26); }
    try { return fn.apply(this, a); } finally { ctx.restore(); depth--; }
  };
}
poly = wrapOp(poly); card = wrapOp(card); oval = wrapOp(oval); line = wrapOp(line);
text = wrapOp(text); headline = wrapOp(headline); tag = wrapOp(tag); arrow = wrapOp(arrow);
server = wrapOp(server); chip = wrapOp(chip); bill = wrapOp(bill); bolt = wrapOp(bolt);
building = wrapOp(building); factory = wrapOp(factory); display = wrapOp(display);
torn = wrapOp(torn); tape = wrapOp(tape); platform = wrapOp(platform); fan = wrapOp(fan);
rack = wrapOp(rack); beacon = wrapOp(beacon); flame = wrapOp(flame);

const SC = [scene0, scene1, scene2, scene3, scene4];
// Tempo (s) que cada cena leva para ser montada por inteiro
const SPAN = [2.3, 3.2, 4.0, 2.6, 3.4];
const HEAD0 = 1.9; // primeiro quadro já chega com a cena parcialmente montada
const PRE = 0.30, TR = 0.40; // transição começa PRE antes da fala da nova cena

const mk = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
const opCount = SC.map((fn, i) => {
  const c = mk(270, 480); ctx = c.getContext('2d'); ctx.setTransform(.5, 0, 0, .5, 0, 0);
  mode = 'count'; opIndex = 0; depth = 0; fn(); mode = 'draw';
  return opIndex;
});
function drawScene(i, cv, tl) {
  ctx = cv.getContext('2d'); ctx.setTransform(2, 0, 0, 2, 0, 0); ctx.clearRect(0, 0, 540, 960);
  reveal = { tl, span: SPAN[i], N: opCount[i] };
  mode = 'reveal'; opIndex = 0; depth = 0; SC[i](); mode = 'draw';
}
const finalCv = [], live = [mk(W, H), mk(W, H)];
function sceneImage(i, tl) {
  if (tl >= SPAN[i] + 0.4) {
    if (!finalCv[i]) { finalCv[i] = mk(W, H); drawScene(i, finalCv[i], 1e9); }
    return finalCv[i];
  }
  drawScene(i, live[i % 2], tl);
  return live[i % 2];
}

// ------------------------------------------------------------------- tempo
const S = T.bounds.map((b, i) => (i === 0 ? 0 : b - PRE));      // início visual
const sceneDur = i => (i < 4 ? S[i + 1] - S[i] : T.duration - S[i]);
function activeScene(t) { let c = 0; for (let i = 0; i < 5; i++) if (t >= S[i]) c = i; return c; }

// ------------------------------------------------------------------ câmera
function punch(t) {
  let p = 0;
  for (const b of T.beats) { const d = t - b; if (d >= 0 && d < 1) p += 0.042 * Math.exp(-d * 8.5); }
  return p;
}
function drawCam(dst, img, i, t, offX = 0, rot = 0) {
  const u = clamp((t - S[i]) / sceneDur(i));
  const dir = i % 2 === 0 ? 1 : -1;
  const z = 1.055 + 0.06 * (dir > 0 ? u : 1 - u) + punch(t);
  const dx = Math.sin(t * 0.9 + i) * 9 + offX;
  const dy = Math.cos(t * 0.7 + i * 2) * 9;
  const r = Math.sin(t * 0.6 + i) * 0.0045 + rot;
  dst.save();
  dst.translate(W / 2 + dx, H / 2 + dy); dst.rotate(r); dst.scale(z, z);
  dst.drawImage(img, -W / 2, -H / 2);
  dst.restore();
}

// -------------------------------------------------------- camadas de acabamento
const out = document.getElementById('c');
const main = out.getContext('2d');
const vig = mk(W, H);
{ const g = vig.getContext('2d'); const rg = g.createRadialGradient(W / 2, H / 2, H * .30, W / 2, H / 2, H * .72);
  rg.addColorStop(0, 'rgba(20,12,6,0)'); rg.addColorStop(1, 'rgba(20,12,6,.34)'); g.fillStyle = rg; g.fillRect(0, 0, W, H); }
const redGlow = mk(W, H);
{ const g = redGlow.getContext('2d'); const rg = g.createRadialGradient(W / 2, H / 2, H * .22, W / 2, H / 2, H * .68);
  rg.addColorStop(0, 'rgba(230,40,30,0)'); rg.addColorStop(1, 'rgba(230,40,30,1)'); g.fillStyle = rg; g.fillRect(0, 0, W, H); }

// Retalhos de papel caindo (determinísticos em função do tempo)
const scraps = [];
{ const r = rng(777); const cols = [C.gold, C.terra, C.white, C.sage, C.blue];
  for (let j = 0; j < 14; j++) scraps.push({ x: r() * W, y: r() * H, vy: 55 + r() * 80, vx: (r() - .5) * 40, w: 12 + r() * 20, h: 8 + r() * 14,
    rot: r() * 6.28, om: (r() - .5) * 3.2, col: cols[Math.floor(r() * cols.length)], ph: r() * 6.28 }); }
function drawScraps(t) {
  main.save(); main.shadowColor = 'rgba(30,18,8,.35)'; main.shadowBlur = 6; main.shadowOffsetY = 3;
  for (const s of scraps) {
    const x = ((s.x + s.vx * t + Math.sin(t * 1.3 + s.ph) * 30) % (W + 120) + W + 120) % (W + 120) - 60;
    const y = ((s.y + s.vy * t) % (H + 120)) - 60;
    main.save(); main.translate(x, y); main.rotate(s.rot + s.om * t); main.scale(Math.cos(t * 2 + s.ph) * .5 + .6, 1);
    main.globalAlpha = .85; main.fillStyle = s.col; main.fillRect(-s.w / 2, -s.h / 2, s.w, s.h); main.restore();
  }
  main.restore();
}

// ---------------------------------------------------------------- legendas
const CAP_FONT = 'px Anton, Impact, sans-serif', GAP = 40;
// Altura (centro) da legenda em função do tempo, definida em timeline.json
// (caption_y). Cada trecho coloca a legenda sobre algo que NÃO está sendo
// comentado naquele momento. "tw" = duração (s) da animação de deslocamento.
// As alturas em timeline.json estão em coordenadas da CENA (1080x1920, sem
// zoom). A conversão usa o zoom de câmera da cena, para a legenda acompanhar a
// mesma faixa livre enquanto a câmera se aproxima ou se afasta.
function zoomBase(i, t) {
  const u = clamp((t - S[i]) / sceneDur(i));
  return 1.055 + 0.06 * (i % 2 === 0 ? u : 1 - u);
}
function capSeg(t) {
  const seg = T.caption_y;
  let k = 0; for (let i = 0; i < seg.length; i++) if (t >= seg[i].t) k = i;
  return seg[k];
}
function capY(t) {
  const cur = capSeg(t);
  return H / 2 + (cur.y - H / 2) * zoomBase(cur.scene, t);
}
function drawCaption(t) {
  let ch = null;
  for (const c of T.chunks) if (t >= c.s - 0.02 && t < c.hide) ch = c;
  if (!ch) return;
  const age = t - ch.s;
  const pop = age < .16 ? E.outBack(clamp(age / .16)) : 1;
  const fade = clamp((ch.hide - t) / .08);
  main.save();
  const fs = capSeg(t).fs; main.font = fs + CAP_FONT; main.textBaseline = 'middle'; main.lineJoin = 'round';
  const ws = ch.words.map(w => main.measureText(w.w).width);
  const total = ws.reduce((a, b) => a + b, 0) + GAP * (ch.words.length - 1);
  const fit = Math.min(1, 960 / total);
  main.translate(W / 2, capY(t)); main.rotate(-0.012); main.scale(fit * (.8 + .2 * pop), fit * (.8 + .2 * pop));
  main.globalAlpha = clamp(pop * 3) * fade;
  let activeIdx = 0; ch.words.forEach((w, k) => { if (t >= w.s - 0.01) activeIdx = k; });
  // Duas passagens: primeiro todos os contornos, depois todos os preenchimentos,
  // para que o contorno de uma palavra nunca cubra a vizinha.
  for (const pass of ['stroke', 'fill']) {
    let x = -total / 2;
    ch.words.forEach((w, k) => {
      const active = k === activeIdx;
      const wp = active ? clamp((t - w.s) / .14) : 1;
      const sc = active ? 1 + .10 * Math.sin(Math.PI * wp) + .03 : 1;
      main.save(); main.translate(x + ws[k] / 2, 0); main.scale(sc, sc); main.rotate(active ? -.02 * Math.sin(Math.PI * wp) : 0);
      main.textAlign = 'center';
      if (pass === 'stroke') {
        main.shadowColor = 'rgba(0,0,0,.55)'; main.shadowBlur = 18; main.shadowOffsetY = 9;
        main.lineWidth = fs * 0.185; main.strokeStyle = C.deep; main.strokeText(w.w, 0, 0);
      } else {
        main.fillStyle = active ? (w.em ? '#FF5A3C' : '#FFD35E') : (w.em ? '#FFB199' : '#FFFFFF');
        main.fillText(w.w, 0, 0);
      }
      main.restore();
      x += ws[k] + GAP;
    });
  }
  main.restore();
}

// --------------------------------------------------------------- quadro final
window.renderFrame = function (f) {
  const t = f / FPS;
  main.setTransform(1, 0, 0, 1, 0, 0); main.globalAlpha = 1; main.clearRect(0, 0, W, H);
  const cur = activeScene(t);
  const tl = t - S[cur] + (cur === 0 ? HEAD0 : 0);
  const tr = cur > 0 ? (t - S[cur]) / TR : 2;

  if (tr < 1) { // transição de papel: cena anterior sai para a esquerda, nova entra pela direita
    const u = E.inOut(clamp(tr));
    drawCam(main, sceneImage(cur - 1, 1e9), cur - 1, t, -u * W * 1.02, -u * .035);
    const edge = (1 - u) * W;
    const g = main.createLinearGradient(edge - 90, 0, edge, 0);
    g.addColorStop(0, 'rgba(0,0,0,0)'); g.addColorStop(1, 'rgba(0,0,0,.45)');
    main.fillStyle = g; main.fillRect(edge - 90, 0, 90, H);
    main.save(); main.beginPath(); main.rect(Math.max(0, edge - 4), 0, W, H); main.clip();
    drawCam(main, sceneImage(cur, tl), cur, t, (1 - u) * W * 1.02, (1 - u) * .03);
    main.restore();
  } else {
    drawCam(main, sceneImage(cur, tl), cur, t);
  }

  main.drawImage(vig, 0, 0);
  // pisca vermelho de alerta na cena 1 ("warning lights... red")
  if (t > 3.9 && t < 6.9) {
    const a = .30 * (.5 - .5 * Math.cos((t - 3.9) * 2 * Math.PI * 1.7)) * clamp((6.9 - t) / .4) * clamp((t - 3.9) / .3);
    main.globalAlpha = a; main.drawImage(redGlow, 0, 0); main.globalAlpha = 1;
  }
  drawScraps(t);
  drawCaption(t);
  return out.toDataURL('image/jpeg', 0.95);
};
// Auxiliar de análise: cena sem câmera/legenda (tl >= 1e9: completa; tl < 0: só o fundo)
window.sceneDataURL = (i, tl) => { drawScene(i, live[0], tl); return live[0].toDataURL('image/png'); };
window.ENGINE_READY = true;
})();
