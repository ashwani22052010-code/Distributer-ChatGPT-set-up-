#!/usr/bin/env python3
"""ChatGPT Chat Simulator  ->  4K MP4  (Glitch Roast intro (optional), typing + mood sound effects,
mood-based background music, optional Shorts version).

Usage:  python3 render.py scripts/video1.txt --out out
"""
import argparse, json, math, multiprocessing, os, re, subprocess, sys, time, wave
from pathlib import Path

BRAND = "Glitch Roast"               # intro me ye naam dikhega
INTRO_S = 2.8                        # intro kitne second ka
W, H = 1920, 1080                    # page size; DSF=2 -> 3840x2160 (4K)
HERE = Path(__file__).resolve().parent
SR = 44100

# ----------------------------------------------------------------- numpy (khud install ho jaata hai)
try:
    import numpy as np
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "numpy"])
    import numpy as np

# ----------------------------------------------------------------- page helpers
INIT_JS = """
(() => {
  window.AudioContext = window.webkitAudioContext = undefined;
  let sd = 1234567;                       // fixed seed: har baar aur har worker me same timeline
  Math.random = () => { sd |= 0; sd = sd + 0x6D2B79F5 | 0; let t = Math.imul(sd ^ sd >>> 15, 1 | sd);
    t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; };
  window.__clicks = []; window.__done = false;
  window.__sync = (T, step) => {
    for (const a of document.getAnimations()) {
      if (a.__s === undefined) { a.__s = T - step / 2; a.pause(); }
      const t = T - a.__s, e = a.effect && a.effect.getComputedTiming().endTime;
      if (isFinite(e) && t >= e) { a.finish(); continue; }
      a.currentTime = t;
    }
    return window.__done;
  };
})();
"""

PAGE_CSS = """
#tg,#panel{display:none!important}
html,body{background:#000!important}
@font-face{font-family:EMO;src:local("Noto Color Emoji");unicode-range:U+1F000-1FFFF,U+2190-21FF,U+2300-23FF,U+2600-27BF,U+2B00-2BFF,U+FE0F,U+200D}
#stage,#stage *{font-family:%s!important}
"""

# har turn ka start/end time note karta hai (sound effects aur music ke liye)
LOG_JS = """
() => {
  const L = window.__log = []; let i = 0;
  for (const n of ['userTurn', 'gptTurn', 'cmdTurn']) {
    const o = window[n];
    window[n] = async function (t) {
      const e = {k: n === 'cmdTurn' ? -1 : i++, n, s: performance.now(), th: +document.querySelector('#th').value, c: (t && t.cmd) || null};
      L.push(e);
      try { return await o.call(this, t); } finally { e.e = performance.now(); }
    };
  }
}
"""

LAUNCH_ARGS = ["--force-color-profile=srgb", "--font-render-hinting=none", "--hide-scrollbars"]

OVERLAY_CSS = """
#ov{position:absolute;inset:0;pointer-events:none;z-index:30}
.ovi,.ovc{position:absolute;inset:0;background:#000;display:none;flex-direction:column;align-items:center;justify-content:center;text-align:center;padding:0 5cqw}
.ovi{background:#05070a}
.ovi.on{display:flex;animation:ovBg var(--d) linear both}
.ovc.on{display:flex}
.ovi .t,.ovc .ct{position:relative;font-weight:800;line-height:1.12;color:#fff;letter-spacing:.01em;
 text-shadow:-.28cqw 0 #00f0ff,.28cqw 0 #ff2a6d;animation:ovPop .5s cubic-bezier(.2,1.3,.4,1) both,ovGl .6s steps(1) both}
.ovi .s,.ovc .cs{margin-top:2cqw;color:#cfd3d8;font-weight:600;animation:ovFade .5s ease-out .45s both}
.ovi .b{margin-top:3cqw;height:.55cqw;width:34cqw;background:linear-gradient(90deg,#00f0ff,#ff2a6d);animation:ovBar .8s ease-out .3s both}
.ove{position:absolute;inset:0;background:rgba(0,0,0,.8);display:none;flex-direction:column;align-items:center;justify-content:center;gap:3cqw;text-align:center}
.ove.on{display:flex;animation:ovFade .5s ease-out both}
.ove .t{font-size:5.4cqw;font-weight:800;color:#fff;animation:ovPop .6s cubic-bezier(.2,1.4,.4,1) .15s both}
.ove .s{margin-top:-1.6cqw;font-size:2.4cqw;color:#cfd3d8;animation:ovFade .5s ease-out .5s both}
.ove .row{display:flex;align-items:center;gap:2.2cqw;animation:ovSlide .6s cubic-bezier(.2,1.2,.4,1) .55s both}
.ove .bw{position:relative;width:21cqw;height:5.8cqw}
.ove .btn{position:absolute;inset:0;border-radius:2.9cqw;display:flex;align-items:center;justify-content:center;font-weight:800;font-size:2.4cqw;letter-spacing:.08em;color:#fff}
.ove .sub{background:#f00;animation:ovSubOut .3s ease-in 1.5s both}
.ove .done{background:#2b2b2b;opacity:0;animation:ovDoneIn .3s ease-out 1.6s both}
.ove .bell{width:5.2cqw;height:5.2cqw;opacity:0;animation:ovFade .3s ease-out 1.8s both}
.ove .bell svg{width:100%;height:100%;stroke:#fff;fill:none;stroke-width:1.7;stroke-linecap:round;stroke-linejoin:round;transform-origin:50% 8%;animation:ovRing 1.2s ease-in-out 2.1s both}
@keyframes ovBg{0%{opacity:0}5%{opacity:1}90%{opacity:1}100%{opacity:0}}
@keyframes ovPop{0%{opacity:0;transform:scale(.88)}100%{opacity:1;transform:scale(1)}}
@keyframes ovFade{0%{opacity:0}100%{opacity:1}}
@keyframes ovBar{0%{width:0}100%{width:34cqw}}
@keyframes ovGl{0%{transform:translate(-1cqw,0)}12%{transform:translate(1.1cqw,.2cqw)}24%{transform:translate(-.6cqw,-.2cqw)}36%{transform:translate(.7cqw,0)}48%{transform:translate(-.25cqw,0)}60%,100%{transform:translate(0,0)}}
@keyframes ovSlide{0%{opacity:0;transform:translateY(2.5cqw)}100%{opacity:1;transform:translateY(0)}}
@keyframes ovSubOut{0%{transform:scale(1);opacity:1}40%{transform:scale(.9);opacity:1}100%{transform:scale(.9);opacity:0}}
@keyframes ovDoneIn{0%{opacity:0;transform:scale(.9)}100%{opacity:1;transform:scale(1)}}
@keyframes ovRing{0%{transform:rotate(0)}15%{transform:rotate(18deg)}30%{transform:rotate(-16deg)}45%{transform:rotate(12deg)}60%{transform:rotate(-8deg)}75%{transform:rotate(4deg)}100%{transform:rotate(0)}}
"""

OVERLAY_JS = r"""
() => {
  const st = document.querySelector('#stage'), ov = document.createElement('div'); ov.id = 'ov'; st.appendChild(ov);
  const esc = s => String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
  const split = t => { const p = String(t).split('|'); return [p[0].trim(), (p.slice(1).join('|') || '').trim()]; };
  const BELL = '<svg viewBox="0 0 24 24"><path d="M6 17V11a6 6 0 0 1 12 0v6l1.5 2h-15z"/><path d="M10 21a2 2 0 0 0 4 0"/></svg>';
  // text ko screen ki left-right chaudai tak bada karta hai (zyada lamba ho to 2-3 lines me)
  const fitTxt = (el, maxF, minF, targetW, wrapW) => {
    const cq = st.clientWidth / 100;
    el.style.display = 'inline-block'; el.style.whiteSpace = 'nowrap'; el.style.maxWidth = ''; el.style.fontSize = maxF + 'cqw';
    const w = el.scrollWidth / cq;
    let f = maxF * Math.min(1, targetW / w);
    if (f < minF) { f = minF; el.style.whiteSpace = 'normal'; el.style.maxWidth = wrapW + 'cqw'; }
    el.style.fontSize = f + 'cqw'; return f;
  };
  const card = (cls, a, b, d, big) => {
    const e = document.createElement('div'); e.className = cls; e.style.setProperty('--d', d + 's');
    const t1 = cls === 'ovi' ? 't' : 'ct', t2 = cls === 'ovi' ? 's' : 'cs';
    e.innerHTML = '<div class="' + t1 + '">' + esc(a) + '</div>' + (cls === 'ovi' ? '<div class="b"></div>' : '') + (b ? '<div class="' + t2 + '">' + esc(b) + '</div>' : '');
    ov.appendChild(e); e.classList.add('on');
    const f = fitTxt(e.querySelector('.' + t1), big, 5.6, 90, 90);
    const sub = e.querySelector('.' + t2); if (sub) fitTxt(sub, Math.max(2.6, Math.min(5.4, f * 0.42)), 2.4, 88, 88);
    return e;
  };
  window.cmdTurn = async function (m) {
    const [a, b] = split(m.t);
    if (m.cmd === 'intro') {
      const d = m.dur || 3.2, e = card('ovi', a, b, d, 14); await sleep(d * 1000); e.remove();
    } else if (m.cmd === 'caption' || m.cmd === 'level') {            // poori black screen, chat dikhti nahi, conversation ruki rehti hai
      const d = m.dur || 3, e = card('ovc', a, b, d, 18); await sleep(d * 1000); e.remove();
    } else if (m.cmd === 'end') {
      const e = document.createElement('div'); e.className = 'ove';
      e.innerHTML = '<div class="t">' + esc(a || 'Thanks for watching!') + '</div>' + (b ? '<div class="s">' + esc(b) + '</div>' : '') +
        '<div class="row"><div class="bw"><div class="btn sub">SUBSCRIBE</div><div class="btn done">SUBSCRIBED</div></div><div class="bell">' + BELL + '</div></div>';
      ov.appendChild(e); e.classList.add('on'); await sleep(5000); e.remove();
    }
  };
  // ---- lamba ChatGPT/Gemini reply: camera itna zoom kare ki poora message screen me aa jaaye
  const _zoom = window.zoom;
  window.zoom = function (k) {
    if (k === 'reply' && window.__fit && document.querySelector('#zm').checked) {
      const f = window.__fit; world.style.setProperty('--z', f.z); world.style.setProperty('--ox', f.ox); world.style.setProperty('--oy', f.oy); return;
    }
    return _zoom(k);
  };
  const dockEls = () => ['#dock', '#note', '#pill'].map(q => document.querySelector(q)).filter(e => e);
  const resetFit = () => { msgEl.style.maxWidth = ''; msgEl.style.top = ''; dockEls().forEach(e => e.style.opacity = ''); };
  const fitReply = text => {
    resetFit(); reply.textContent = text;                               // poora text rakh kar size naapo
    const W = st.clientWidth, H = st.clientHeight, cq = W / 100, mx = 3.5 * cq, my = 3.5 * cq, p = Z.reply;
    const zmax = parseFloat(p[0]), pox = parseFloat(p[1]) / 100 * W, poy = parseFloat(p[2]) / 100 * H;
    const tops = dockEls().filter(e => e.offsetParent === world).map(e => e.offsetTop);
    const pillTop = tops.length ? Math.min(...tops) : H, gap = 1.5 * cq;
    const L = msgEl.offsetLeft, T = msgEl.offsetTop; let w = msgEl.offsetWidth, h = msgEl.offsetHeight;
    const x0 = pox + (L - pox) * zmax, x1 = pox + (L + w - pox) * zmax, y0 = poy + (T - poy) * zmax, y1 = poy + (T + h - poy) * zmax;
    if (x0 >= mx && x1 <= W - mx && y0 >= my && y1 <= H - my && T + h <= pillTop - gap) { reply.textContent = ''; return null; }  // chhota message: pehle jaisa
    // bada message: message ko upar le jao, sahi chaudai ki column chuno taaki chat-box se na takraye aur zoom sabse zyada ho
    const T2 = 3 * cq; msgEl.style.top = T2 + 'px';
    let availH = pillTop - gap - T2, best = null;
    const scan = limitH => {
      for (let wc = 88; wc >= 34; wc -= 2) {
        msgEl.style.maxWidth = wc + 'cqw'; w = msgEl.offsetWidth; h = msgEl.offsetHeight;
        if (h <= limitH) { const z = Math.min(zmax, (W - 2 * mx) / w, (H - 2 * my) / h); if (!best || z > best.z + 0.001) best = {z, wc}; }
      }
    };
    scan(availH);
    if (!best) { dockEls().forEach(e => e.style.opacity = 0); scan(H - T2 - my); }   // bahut lamba: input box ko reply ke time chhupa do
    reply.textContent = '';
    if (!best) { resetFit(); return {z: '1', ox: '50%', oy: '50%'}; }
    msgEl.style.maxWidth = best.wc + 'cqw';
    if (best.z < 1.04) return {z: '1', ox: '50%', oy: '50%'};
    const z = best.z;
    return {z: String(z), ox: ((mx - L * z) / (1 - z) / W * 100) + '%', oy: ((my - T2 * z) / (1 - z) / H * 100) + '%'};
  };
  window.parse = function (t) {
    const o = [];
    t.split(/\r?\n/).forEach(l => {
      const c = l.match(/^\s*!(\w+)(?:\s+(\d+(?:\.\d+)?))?\s*:?\s*(.*)$/);
      if (c) { o.push({r: 'c', cmd: c[1].toLowerCase(), dur: c[2] ? +c[2] : null, t: c[3].trim()}); return; }
      const m = l.match(/^\s*(user|you|gemini|chatgpt|gpt|ai|assistant)\s*:\s*(.*)$/i);
      if (m) o.push({r: /^(user|you)$/i.test(m[1]) ? 'u' : 'g', t: clean(m[2])});
      else if (l.trim() && o.length && o[o.length - 1].r !== 'c') o[o.length - 1].t += '\n' + l.trim();
    });
    return o;
  };
  window.play = async function () {
    load(); if (!msgs.length) return;
    run++; cur = run; paused = false; resetUI();
    try {
      if (!(msgs[0].r === 'c' && msgs[0].cmd === 'intro')) await sleep(500);
      for (const m of msgs) {
        if (m.r === 'c') await cmdTurn(m);
        else if (m.r === 'u') await userTurn(m.t);
        else { window.__fit = fitReply(m.t); await gptTurn(m.t); resetFit(); }
      }
      await sleep(600); zoom('wide');
      const o = window.__opts || {};
      if (!/^(off|no|0|false)$/i.test(o.end || 'on') && !msgs.some(m => m.r === 'c' && m.cmd === 'end'))
        await cmdTurn({r: 'c', cmd: 'end', t: 'Thanks for watching!|' + (window.__brand || '')});
    } catch (e) {}
  };
}
"""

OPT_KEYS = {"typing": "ts", "reply": "rs", "think": "th", "pause": "hd"}
OPT_RE = re.compile(r"^\s*#\s*(typing|reply|think|pause|zoom|music|sfx|click|keys|intro|shorts|auto|app|end|bgm|bgm_start|bgm_vol)\s*=\s*(\S+)\s*$", re.I)
MSG_RE = re.compile(r"^\s*(user|you|gemini|chatgpt|gpt|ai|assistant)\s*:\s*(.*)$", re.I)

MOODS = ["calm", "funny", "scary", "sad", "mystery", "hype", "surprise", "angry"]
MUSIC_OF = {"calm": "calm", "funny": "funny", "scary": "scary", "sad": "sad",
            "mystery": "mystery", "hype": "hype", "surprise": "hype", "angry": "scary"}
TAG_RE = re.compile(r"\s*\{\s*(%s)\s*\}" % "|".join(MOODS), re.I)

AUTO = [  # (mood, emojis, words) - tag na ho tab ye andaza lagata hai
    ("funny", "😂🤣😆😹", r"\b(lol|lmao|rofl|haha+)\b"),
    ("scary", "😱😨😰👻💀🩸🔪🕷", r"\b(scary|ghost|haunted|creepy)\b"),
    ("sad", "😢😭💔😞😔🥺", r"\b(sad|crying|miss you)\b"),
    ("mystery", "🤔🧐🕵🔍", r"\b(secret|mystery|suspicious)\b"),
    ("hype", "🔥🎉🚀💪🥳🤩🏆", r"\b(let'?s go|amazing|epic)\b"),
    ("surprise", "😲😮🤯😳", r"\bno way\b|\bwhat\?!"),
    ("angry", "😡🤬😠👿", r"\b(angry|hate|stupid|idiot)\b"),
]

MOJI = re.compile("[\u00c2-\u00f4][\u0080-\u00bf\u0152\u0153\u0160\u0161\u0178\u017d\u017e\u0192\u02c6\u02dc\u2013-\u203a\u20ac\u2122]")


def fix_mojibake(line):
    """'ðŸ˜€' jaisa kharab text (galat encoding me save hua) wapas asli emoji bana deta hai."""
    if not MOJI.search(line):
        return line
    try:
        raw = bytearray()
        for ch in line:
            try:
                raw += ch.encode("cp1252")
            except UnicodeEncodeError:
                raw += ch.encode("latin-1")
        return raw.decode("utf-8")
    except (UnicodeEncodeError, UnicodeDecodeError):
        return line


def auto_mood(text):
    for mood, emojis, rx in AUTO:
        if any(e in text for e in emojis) or re.search(rx, text, re.I):
            return mood
    return None


def parse_script(path):
    """Returns (clean_text, options, moods{msg_index: mood})."""
    opts, lines, tags, texts, idx = {}, [], {}, {}, -1
    for line in Path(path).read_text(encoding="utf-8-sig").splitlines():
        line = fix_mojibake(line)
        m = OPT_RE.match(line)
        if m:
            opts[m.group(1).lower()] = m.group(2)
            continue
        if line.lstrip().startswith("!"):
            lines.append(line.rstrip())
            continue
        if MSG_RE.match(line):
            idx += 1
        if idx >= 0:
            found = TAG_RE.findall(line)
            if found:
                tags[idx] = found[-1].lower()
        line = TAG_RE.sub("", line).rstrip()
        if idx >= 0:
            texts[idx] = texts.get(idx, "") + " " + line
        lines.append(line)
    moods = dict(tags)
    if opts.get("auto", "on").lower() not in ("off", "no", "0", "false"):
        for i, t in texts.items():
            if i not in moods:
                g = auto_mood(t)
                if g:
                    moods[i] = g
    return "\n".join(lines).strip(), opts, moods


def find_html(name):
    """ChatGPT.html / Gemini.html ka naam thoda alag ho (capital/space/(1)) tab bhi dhundh leta hai."""
    p = HERE / name
    if p.exists():
        return p
    cands = sorted(HERE.glob("*.[hH][tT][mM][lL]"))
    want = Path(name).stem.lower().split(" ")[0].split("(")[0]          # 'chatgpt' ya 'gemini'
    for c in cands:
        if want and want in c.name.lower():
            return c
    if "gemini" not in name.lower():
        for c in cands:
            if "gptsim" in c.read_text(encoding="utf-8", errors="ignore"):
                return c
    sys.exit(f"{name} nahi mili. Repo me ye files hain: {[x.name for x in HERE.iterdir()]}")


# ================================================================= AUDIO SYNTH
def tt(d):
    return np.arange(int(d * SR)) / SR


def midi(n):
    return 440.0 * 2 ** ((n - 69) / 12)


def tone(f, d, decay=4.0, harm=(1,), amps=None, attack=0.004, tremolo=0.0):
    t = tt(d)
    amps = amps or [1.0 / h for h in harm]
    x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in zip(harm, amps))
    x = x * np.minimum(1, t / attack) * np.exp(-decay * t)
    if tremolo:
        x = x * (0.75 + 0.25 * np.sin(2 * np.pi * tremolo * t))
    return x


def pad_note(f, d, attack=0.5, release=0.5, harm=(1, 2), amps=(1, 0.25)):
    t = tt(d)
    x = sum(a * np.sin(2 * np.pi * f * h * t) for h, a in zip(harm, amps))
    return x * np.minimum(1, t / attack) * np.clip((d - t) / release, 0, 1)


def noise(d, seed=1):
    return np.random.default_rng(seed).standard_normal(int(d * SR))


def put(out, x, t, g=1.0):
    s = int(round(t * SR))
    if s >= len(out) or s + len(x) <= 0:
        return
    a, b = max(0, -s), min(len(x), len(out) - s)
    out[s + a:s + b] += x[a:b] * g


def reverb(x, rt=1.2, mix=0.25, seed=3):
    n = int(rt * SR)
    rng = np.random.default_rng(seed)
    ir = rng.standard_normal(n) * np.exp(-6.9 * np.arange(n) / n)
    ir[0] = 0
    L = len(x) + n
    N = 1 << (L - 1).bit_length()
    y = np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:L]
    y *= (np.abs(x).max() + 1e-9) / (np.abs(y).max() + 1e-9)
    out = np.zeros(L)
    out[:len(x)] += x * (1 - mix)
    out += y * mix
    return out


def kick(amp=1.0):
    t = tt(0.32)
    f = 45 + 95 * np.exp(-t * 30)
    return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 12) * amp


def hat(amp=1.0, seed=5):
    x = np.diff(noise(0.07, seed), prepend=0)
    return x * np.exp(-tt(0.07) * 70) * amp


# ---- music beds
BEDS = {
    "calm":    dict(bpm=72, chords=[[48, 52, 55, 59], [45, 48, 52, 55], [41, 45, 48, 52], [43, 47, 50, 53]],
                    pad=0.45, arp=[0, 1, 2, 3, 2, 1, 2, 1], arp_amp=0.22, bass=0.45, kick=0.35, hat=0.05, rev=0.3),
    "funny":   dict(bpm=116, chords=[[48, 52, 55], [53, 57, 60], [55, 59, 62], [48, 52, 55]],
                    pad=0.16, penta=[60, 62, 64, 67, 69, 72], pluck=0.3, bass=0.45, tick=0.07, rev=0.12),
    "scary":   dict(bpm=60, chords=[[33, 34, 45]] * 4, pad=0.5, tremolo=5.0, heart=0.8, shimmer=0.035, rev=0.4),
    "sad":     dict(bpm=58, chords=[[45, 48, 52, 57], [41, 45, 48, 53], [48, 52, 55, 60], [43, 47, 50, 55]],
                    pad=0.5, bells=[72, 71, 69, 67, 69, 67, 64, 62], bell_amp=0.28, rev=0.4),
    "mystery": dict(bpm=76, chords=[[50, 53, 57, 60], [46, 50, 53, 57], [43, 46, 50, 53], [45, 49, 52, 55]],
                    pad=0.42, pings=[74, 77, 79, 81, 84], ping_amp=0.2, rev=0.45),
    "hype":    dict(bpm=126, chords=[[57, 60, 64], [53, 57, 60], [48, 52, 55], [55, 59, 62]],
                    pad=0.2, kick=0.6, hat=0.07, bass8=0.4, arp16=0.2, rev=0.12),
}


def make_bed(mood):
    sp = BEDS[mood]
    spb = 60.0 / sp["bpm"]
    bar = 4 * spb
    ch = sp["chords"]
    bars = len(ch)
    L = int(round(bars * bar * SR))
    out = np.zeros(2 * L + 2 * SR)
    rng = np.random.default_rng(42)
    step = spb / 4
    for loop in range(2):
        for bi, chord in enumerate(ch):
            t0 = (loop * bars + bi) * bar
            for n in chord:
                x = pad_note(midi(n), bar + 0.6)
                if sp.get("tremolo"):
                    x = x * (0.8 + 0.2 * np.sin(2 * np.pi * sp["tremolo"] * tt(bar + 0.6)))
                put(out, x, t0 - 0.1, sp["pad"] / max(1, len(chord) ** 0.5))
            root = chord[0]
            if "bass" in sp:
                for b in (0, 2):
                    put(out, tone(midi(root - 12), spb * 1.8, decay=2.5), t0 + b * spb, sp["bass"])
            if "arp" in sp:
                for s in range(8):
                    n = chord[sp["arp"][s] % len(chord)] + 12
                    put(out, tone(midi(n), spb, decay=6), t0 + s * spb / 2, sp["arp_amp"])
            if "kick" in sp:
                beats = (0, 2) if mood == "calm" else (0, 1, 2, 3)
                for b in beats:
                    put(out, kick(), t0 + b * spb, sp["kick"])
            if "hat" in sp:
                for s in range(8):
                    put(out, hat(seed=s + 1), t0 + s * spb / 2 + spb / 4 if mood == "hype" else t0 + s * spb / 2 + spb / 2, sp["hat"])
            if "penta" in sp:
                for s in range(16):
                    if rng.random() < 0.62:
                        n = int(rng.choice(sp["penta"]))
                        put(out, tone(midi(n), 0.25, decay=14, harm=(1, 2), amps=(1, .3)), t0 + s * step, sp["pluck"])
                put(out, tone(midi(root - 12), spb, decay=7), t0, sp["bass"])
                put(out, tone(midi(root - 12 + 7), spb, decay=7), t0 + 2.5 * spb, sp["bass"])
            if "tick" in sp:
                for b in range(4):
                    put(out, tone(1200, 0.06, decay=60), t0 + b * spb, sp["tick"])
            if "heart" in sp:
                for b in range(4):
                    put(out, kick(), t0 + b * spb, sp["heart"])
                    put(out, kick(), t0 + b * spb + 0.26, sp["heart"] * 0.6)
            if "shimmer" in sp and bi % 2 == 0:
                for f in (2093.0, 2217.5):
                    put(out, pad_note(f, bar * 2, attack=bar, release=bar), t0, sp["shimmer"])
            if "bells" in sp:
                for k, b in enumerate((0, 2)):
                    n = sp["bells"][(bi * 2 + k) % len(sp["bells"])]
                    put(out, tone(midi(n), 2.5, decay=1.6, harm=(1, 2.76, 5.4), amps=(1, .35, .15)), t0 + b * spb, sp["bell_amp"])
            if "pings" in sp:
                for _ in range(2):
                    n = int(rng.choice(sp["pings"]))
                    put(out, tone(midi(n), 3.0, decay=1.8, harm=(1, 2.01), amps=(1, .3)), t0 + rng.uniform(0, bar - 0.5), sp["ping_amp"])
            if "bass8" in sp:
                for s in range(8):
                    put(out, tone(midi(root - 24), spb / 2, decay=6, harm=(1, 2), amps=(1, .4)), t0 + s * spb / 2, sp["bass8"])
            if "arp16" in sp:
                for s in range(16):
                    n = chord[s % len(chord)] + 12 * (1 + (s // 4) % 2)
                    put(out, tone(midi(n), 0.2, decay=12), t0 + s * step, sp["arp16"])
    y = reverb(out[:2 * L + SR], rt=1.8, mix=sp["rev"])
    bed = y[L:2 * L]
    return bed / (np.abs(bed).max() + 1e-9) * 0.9


def music_track(timeline, seconds, intro_s, vol):
    n = int(seconds * SR)
    t = np.arange(n) / SR
    tl = [(0.0, "calm")]
    for tm, m in sorted(timeline):
        if m != tl[-1][1]:
            tl.append((max(tm, tl[-1][0] + 2.0), m))
    used = sorted({m for _, m in tl})
    out = np.zeros(n)
    for m in used:
        bed = make_bed(m)
        sig = np.tile(bed, n // len(bed) + 1)[:n]
        xs, ys = [0.0], [1.0 if tl[0][1] == m else 0.0]
        for i in range(1, len(tl)):
            xs += [tl[i][0] - 0.5, tl[i][0] + 1.5]
            ys += [1.0 if tl[i - 1][1] == m else 0.0, 1.0 if tl[i][1] == m else 0.0]
        g = np.sin(np.interp(t, xs, ys) * np.pi / 2)
        out += sig * g
    fade = np.interp(t, [0, intro_s, intro_s + 1.5, seconds - 2.5, seconds], [0, 0, 1, 1, 0])
    return out * fade * vol


# ---- sound effects
def sfx(name):
    if name == "send":
        t = tt(0.09)
        return np.sin(2 * np.pi * np.cumsum(700 - 3000 * t) / SR) * np.exp(-t * 35) * 0.30
    if name == "recv":
        x = np.zeros(int(0.5 * SR))
        put(x, tone(880, 0.4, decay=9), 0, 0.22)
        put(x, tone(1318.5, 0.4, decay=9), 0.07, 0.22)
        return x
    if name == "funny":
        t = tt(0.55)
        f = 240 + 170 * np.sin(2 * np.pi * 9 * t) * np.exp(-5 * t) + 330 * np.exp(-6 * t)
        return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5) * 0.5
    if name in ("scary", "angry"):
        d = 1.8 if name == "scary" else 0.7
        t = tt(d)
        body = np.sin(2 * np.pi * (55 if name == "scary" else 80) * t) * np.exp(-t * (2.2 if name == "scary" else 5))
        rumble = np.convolve(noise(d, 9), np.ones(60) / 60, mode="same") * np.exp(-t * 3) * 3
        x = (body * 0.7 + rumble * 0.4)
        if name == "angry":
            saw = sum(np.sin(2 * np.pi * 80 * h * t) / h for h in range(1, 9)) * np.exp(-t * 6)
            x = np.tanh(saw * 1.6) * 0.5 + body * 0.4
        return reverb(x, rt=1.2, mix=0.3)[:int(d * SR + SR)] * 0.9
    if name == "sad":
        x = np.zeros(int(2.4 * SR))
        put(x, tone(midi(76), 1.8, decay=2.2, harm=(1, 2.76), amps=(1, .3)), 0, 0.3)
        put(x, tone(midi(72), 2.0, decay=2.0, harm=(1, 2.76), amps=(1, .3)), 0.45, 0.3)
        return reverb(x, rt=1.5, mix=0.35)
    if name == "mystery":
        d = 2.6
        x = (tone(1318.5, d, decay=1.6, harm=(1, 1.5), amps=(1, .5), tremolo=6) +
             tone(1976, d, decay=1.8, tremolo=4) * 0.6 + tone(2637, d, decay=2.2) * 0.35)
        return reverb(x * 0.18, rt=2.0, mix=0.45)
    if name == "whoosh":
        d = 0.7; t = tt(d)
        w = np.diff(noise(d, 8), prepend=0) * np.sin(np.pi * t / d) ** 2
        return w / (np.abs(w).max() + 1e-9) * 0.4
    if name == "hit":
        t = tt(0.5)
        x = np.sin(2 * np.pi * 62 * t) * np.exp(-t * 9) + _lp(noise(0.5, 6), 18) * np.exp(-t * 30) * 2
        return x / (np.abs(x).max() + 1e-9) * 0.55
    if name == "pop2":
        t = tt(0.16)
        x = np.sin(2 * np.pi * np.cumsum(520 + 1500 * t) / SR) * np.exp(-t * 20) * np.minimum(1, t / 0.004)
        return x * 0.35
    if name == "subscribe":
        x = np.zeros(int(0.5 * SR))
        put(x, tone(1800, 0.05, decay=90), 0, 0.5)                 # click
        put(x, tone(880, 0.35, decay=9), 0.06, 0.28)               # chhoti "ting"
        put(x, tone(1318.5, 0.35, decay=9), 0.13, 0.25)
        return x
    if name == "bell":
        d = 1.4
        x = (tone(1568, d, decay=3.2, harm=(1, 2.4, 4.1), amps=(1, .4, .2)) + tone(1046.5, d, decay=3.6, harm=(1, 2.7), amps=(.7, .3)))
        y = np.zeros(int(1.8 * SR)); put(y, x, 0, 0.3); put(y, x, 0.38, 0.22); put(y, x, 0.76, 0.16)
        return reverb(y, rt=1.0, mix=0.2)
    if name in ("hype", "surprise"):
        d = 0.65
        t = tt(d)
        w = np.diff(noise(d, 4), prepend=0) * np.sin(np.pi * t / d) ** 2 * 0.6
        x = w.copy()
        for k, n in enumerate((84, 88, 91, 96)):
            put(x, tone(midi(n), 0.3, decay=12), 0.28 + k * 0.06, 0.22 * 3)
        return x / (np.abs(x).max() + 1e-9) * 0.45
    return np.zeros(10)


def intro_sfx():
    rng = np.random.default_rng(11)
    out = np.zeros(int((INTRO_S + 0.8) * SR))
    for t0 in (0.05, 0.24, 0.41, 0.53, 0.9, 1.12, 1.31):
        d = rng.uniform(0.03, 0.09)
        raw = rng.standard_normal(int(d * SR))
        hold = int(rng.integers(4, 40))
        crush = np.repeat(raw[::hold], hold)[:len(raw)] * 0.3
        put(out, crush, t0)
        sq = np.sign(np.sin(2 * np.pi * float(rng.choice([220, 440, 660, 880])) * tt(d))) * 0.12
        put(out, sq, t0)
    t = tt(0.65)
    sweep = np.sin(2 * np.pi * np.cumsum(200 * 8 ** (t / 0.65)) / SR) * (t / 0.65) * 0.16
    put(out, sweep, 0.9)
    put(out, sfx("scary")[:int(2.2 * SR)], 1.55, 0.7)
    return out


KEY_STYLES = ["iphone", "mech", "thock", "bubble", "typewriter", "glass"]     # option me naam ya number (1-6) chalta hai


def _hp(x):                                  # halka high-pass (tez "tak" wali awaaz)
    return np.diff(x, prepend=0)


def _bp(x):                                  # sirf mid-high "tak" (hiss kam)
    return np.convolve(np.diff(x, prepend=0), np.ones(4) / 4, mode="same")


def _lp(x, n):                               # halka low-pass (dabi hui "thock" wali awaaz)
    return np.convolve(x, np.ones(n) / n, mode="same")


def _key(style, rng):
    if style == "iphone":                    # iPhone keyboard jaisa chhota, saaf, narm "tock"
        t = tt(0.05); f = rng.uniform(330, 420)
        v = (np.sin(2 * np.pi * f * t) * np.exp(-t * 140) * 0.9
             + _bp(rng.standard_normal(len(t))) * np.exp(-t * 600) * 0.45
             + np.sin(2 * np.pi * f * 2.3 * t) * np.exp(-t * 260) * 0.35)
    elif style == "mech":                    # mechanical keyboard: "click-clack"
        t = tt(0.09); v = np.zeros(len(t))
        v += (_bp(rng.standard_normal(len(t))) * np.exp(-t * 480) * 0.9 + np.sin(2 * np.pi * rng.uniform(2400, 2900) * t) * np.exp(-t * 800) * 0.30)
        s2 = int(0.012 * SR); tb = t[:len(t) - s2]
        v[s2:] += np.sin(2 * np.pi * rng.uniform(190, 250) * tb) * np.exp(-tb * 85) * 0.9 + _lp(rng.standard_normal(len(tb)), 6) * np.exp(-tb * 220) * 0.6
    elif style == "thock":                   # gehri, creamy "thock"
        t = tt(0.10); f = 190 * np.exp(-t * 9) + rng.uniform(105, 125)
        v = (np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 48) * 1.0
             + _lp(rng.standard_normal(len(t)), 22) * np.exp(-t * 180) * 1.2
             + np.sin(2 * np.pi * rng.uniform(1800, 2300) * t) * np.exp(-t * 800) * 0.12)
    elif style == "bubble":                  # satisfying "bloop/pop"
        t = tt(0.10); f = rng.uniform(340, 420) + rng.uniform(480, 600) * np.exp(-t * 62)
        v = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 42) * np.minimum(1, t / 0.002) + np.sin(2 * np.pi * np.cumsum(2 * f) / SR) * np.exp(-t * 90) * 0.18
    elif style == "typewriter":              # purana typewriter: dhatu ki chot + halki ghanti
        t = tt(0.14)
        v = (_bp(rng.standard_normal(len(t))) * np.exp(-t * 300) * 0.8
             + (np.sin(2 * np.pi * 1450 * t) * np.exp(-t * 95) + np.sin(2 * np.pi * 2210 * t) * np.exp(-t * 140) * 0.7
                + np.sin(2 * np.pi * 3320 * t) * np.exp(-t * 190) * 0.4) * 0.28
             + np.sin(2 * np.pi * rng.uniform(88, 104) * t) * np.exp(-t * 65) * 1.0)
    else:                                    # glass: saaf, shishe jaisa tap (ASMR type)
        t = tt(0.14); f = rng.uniform(2300, 3100)
        v = (_bp(rng.standard_normal(len(t))) * np.exp(-t * 800) * 0.3
             + np.sin(2 * np.pi * f * t) * np.exp(-t * 75) * 0.8 + np.sin(2 * np.pi * f * 1.51 * t) * np.exp(-t * 115) * 0.35
             + np.sin(2 * np.pi * 520 * t) * np.exp(-t * 120) * 0.3)
    v = v / (np.sqrt((v ** 2).mean()) + 1e-9) * 0.11            # sab styles ek jitne loud
    v = v / max(1.0, np.abs(v).max() / 0.7)                       # peak 0.7 se upar nahi
    return v * rng.uniform(0.88, 1.0)


def norm_style(k):
    k = str(k).lower().strip()
    if k.isdigit() and 1 <= int(k) <= len(KEY_STYLES):
        return KEY_STYLES[int(k) - 1]
    if k in KEY_STYLES:
        return k
    print(f"(keys='{k}' nahi mila, 'iphone' use kar raha hoon. Options: {', '.join(KEY_STYLES)} ya 1-6)")
    return "iphone"


def key_variants(style, n=8, seed=7):
    rng = np.random.default_rng(seed)
    return [_key(style, rng) for _ in range(n)]


def bgm_track(b, seconds, intro_s):
    """Apni music file: start second se kaat kar, loop karke, fade-in/out ke saath video ki lambai tak."""
    raw = subprocess.run(["ffmpeg", "-loglevel", "error", "-ss", str(b["start"]), "-i", b["path"],
                          "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"], capture_output=True).stdout
    x = np.frombuffer(raw, dtype="<f4").astype(float)
    n = int(seconds * SR)
    if len(x) < SR:
        print("(bgm file se audio nahi mila)")
        return np.zeros(n)
    cf = int(0.4 * SR)
    y = x.copy()
    while len(y) < n:                         # chhoti file ho to loop, joint par crossfade
        if len(x) > 2 * cf:
            a = y[-cf:] * np.cos(np.linspace(0, np.pi / 2, cf)); c = x[:cf] * np.sin(np.linspace(0, np.pi / 2, cf))
            y = np.concatenate([y[:-cf], a + c, x[cf:]])
        else:
            y = np.concatenate([y, x])
    y = y[:n] / (np.abs(y[:n]).max() + 1e-9)
    t = np.arange(n) / SR
    fade = np.interp(t, [0, intro_s, intro_s + 1.5, max(seconds - 3.0, intro_s + 1.5), seconds], [0, 0, 1, 1, 0])
    return y * fade * b["vol"]


def make_audio(clicks_s, events, music_tl, seconds, intro_s, path, vol_click, vol_sfx, vol_music, use_intro, keys="iphone", bgm=None):
    out = np.zeros(int(seconds * SR))
    rng = np.random.default_rng(7)
    variants = key_variants(norm_style(keys))
    for c in clicks_s:
        put(out, variants[int(rng.integers(0, 8))], c, vol_click)
    if vol_sfx > 0:
        cache = {}
        for tm, name in events:
            if name not in cache:
                cache[name] = sfx(name)
            put(out, cache[name], tm, vol_sfx)
        if use_intro:
            put(out, intro_sfx(), 0.0, vol_sfx)
    if bgm:
        out += bgm_track(bgm, seconds, intro_s if use_intro else 0.0)
    elif vol_music > 0:
        out += music_track(music_tl, seconds, intro_s if use_intro else 0.0, vol_music)
    peak = np.abs(out).max()
    if peak > 0.95:
        out *= 0.95 / peak
    pcm = (np.clip(out, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


# ================================================================= INTRO (frames)
INTRO_HTML = """<!doctype html><meta charset=utf-8><style>
html,body{margin:0;height:100%%;background:#04060a;overflow:hidden}
body{display:flex;align-items:center;justify-content:center;flex-direction:column;
 background:radial-gradient(ellipse at center,#0b1018 0%%,#04060a 70%%)}
.scan{position:fixed;inset:0;background:repeating-linear-gradient(0deg,rgba(255,255,255,.035) 0 2px,transparent 2px 5px);pointer-events:none}
.w{position:relative;font:800 150px/1 'Roboto Mono','DejaVu Sans Mono',monospace;letter-spacing:.06em;text-transform:uppercase;
 white-space:nowrap;animation:flick %(d)ss steps(1,end) both}
.w span{display:block}
.l1,.l2{position:absolute;left:0;top:0}
.l0{color:#fff}
.l1{color:#00f0ff;mix-blend-mode:screen;animation:g1 %(d)ss steps(1,end) both}
.l2{color:#ff2a6d;mix-blend-mode:screen;animation:g2 %(d)ss steps(1,end) both}
.bar{margin-top:46px;height:6px;background:linear-gradient(90deg,#00f0ff,#ff2a6d);box-shadow:0 0 24px #00f0ff88;
 animation:bar %(d)ss linear both}
.fade{position:fixed;inset:0;background:#000;animation:fade %(d)ss linear both}
@keyframes flick{0%%{opacity:0}2%%{opacity:1}7%%{opacity:0}9%%{opacity:1}15%%{opacity:.2}17%%{opacity:1}30%%{opacity:.6}32%%{opacity:1}100%%{opacity:1}}
@keyframes g1{0%%{transform:translate(-18px,0);clip-path:inset(10%% 0 62%% 0)}6%%{transform:translate(14px,-4px);clip-path:inset(55%% 0 20%% 0)}
 12%%{transform:translate(-9px,3px);clip-path:inset(30%% 0 45%% 0)}19%%{transform:translate(22px,0);clip-path:inset(5%% 0 80%% 0)}
 27%%{transform:translate(-12px,0);clip-path:inset(60%% 0 10%% 0)}34%%{transform:translate(8px,2px);clip-path:inset(20%% 0 55%% 0)}
 42%%{transform:translate(-5px,0);clip-path:inset(40%% 0 40%% 0)}50%%{transform:translate(0,0);clip-path:inset(0 0 100%% 0)}100%%{transform:translate(0,0);clip-path:inset(0 0 100%% 0)}}
@keyframes g2{0%%{transform:translate(16px,2px);clip-path:inset(45%% 0 30%% 0)}6%%{transform:translate(-20px,0);clip-path:inset(8%% 0 70%% 0)}
 12%%{transform:translate(11px,-3px);clip-path:inset(62%% 0 8%% 0)}19%%{transform:translate(-14px,0);clip-path:inset(25%% 0 50%% 0)}
 27%%{transform:translate(19px,0);clip-path:inset(70%% 0 5%% 0)}34%%{transform:translate(-7px,2px);clip-path:inset(12%% 0 66%% 0)}
 42%%{transform:translate(6px,0);clip-path:inset(35%% 0 42%% 0)}50%%{transform:translate(0,0);clip-path:inset(0 0 100%% 0)}100%%{transform:translate(0,0);clip-path:inset(0 0 100%% 0)}}
@keyframes bar{0%%{width:0}20%%{width:0}60%%{width:620px}100%%{width:620px}}
@keyframes fade{0%%{opacity:0}88%%{opacity:0}100%%{opacity:1}}
</style><div class=scan></div>
<div class=w><span class=l0>@@NAME@@</span><span class=l1>@@NAME@@</span><span class=l2>@@NAME@@</span></div>
<div class=bar></div><div class=fade></div>"""


def render_intro(browser, ff, fps, dsf):
    page = browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=dsf).new_page()
    page.set_content((INTRO_HTML % {"d": INTRO_S}).replace("@@NAME@@", BRAND))
    page.evaluate("document.fonts.ready.then(()=>1)")
    n = int(round(INTRO_S * fps))
    for k in range(n):
        page.evaluate("T=>document.getAnimations().forEach(a=>{a.pause();a.currentTime=T})", k * 1000.0 / fps)
        ff.stdin.write(page.screenshot(type="jpeg", quality=95))
    page.close()
    return n


# ================================================================= RENDER
def start_ffmpeg(out, fps, crf, preset):
    return subprocess.Popen([
        "ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(fps), "-c:v", "mjpeg", "-i", "-",
        "-vf", "scale=in_range=full:out_range=tv:out_color_matrix=bt709:flags=lanczos,format=yuv420p",
        "-c:v", "libx264", "-preset", preset, "-crf", str(crf), "-r", str(fps),
        "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709", "-color_range", "tv",
        "-movflags", "+faststart", str(out)], stdin=subprocess.PIPE)


def open_page(b, cfg):
    """Page kholta hai, script bharta hai, virtual clock rokta hai aur play() shuru karta hai."""
    page = b.new_context(viewport={"width": W, "height": H}, device_scale_factor=cfg["dsf"]).new_page()
    page.add_init_script(INIT_JS)
    page.clock.install(time=0)
    page.goto(find_html(cfg["html"]).as_uri())
    page.add_style_tag(content=PAGE_CSS % cfg["font"])
    page.evaluate("""([src, opts, keys, brand]) => {
        document.querySelector('#src').value = src;
        for (const [k, id] of Object.entries(keys)) if (opts[k]) document.querySelector('#' + id).value = opts[k];
        document.querySelector('#zm').checked = !/^(off|no|0|false)$/i.test(opts.zoom || 'on');
        window.click = () => window.__clicks.push(performance.now());
        window.__opts = opts; window.__brand = brand;
    }""", [cfg["text"], cfg["opts"], OPT_KEYS, BRAND])
    page.add_style_tag(content=OVERLAY_CSS)
    page.evaluate(OVERLAY_JS)
    page.evaluate(LOG_JS)
    page.clock.pause_at(60000)
    t0 = page.evaluate("performance.now()")
    page.evaluate("() => { window.__p = play().then(() => { window.__done = true; }); }")
    return page, t0


def dry_run(cfg):
    """Bina screenshot ke poori timeline chalata hai: kul frames, click times aur message timings milte hain."""
    from playwright.sync_api import sync_playwright
    fps = cfg["fps"]; step = 1000.0 / fps
    with sync_playwright() as p:
        b = p.chromium.launch(args=LAUNCH_ARGS)
        page, t0 = open_page(b, cfg)
        k, prev, tail, max_frames = 0, 0, None, fps * 60 * 25
        while True:
            done = page.evaluate("window.__done")
            k += 1
            if done and tail is None:
                tail = k + fps
            if (tail is not None and k >= tail) or k >= max_frames:
                break
            target = round(k * step)
            page.clock.run_for(target - prev); prev = target
        clicks = [c - t0 for c in page.evaluate("window.__clicks")]
        log = page.evaluate("window.__log")
        b.close()
    return k, t0, clicks, log


def segment_task(t):
    """Ek worker: video ka ek hissa (frames f0..f1) render karke apni alag mp4 me daalta hai."""
    from playwright.sync_api import sync_playwright
    fps = t["fps"]; step = 1000.0 / fps
    ff = start_ffmpeg(t["out"], fps, t["crf"], t["preset"])
    with sync_playwright() as p:
        b = p.chromium.launch(args=LAUNCH_ARGS)
        if t["kind"] == "intro":
            render_intro(b, ff, fps, t["dsf"])
        else:
            page, _ = open_page(b, t)
            prev, f0, f1, t_start = 0, t["f0"], t["f1"], time.time()
            for k in range(f1):
                # animations ko har frame sync karna zaroori hai (screenshot na bhi lena ho), warna transitions bigad jaate hain
                page.evaluate("([T, s]) => window.__sync(T, s)", [k * step, step])
                if k >= f0:
                    ff.stdin.write(page.screenshot(type="jpeg", quality=95))
                    n = k - f0 + 1
                    if n % (fps * 5) == 0:
                        print(f"[{t['name']}] part {t['idx']}: {n}/{f1 - f0} frames ({n/(time.time()-t_start):.1f} f/s)", flush=True)
                if k + 1 < f1:
                    target = round((k + 1) * step)
                    page.clock.run_for(target - prev); prev = target
        b.close()
    ff.stdin.close(); ff.wait()
    if ff.returncode:
        sys.exit("ffmpeg fail ho gaya")
    return t["out"]


def find_bgm(opts):
    """# bgm=song.mp3  ->  repo ke music/ folder (ya root) me se apni music file."""
    name = opts.get("bgm")
    if not name or str(name).lower() in ("off", "no", "0", "false"):
        return None
    for p in (HERE / "music" / name, HERE / name):
        if p.exists():
            return dict(path=str(p), start=float(opts.get("bgm_start", 0)), vol=float(opts.get("bgm_vol", 0.12)))
    print(f"(bgm '{name}' nahi mili - music/ folder me upload karo. Abhi built-in music use ho raha hai)")
    return None


def settings(script, a):
    text, opts, moods = parse_script(script)
    if not text:
        sys.exit(f"{script}: script khali hai")
    off = lambda k, d="on": str(opts.get(k, d)).lower() in ("off", "no", "0", "false")
    S = dict(
        moods=moods, name=Path(script).stem, use_intro=not off("intro", "off"),       # intro default band
        keys=norm_style(opts.get("keys", "iphone")),
        vol_click=0.0 if off("click") else a.volume * (1.0 if str(opts.get("click", "on")).lower() == "on" else float(opts["click"])),
        vol_music=0.0 if off("music") else (0.12 if str(opts.get("music", "on")).lower() == "on" else float(opts["music"])),
        vol_sfx=0.0 if off("sfx") else (1.0 if str(opts.get("sfx", "on")).lower() == "on" else float(opts["sfx"])),
        want_shorts=not off("shorts", "off"), bgm=find_bgm(opts))                      # shorts default band
    html = "Gemini.html" if str(opts.get("app", "")).lower() == "gemini" else a.html          # "# app=gemini" se Gemini look
    cfg = dict(text=text, opts=opts, html=html, font=a.font, dsf=a.dsf, fps=a.fps, crf=a.crf,
               preset=a.preset, name=S["name"])
    return S, cfg


def render_range(cfg, S, plan, f0, f1, with_intro, workers, out_dir, tag):
    """Frames f0..f1 (aur chaaho to intro) render karke ek video-only mp4 banata hai (workers ek saath)."""
    name = cfg["name"]; out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    n = f1 - f0
    workers = max(1, min(workers, n))
    bounds = [f0 + round(i * n / workers) for i in range(workers + 1)]
    tasks = []
    if with_intro:
        tasks.append(dict(cfg, kind="intro", idx=-1, out=str(out_dir / f"{name}.sub_{tag}_intro.mp4")))
    for i in range(workers):
        tasks.append(dict(cfg, kind="seg", idx=i, f0=bounds[i], f1=bounds[i + 1], total=plan["total"],
                          out=str(out_dir / f"{name}.sub_{tag}_{i:02d}.mp4")))
    print(f"[{name}] frames {f0}-{f1}: {workers} worker ek saath", flush=True)
    if len(tasks) == 1:
        parts = [segment_task(tasks[0])]
    else:
        with multiprocessing.get_context("spawn").Pool(min(workers, len(tasks))) as pool:
            parts = pool.map(segment_task, tasks, chunksize=1)
    return concat_videos(parts, out_dir / f"{name}.part_{tag}.mp4", delete=True)


def concat_videos(parts, out_path, delete=False):
    out_path = Path(out_path)
    lst = out_path.with_suffix(".txt")
    lst.write_text("".join(f"file '{Path(p).resolve()}'\n" for p in parts))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst),
                    "-c", "copy", str(out_path)], check=True)
    lst.unlink()
    if delete:
        for p in parts:
            Path(p).unlink()
    return str(out_path)


def finish(cfg, S, plan, video_path, out_dir):
    """Audio banata hai (clicks, sfx, music), video ke saath jodta hai, chaaho to Shorts bhi."""
    name, fps, k = cfg["name"], cfg["fps"], plan["total"]
    out_dir = Path(out_dir)
    tmp_audio, final = out_dir / f"{name}.wav", out_dir / f"{name}.mp4"
    n_intro = int(round(INTRO_S * fps)) if S["use_intro"] else 0
    intro_s = n_intro / fps
    t0, events, music_tl = plan["t0"], [], []
    for e in plan["log"]:
        if e.get("e") is None:
            continue
        s = (e["s"] - t0) / 1000 + intro_s
        en = (e["e"] - t0) / 1000 + intro_s
        if e["n"] == "cmdTurn":                           # intro / caption / end card ki awaaz
            c = e.get("c")
            if c == "intro":
                events += [(s + 0.02, "whoosh"), (s + 0.4, "hit")]
            elif c in ("caption", "level"):
                events.append((s + 0.02, "pop2"))
            elif c == "end":
                events += [(s + 1.5, "subscribe"), (s + 1.85, "bell")]
            continue
        user = e["n"] == "userTurn"
        t_ev = (en - 0.15) if user else (s + e["th"] / 1000)
        events.append((t_ev, "send" if user else "recv"))
        mood = S["moods"].get(e["k"])
        if mood:
            if mood != "calm":
                events.append((t_ev + 0.04, mood))
            music_tl.append((s + (0.9 if user else 0.0), MUSIC_OF[mood]))
    clicks_s = [c / 1000 + intro_s for c in plan["clicks"]]      # plan me clicks pehle se video-time (ms) me hain
    seconds = (n_intro + k) / fps
    print(f"[{name}] {len(clicks_s)} clicks, {len(events)} sfx, moods: {sorted(set(m for _, m in music_tl)) or ['calm']}")
    make_audio(clicks_s, events, music_tl, seconds, intro_s, tmp_audio, S["vol_click"], S["vol_sfx"], S["vol_music"], S["use_intro"], S["keys"], S["bgm"])
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video_path), "-i", str(tmp_audio),
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2", "-shortest",
                    "-movflags", "+faststart", str(final)], check=True)
    Path(video_path).unlink(); tmp_audio.unlink()
    print(f"[{name}] DONE  {seconds:.1f}s, {final.stat().st_size/1e6:.0f} MB -> {final}")
    if S["want_shorts"]:
        sh = out_dir / f"{name}_shorts.mp4"
        vf = ("[0:v]split[a][b];[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,"
              "boxblur=40:5,eq=brightness=-0.18[bg];[b]scale=1080:-2[fg];[bg][fg]overlay=(W-w)/2:(H-h)/2,format=yuv420p")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(final), "-filter_complex", vf,
                        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-c:a", "copy",
                        "-movflags", "+faststart", str(sh)], check=True)
        print(f"[{name}] SHORTS -> {sh}" + ("" if seconds <= 180 else "  (dhyan: Shorts 3 minute se chhoti honi chahiye)"))


def make_plan(cfg):
    t = time.time()
    total, t0, clicks, log = dry_run(cfg)
    print(f"[{cfg['name']}] timeline ready: {total/cfg['fps']:.1f}s = {total} frames ({time.time()-t:.0f}s)", flush=True)
    return dict(total=total, t0=t0, clicks=clicks, log=log, fps=cfg["fps"])


def make_key_samples(out_dir):
    """Har style ka ~4 second ka sample (typing + send + reply) aur ek sab-ek-saath file banata hai."""
    out_dir = Path(out_dir); out_dir.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(3)
    t, clicks = 0.4, []
    for ch in "Hey ChatGPT, tell me a joke":          # insaani typing jaisa thoda upar-neeche gap
        if ch != " ":
            clicks.append(t)
        t += float(rng.uniform(0.065, 0.115)) * (2.2 if ch == " " else 1)
    seconds = t + 1.6
    for i, st in enumerate(KEY_STYLES, 1):
        wav = out_dir / f"{i}_{st}.wav"
        make_audio(clicks, [(t + 0.2, "send"), (t + 0.75, "recv")], [], seconds, 0, wav, 1.0, 1.0, 0.0, False, st)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-ac", "2", "-b:a", "192k",
                        str(out_dir / f"{i}_{st}.mp3")], check=True)
    lst = out_dir / "all.txt"
    gap = out_dir / "gap.wav"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", "1.2",
                    str(gap)], check=True)
    lst.write_text("".join(f"file '{(out_dir / f'{i}_{st}.wav').resolve()}'\nfile '{gap.resolve()}'\n"
                           for i, st in enumerate(KEY_STYLES, 1)))
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-ac", "2",
                    "-b:a", "192k", str(out_dir / "all_6_in_order.mp3")], check=True)
    for p in list(out_dir.glob("*.wav")) + [lst]:
        p.unlink()
    print("samples ban gaye:", sorted(x.name for x in out_dir.iterdir()))


def plan_path(plan_dir, name):
    return Path(plan_dir) / f"{name}.plan.json"


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script", nargs="?"); ap.add_argument("--out", default="out")
    ap.add_argument("--sample-keys", metavar="DIR", help="6 typing-sound styles ke sunne wale sample banao")
    ap.add_argument("--fps", type=int, default=int(os.environ.get("FPS", 30)))
    ap.add_argument("--crf", type=int, default=15); ap.add_argument("--preset", default="veryfast")
    ap.add_argument("--workers", type=int, default=int(os.environ.get("WORKERS", min(os.cpu_count() or 1, 4))),
                    help="ek machine par kitne hisse ek saath render hon")
    ap.add_argument("--volume", type=float, default=1.0, help="typing click volume")
    ap.add_argument("--font", default='Roboto,"Noto Sans",EMO,sans-serif')
    ap.add_argument("--html", default="ChatGPT.html")
    ap.add_argument("--dsf", type=float, default=2, help="2 = 4K (test ke liye 0.5)")
    # --- kai GitHub machines par baantne ke modes (plan -> part -> merge)
    ap.add_argument("--plan", metavar="DIR", help="sirf timeline banao aur DIR me plan.json likho")
    ap.add_argument("--part", type=int, help="plan ka ye hissa render karo")
    ap.add_argument("--merge", action="store_true", help="saare parts jodkar audio ke saath final video banao")
    ap.add_argument("--plan-dir", default="plan"); ap.add_argument("--parts-dir", default="parts")
    ap.add_argument("--frames-per-part", type=int, default=1800, help="ek machine ko kitne frames milen")
    a = ap.parse_args()

    if a.sample_keys:
        make_key_samples(a.sample_keys)
        sys.exit(0)
    if not a.script:
        sys.exit("script ka path do, jaise: python3 render.py scripts/video1.txt")
    S, cfg = settings(a.script, a)
    name = cfg["name"]
    if a.plan:                                                     # step 1
        plan = make_plan(cfg)
        parts = max(1, min(8, math.ceil(plan["total"] / a.frames_per_part)))
        plan["parts"] = parts
        Path(a.plan).mkdir(parents=True, exist_ok=True)
        plan_path(a.plan, name).write_text(json.dumps(plan))
        print(f"[{name}] {parts} part(s) banenge")
        if os.environ.get("GITHUB_OUTPUT"):
            with open(os.environ["GITHUB_OUTPUT"], "a") as o:
                o.write("parts=" + json.dumps(list(range(parts))) + "\n")
    elif a.part is not None:                                       # step 2 (har machine par ek)
        plan = json.loads(plan_path(a.plan_dir, name).read_text())
        P, i = plan["parts"], a.part
        f0, f1 = round(i * plan["total"] / P), round((i + 1) * plan["total"] / P)
        render_range(cfg, S, plan, f0, f1, S["use_intro"] and i == 0, a.workers, a.out, f"{i:02d}")
    elif a.merge:                                                  # step 3
        plan = json.loads(plan_path(a.plan_dir, name).read_text())
        files = sorted(Path(a.parts_dir).glob(f"{name}.part_*.mp4"))
        if len(files) != plan["parts"]:
            sys.exit(f"{len(files)} part mile, {plan['parts']} chahiye the")
        Path(a.out).mkdir(parents=True, exist_ok=True)
        video = concat_videos(files, Path(a.out) / f"{name}.noaudio.mp4")
        finish(cfg, S, plan, video, a.out)
    else:                                                          # akela mode (ek hi machine par sab)
        plan = make_plan(cfg)
        video = render_range(cfg, S, plan, 0, plan["total"], S["use_intro"], a.workers, a.out, "all")
        finish(cfg, S, plan, video, a.out)
