// Generates the "How it works" pipeline animation as Lottie JSON (bodymovin 5.x).
// Five stations on a track; a pulse travels between them and each node fills as its step completes.
// Colours are passed in so the animation follows the page theme.

type RGB = [number, number, number];
export interface PipelineColors { ink: RGB; paper: RGB; accent: RGB }

export const W = 1200;
export const H = 260;
export const FPS = 60;
export const OUT = 420;
const Y = 130;
export const STATIONS = [100, 350, 600, 850, 1100];
/** Frame at which the pulse arrives at station i. */
export const arrive = (i: number) => 20 + i * 70;
const depart = (i: number) => arrive(i) + 25;
const FADE_FROM = 380;
const FADE_TO = 410;

export function hexToRgb(hex: string): RGB {
  const h = hex.trim().replace("#", "");
  const n = parseInt(h.length === 3 ? h.split("").map((c) => c + c).join("") : h.slice(0, 6), 16);
  return [((n >> 16) & 255) / 255, ((n >> 8) & 255) / 255, (n & 255) / 255];
}

const st = (k: unknown) => ({ a: 0, k });
const ease = { o: { x: [0.33], y: [0] }, i: { x: [0.2], y: [1] } };
const anim = (kfs: [number, number[]][]) => ({
  a: 1,
  k: kfs.map(([t, s], i) => (i < kfs.length - 1 ? { t, s, ...ease } : { t, s })),
});
const tr = () => ({ ty: "tr", p: st([0, 0]), a: st([0, 0]), s: st([100, 100]), r: st(0), o: st(100), sk: st(0), sa: st(0) });
const gr = (nm: string, it: object[]) => ({ ty: "gr", nm, it: [...it, tr()] });
const ellipse = (d: number) => ({ ty: "el", p: st([0, 0]), s: st([d, d]), d: 1 });
const rect = (x: number, y: number, w: number, h: number, r = 2) => ({ ty: "rc", p: st([x, y]), s: st([w, h]), r: st(r), d: 1 });
const path = (v: number[][], c = false) => ({ ty: "sh", ks: st({ i: v.map(() => [0, 0]), o: v.map(() => [0, 0]), v, c }), d: 1 });
const stroke = (c: RGB, w: number, o = 100, dash?: [number, number]) => ({
  ty: "st", c: st([...c, 1]), o: st(o), w: st(w), lc: 2, lj: 2, ml: 4,
  ...(dash ? { d: [{ n: "d", nm: "dash", v: st(dash[0]) }, { n: "g", nm: "gap", v: st(dash[1]) }, { n: "o", nm: "offset", v: st(0) }] } : {}),
});
const fill = (c: RGB, o = 100) => ({ ty: "fl", c: st([...c, 1]), o: st(o), r: 1 });

let ind = 0;
const layer = (nm: string, shapes: object[], ks: Partial<Record<"o" | "p" | "s", object>> = {}) => ({
  ddd: 0, ind: ++ind, ty: 4, nm, sr: 1, ao: 0, ip: 0, op: OUT, st: 0, bm: 0,
  ks: { o: ks.o ?? st(100), r: st(0), p: ks.p ?? st([0, 0, 0]), a: st([0, 0, 0]), s: ks.s ?? st([100, 100, 100]) },
  shapes,
});
const fadeOut = (from = 100) => anim([[0, [from]], [FADE_FROM, [from]], [FADE_TO, [0]]]);

// Station glyphs, centred on 0,0.
function glyph(i: number, c: RGB): object[] {
  const s = (w = 2.2) => stroke(c, w);
  switch (i) {
    case 0: // enquiry: lines of text
      return [gr("lines", [path([[-12, -8], [12, -8]]), path([[-12, 0], [12, 0]]), path([[-12, 8], [3, 8]]), s()])];
    case 1: // facts (solid) and unknowns (dashed)
      return [gr("fact", [rect(-8, 0, 12, 12), s()]), gr("unknown", [rect(8, 0, 12, 12), stroke(c, 2.2, 100, [3, 3])])];
    case 2: // AFS page
      return [gr("page", [path([[-9, -13], [4, -13], [9, -8], [9, 13], [-9, 13]], true), path([[-5, -2], [5, -2]]), path([[-5, 4], [5, 4]]), s()])];
    case 3: // premise check
      return [gr("check", [path([[-11, 0], [-3, 8], [12, -9]]), s(2.6)])];
    default: // report with a cited line
      return [gr("report", [rect(0, 0, 22, 26, 2), path([[-6, -5], [6, -5]]), path([[-6, 1], [6, 1]]), path([[-6, 7], [1, 7]]), s()])];
  }
}

export function pipelineAnimation({ ink, paper, accent }: PipelineColors) {
  ind = 0;
  const layers: object[] = [];
  const at = (i: number) => st([STATIONS[i], Y, 0]);

  // Pulse dot travelling along the track, holding at each station.
  const posK: [number, number[]][] = [[0, [STATIONS[0], Y, 0]]];
  STATIONS.forEach((x, i) => { posK.push([arrive(i), [x, Y, 0]]); if (i < 4) posK.push([depart(i), [x, Y, 0]]); });
  posK.push([OUT, [STATIONS[4], Y, 0]]);
  const dotOpacity = anim([[0, [0]], [14, [100]], [FADE_FROM, [100]], [FADE_TO, [0]]]);
  layers.push(layer("pulse", [gr("dot", [ellipse(14), fill(accent)])], { p: anim(posK), o: dotOpacity }));

  // Halo ripples on arrival.
  const haloS: [number, number[]][] = [[0, [100, 100, 100]]];
  const haloO: [number, number[]][] = [[0, [0]]];
  STATIONS.forEach((_, i) => {
    const a = arrive(i);
    haloS.push([a - 1, [100, 100, 100]], [a, [100, 100, 100]], [a + 34, [320, 320, 100]]);
    haloO.push([a - 1, [0]], [a, [70]], [a + 34, [0]]);
  });
  layers.push(layer("halo", [gr("ring", [ellipse(14), stroke(accent, 1.5)])], { p: anim(posK), s: anim(haloS), o: anim(haloO) }));

  STATIONS.forEach((_, i) => {
    const a = arrive(i);
    // Paper glyph shows once the node is filled.
    layers.push(layer(`glyph-on-${i}`, glyph(i, paper), { p: at(i), o: anim([[0, [0]], [a + 4, [0]], [a + 14, [100]], [FADE_FROM, [100]], [FADE_TO, [0]]]) }));
    // Ink glyph before the node is reached.
    layers.push(layer(`glyph-off-${i}`, glyph(i, ink), { p: at(i), o: anim([[0, [60]], [a, [60]], [a + 6, [0]], [FADE_FROM, [0]], [FADE_TO, [60]]]) }));
    // Ink fill that grows when the pulse arrives.
    layers.push(layer(`fill-${i}`, [gr("disc", [ellipse(72), fill(i === 4 ? accent : ink)])], {
      p: at(i),
      s: anim([[0, [0, 0, 100]], [a - 2, [0, 0, 100]], [a + 16, [100, 100, 100]]]),
      o: fadeOut(),
    }));
    // Outline ring with a small pop on arrival.
    layers.push(layer(`ring-${i}`, [gr("ring", [ellipse(72), stroke(ink, 1.5), fill(paper)])], {
      p: at(i),
      s: anim([[0, [100, 100, 100]], [a - 4, [100, 100, 100]], [a + 6, [110, 110, 100]], [a + 20, [100, 100, 100]]]),
    }));
  });

  // Report glow once the last step completes.
  layers.push(layer("report-glow", [gr("ring", [ellipse(72), stroke(accent, 2)])], {
    p: at(4),
    s: anim([[0, [100, 100, 100]], [arrive(4) + 10, [100, 100, 100]], [arrive(4) + 60, [150, 150, 100]]]),
    o: anim([[0, [0]], [arrive(4) + 10, [0]], [arrive(4) + 12, [60]], [arrive(4) + 60, [0]]]),
  }));

  // Progress line (trim follows the pulse) over the base track.
  const trimK: [number, number[]][] = [[0, [0]]];
  STATIONS.forEach((_, i) => { trimK.push([arrive(i), [i * 25]]); if (i < 4) trimK.push([depart(i), [i * 25]]); });
  const track = () => path([[STATIONS[0], Y], [STATIONS[4], Y]]);
  layers.push(layer("progress", [gr("line", [track(), stroke(accent, 2.5), { ty: "tm", s: st(0), e: anim(trimK), o: st(0), m: 1 }])], { o: fadeOut() }));
  layers.push(layer("track", [gr("line", [track(), stroke(ink, 1.5, 22)])]));

  // lottie-web rewrites animation data in place while parsing; give it an unshared copy.
  return JSON.parse(JSON.stringify({ v: "5.7.4", fr: FPS, ip: 0, op: OUT, w: W, h: H, nm: "SpectraSense pipeline", ddd: 0, assets: [], layers }));
}
