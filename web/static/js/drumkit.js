/*
 * Maqamatic percussion kit: darbuka strokes (dum, tak, ka) and riq-style
 * jingles, synthesised from the vibration modes of a drum head.
 *
 * Each stroke is rendered once, at audio start-up, into sample buffers
 * that the player triggers per hit. Unlike one-voice synths, buffers let
 * hits overlap and ring out, and several variants per stroke keep repeated
 * strokes from sounding machine-identical.
 *
 * Plain JavaScript with no dependencies: render() returns a Float32Array.
 */
(function (global) {
    'use strict';

    // Mode frequencies of an ideal circular membrane relative to its
    // fundamental (Bessel zeros: modes 01, 11, 21, 02, 31, 12, 41, 22, 03,
    // 51, 32, 61). A centre strike excites mostly the low ones; an edge
    // strike the higher ones.
    const MEMBRANE = [1.000, 1.594, 2.136, 2.296, 2.653, 2.918, 3.156, 3.501,
                      3.600, 3.652, 4.060, 4.154];

    // Head modes as [frequency Hz, amplitude, decay time constant s];
    // higher modes die away faster.
    function head(f0, amps, decay) {
        return amps.map((a, i) => [f0 * MEMBRANE[i], a, decay * Math.pow(0.86, i)]);
    }

    const STROKES = {
        // Centre of the head: the air in the goblet booms (around 90 Hz)
        // under the head's low modes, with a soft, padded thump.
        // The boom's octave keeps it audible on laptop and phone speakers,
        // which cannot reproduce 90 Hz itself.
        dum: {
            length: 0.95,
            pitchDrop: 0.14, dropTime: 0.03,   // the strike briefly tightens the head
            modes: [[88, 1.0, 0.17], [176, 0.55, 0.11], [264, 0.20, 0.07]].concat(
                head(205, [0.70, 0.42, 0.28, 0.18, 0.12, 0.08, 0.05], 0.09)),
            noise: { filter: 'lowpass', freq: 1100, q: 0.7, amp: 0.55, decay: 0.010 },
            drive: 1.7,
        },
        // Fingers snapping on the rim: a bright head and a sharp slap of
        // skin. The ring above the head is kept short and soft, so the
        // stroke stays skin-like rather than metallic (owner feedback).
        tak: {
            length: 0.45,
            pitchDrop: 0.03, dropTime: 0.01,
            modes: [[88, 0.10, 0.05]].concat(
                head(230, [0.08, 0.20, 0.28, 0.32, 0.32, 0.30, 0.28, 0.25, 0.22, 0.20, 0.17, 0.15], 0.075),
                [[1480, 0.24, 0.035], [2210, 0.18, 0.028], [3050, 0.10, 0.022]]),
            noise: { filter: 'bandpass', freq: 2600, q: 0.6, amp: 1.1, decay: 0.007 },
            drive: 1.3,
        },
        // The other hand's lighter rim stroke: shorter and a little darker.
        ka: {
            length: 0.35,
            pitchDrop: 0.03, dropTime: 0.01,
            modes: head(225, [0.07, 0.18, 0.25, 0.28, 0.27, 0.25, 0.22, 0.19, 0.16, 0.14], 0.055).concat(
                [[1450, 0.20, 0.03], [2170, 0.14, 0.025], [2980, 0.07, 0.02]]),
            noise: { filter: 'bandpass', freq: 2100, q: 0.6, amp: 0.95, decay: 0.006 },
            drive: 1.3,
        },
        // Riq jingles (zills): inharmonic metal partials, struck several
        // times in quick succession as the pairs of zills collide.
        jingle: {
            length: 0.4,
            metal: { count: 12, low: 3800, high: 11000, decay: [0.05, 0.15] },
            strikes: [[0, 1.0], [0.004, 0.6], [0.011, 0.4], [0.019, 0.2]],  // [offset s, amplitude], jittered
            noise: { filter: 'highpass', freq: 6000, q: 0.7, amp: 0.4, decay: 0.003 },
            drive: 1.0,
        },
    };

    // Level of each stroke in the mix, in dB (buffers are peak-normalised).
    const LEVELS = { dum: 0, tak: -3, ka: -7, jingle: -27 };
    const VARIANTS = 4;

    // Small deterministic generator, so a variant always sounds the same.
    function rng(seed) {
        let s = seed >>> 0;
        return () => {
            s = (Math.imul(s, 1664525) + 1013904223) >>> 0;
            return s / 4294967296;
        };
    }

    // RBJ biquad filter, in place. Bandpass has 0 dB peak gain.
    function biquad(x, sr, type, freq, q) {
        const w = 2 * Math.PI * freq / sr, cos = Math.cos(w), alpha = Math.sin(w) / (2 * q);
        let b0, b1, b2;
        if (type === 'lowpass') { b0 = (1 - cos) / 2; b1 = 1 - cos; b2 = b0; }
        else if (type === 'highpass') { b0 = (1 + cos) / 2; b1 = -(1 + cos); b2 = b0; }
        else { b0 = alpha; b1 = 0; b2 = -alpha; }
        const a0 = 1 + alpha, a1 = -2 * cos, a2 = 1 - alpha;
        let x1 = 0, x2 = 0, y1 = 0, y2 = 0;
        for (let i = 0; i < x.length; i++) {
            const y = (b0 * x[i] + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2) / a0;
            x2 = x1; x1 = x[i]; y2 = y1; y1 = y;
            x[i] = y;
        }
        return x;
    }

    // Exponentially decaying sine, added into out from sample `start`.
    function addMode(out, sr, start, freq, amp, decay, phase0, drop, dropTime) {
        const k = Math.exp(-1 / (decay * sr));
        const kb = Math.exp(-1 / (dropTime * sr));
        const end = Math.min(out.length, start + Math.ceil(decay * 9 * sr));  // to about -78 dB
        const step = 2 * Math.PI * freq / sr;
        let env = amp, phase = phase0, bend = drop, i = start;
        // While the pitch is still settling, follow the bend sample by sample...
        for (; i < end && bend > 1e-6; i++) {
            phase += step * (1 + bend);
            out[i] += env * Math.sin(phase);
            env *= k;
            bend *= kb;
        }
        // ...then a steady sine: s[n+1] = 2cos(w)·s[n] − s[n−1].
        const c2 = 2 * Math.cos(step);
        let prev = Math.sin(phase), cur = Math.sin(phase + step);
        for (; i < end; i++) {
            out[i] += env * cur;
            const next = c2 * cur - prev;
            prev = cur; cur = next;
            env *= k;
        }
    }

    function addNoise(out, sr, start, z, r) {
        const n = Math.min(out.length - start, Math.ceil(z.decay * 10 * sr));
        const buf = new Float32Array(n);
        const k = Math.exp(-1 / (z.decay * sr));
        let env = z.amp;
        for (let i = 0; i < n; i++) { buf[i] = (r() * 2 - 1) * env; env *= k; }
        biquad(buf, sr, z.filter, z.freq, z.q);
        for (let i = 0; i < n; i++) out[start + i] += buf[i];
    }

    function render(name, sampleRate, variant) {
        const s = STROKES[name];
        if (!s) throw new Error('Unknown stroke: ' + name);
        const seed = Array.from(name).reduce((h, c) => Math.imul(h, 31) + c.charCodeAt(0), 7);
        const r = rng(seed * 7919 + (variant || 0) * 104729 + 1);
        const sr = sampleRate;
        const out = new Float32Array(Math.ceil(s.length * sr));

        if (s.modes) {
            const tuning = 1 + (r() - 0.5) * 0.03;       // each variant is tuned slightly differently
            for (const [f, a, tau] of s.modes) {
                addMode(out, sr, 0,
                        f * tuning * (1 + (r() - 0.5) * 0.01),
                        a * (0.85 + r() * 0.3),
                        tau * (0.9 + r() * 0.2),
                        0, s.pitchDrop, s.dropTime);
            }
            if (s.noise) addNoise(out, sr, 0, s.noise, r);
        } else {
            const m = s.metal;
            const partials = [];
            for (let i = 0; i < m.count; i++) {
                partials.push([m.low * Math.pow(m.high / m.low, r()), 0.3 + r() * 0.7,
                               m.decay[0] + r() * (m.decay[1] - m.decay[0])]);
            }
            for (const [offset, level] of s.strikes) {
                const start = Math.round((offset + (offset ? (r() - 0.5) * 0.003 : 0)) * sr);
                const strikeLevel = level * (0.8 + r() * 0.4);
                for (const [f, a, tau] of partials) {
                    addMode(out, sr, start, f, a * strikeLevel, tau, r() * 2 * Math.PI, 0, 1);
                }
                if (s.noise) addNoise(out, sr, start, Object.assign({}, s.noise, { amp: s.noise.amp * strikeLevel }), r);
            }
        }

        // Soft saturation for warmth and presence, then normalise to 0.9
        // and fade out the last 15 ms.
        let peak = 0;
        for (let i = 0; i < out.length; i++) peak = Math.max(peak, Math.abs(out[i]));
        const drive = s.drive, norm = peak > 0 ? 1 / peak : 1, scale = 0.9 / Math.tanh(drive);
        const fade = Math.ceil(0.015 * sr);
        for (let i = 0; i < out.length; i++) {
            out[i] = Math.tanh(drive * out[i] * norm) * scale;
            const left = out.length - 1 - i;
            if (left < fade) out[i] *= left / fade;
        }
        return out;
    }

    global.MaqamaticDrums = { STROKES, LEVELS, VARIANTS, render };
})(typeof window !== 'undefined' ? window : globalThis);
