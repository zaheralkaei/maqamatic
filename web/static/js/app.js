/**
 * Maqamatic - Arabic Maqam Generator
 * Frontend Application — Full Parameter Control
 */

// ============================================
// State Management
// ============================================

const state = {
    maqamat: [],
    iqaat: [],
    presets: {},
    parameters: {},
    currentMaqam: null,
    currentIqa: null,
    currentPreset: null,
    generatedMusicXML: null,
    fileId: null,
    osmd: null,
    isPlaying: false,
    isLooping: false,
    synth: null,
    tempo: 90,
    audioInitialized: false
};

// ============================================
// Utilities
// ============================================

/** Update numeric value badges for integer sliders (phrase length, section count, max maqamat) */
const COMPOSED_FORMS = {
    samai:  { name: "Sama'i", main: "Samā'ī Thaqīl (10/8)", k4: "Samā'ī Dārij (3/4)" },
    longa:  { name: "Longa",  main: "Fox (2/4)",             k4: "Samā'ī Dārij (3/4)" },
    bashraf:{ name: "Bashraf", main: "Maqsūm (4/4)",        k4: "Samā'ī Dārij (3/4)" },
};

function updateComposedFormIndicator() {
    const formVal = document.getElementById('select-form-type').value;
    const notice = document.getElementById('iqa-override-notice');
    const iqaSelect = document.getElementById('select-iqa');
    const iqaInfo = COMPOSED_FORMS[formVal];

    if (iqaInfo && notice) {
        notice.style.display = 'block';
        document.getElementById('iqa-override-text').textContent =
            `Iqa set by ${iqaInfo.name}: ${iqaInfo.main}, K4 in ${iqaInfo.k4}`;
        if (iqaSelect) {
            iqaSelect.style.opacity = '0.4';
            iqaSelect.style.pointerEvents = 'none';
        }
    } else if (notice) {
        notice.style.display = 'none';
        if (iqaSelect) {
            iqaSelect.style.opacity = '1';
            iqaSelect.style.pointerEvents = 'auto';
        }
    }
}

function updateNumericDisplays() {
    const map = {
        'slider-phrase-length': 'val-phrase-length',
        'slider-section-count': 'val-section-count',
        'slider-phrase-measures': 'val-phrase-measures',
        'slider-max-maqamat': 'val-max-maqamat'
    };
    Object.entries(map).forEach(([sliderId, valId]) => {
        const slider = document.getElementById(sliderId);
        const display = document.getElementById(valId);
        if (slider && display) display.textContent = slider.value;
    });
}

// ============================================
// API Functions
// ============================================

const API = {
    baseUrl: '',

    async getMaqamat() {
        const response = await fetch(`${this.baseUrl}/api/maqamat`);
        return response.json();
    },

    async getIqaat() {
        const response = await fetch(`${this.baseUrl}/api/iqaat`);
        return response.json();
    },

    async getPresets() {
        const response = await fetch(`${this.baseUrl}/api/presets`);
        return response.json();
    },

    async getParameters() {
        const response = await fetch(`${this.baseUrl}/api/parameters`);
        return response.json();
    },

    async getMaqamDetails(maqamId) {
        const response = await fetch(`${this.baseUrl}/api/maqam/${maqamId}`);
        return response.json();
    },

    async getIqaDetails(iqaId) {
        const response = await fetch(`${this.baseUrl}/api/iqa/${iqaId}`);
        return response.json();
    },

    async generate(params) {
        // Audit v3: a bare fetch() on Railway's free tier can hit
        // a cold start where the service takes 30+ seconds to
        // respond, which the browser interprets as a network
        // failure. Use AbortController with a 90s timeout so the
        // user sees a real error instead of "Failed to fetch".
        const controller = new AbortController();
        const timeout = setTimeout(() => controller.abort(), 90000);
        try {
            const response = await fetch(`${this.baseUrl}/api/generate`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params),
                signal: controller.signal
            });
            clearTimeout(timeout);
            return response.json();
        } catch (err) {
            clearTimeout(timeout);
            if (err.name === 'AbortError') {
                throw new Error('Request timed out after 90s. The service may be cold-starting — try again in a moment.');
            }
            // Browser's "Failed to fetch" is uninformative; add
            // guidance so the user knows what to try.
            throw new Error('Network error: ' + err.message + '. Check your connection and the Railway service status.');
        }
    }
};

// ============================================
// UI Functions
// ============================================

const UI = {
    populateMaqamat(maqamat) {
        const select = document.getElementById('select-maqam');
        select.innerHTML = maqamat.map(m =>
            `<option value="${m.id}">${m.name} (${m.family})</option>`
        ).join('');
        if (maqamat.length > 0) {
            select.value = 'bayati';
            this.updateMaqamPreview('bayati');
        }
    },

    populateIqaat(iqaat) {
        const select = document.getElementById('select-iqa');
        select.innerHTML = iqaat.map(i =>
            `<option value="${i.id}">${i.name} (${i.time_signature})</option>`
        ).join('');
        if (iqaat.length > 0) {
            select.value = 'maqsum';
            this.updateIqaPreview('maqsum');
        }
    },

    populatePresets(presets) {
        const grid = document.getElementById('preset-grid');
        grid.innerHTML = Object.entries(presets).map(([id, preset]) =>
            `<button class="preset-btn" data-preset="${id}" title="${preset.description}">
                ${preset.name}
            </button>`
        ).join('');
        grid.querySelectorAll('.preset-btn').forEach(btn => {
            btn.addEventListener('click', () => this.applyPreset(btn.dataset.preset));
        });
    },

    updateMaqamPreview(maqamId) {
        const maqam = state.maqamat.find(m => m.id === maqamId);
        const moodEl = document.getElementById('maqam-mood');
        if (maqam && maqam.characteristics && maqam.characteristics.mood) {
            moodEl.textContent = Array.isArray(maqam.characteristics.mood)
                ? maqam.characteristics.mood.join(', ')
                : maqam.characteristics.mood;
        } else {
            moodEl.textContent = '\u2014';
        }
        state.currentMaqam = maqamId;
    },

    updateIqaPreview(iqaId) {
        const iqa = state.iqaat.find(i => i.id === iqaId);
        const timeEl = document.getElementById('iqa-time');
        if (iqa) {
            timeEl.textContent = iqa.time_signature;
        } else {
            timeEl.textContent = '\u2014';
        }
        state.currentIqa = iqaId;
    },

    // Apply preset — set only controls that the preset defines
    applyPreset(presetId) {
        const preset = state.presets[presetId];
        if (!preset) return;
        const v = preset.values;

        const setSlider = (id, val) => {
            const el = document.getElementById(id);
            if (el && val !== undefined) el.value = val;
        };
        const setSelect = (id, val) => {
            const el = document.getElementById(id);
            if (el && val !== undefined) el.value = val;
        };

        setSlider('slider-tradition', v.tradition_vs_experimental);
        setSlider('slider-energy-level', v.energy_level);
        setSlider('slider-density', v.melodic_density);
        setSlider('slider-melodic-balance', v.melodic_balance);
        setSlider('slider-step-vs-jump', v.step_vs_jump);
        setSlider('slider-jins-adherence', v.jins_adherence);
        setSelect('select-contour-type', v.contour_type);
        setSlider('slider-phrase-length', v.phrase_length);
        setSlider('slider-repetition-amount', v.repetition_amount);
        setSelect('select-form-type', v.form_type);
        setSlider('slider-phase-mode', v.phase_mode);
        setSlider('slider-section-count', v.section_count);
        setSlider('slider-phrase-measures', v.phrase_length_measures || 1);
        setSelect('select-tension-curve', v.tension_curve);
        setSlider('slider-rhythmic-alignment', v.rhythmic_alignment);
        setSlider('slider-duration-variety', v.duration_variety);
        setSlider('slider-tempo-stability', v.tempo_stability);
        setSlider('slider-modulation-frequency', v.modulation_frequency);
        setSlider('slider-modulation-distance', v.modulation_distance);
        setSlider('slider-max-maqamat', v.max_maqamat);
        setSlider('slider-ornaments', v.ornamentation_density);
        setSlider('slider-vibrato-amount', v.vibrato_amount);
        setSlider('slider-dynamics-range', v.dynamics_range);
        setSlider('slider-pitch-gravity', v.pitch_gravity_strength);
        setSlider('slider-transition-weight', v.transition_matrix_weight);

        // Update numeric value displays
        updateNumericDisplays();
        updateComposedFormIndicator();

        document.querySelectorAll('.preset-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.preset === presetId);
        });
        state.currentPreset = presetId;
        setTimeout(() => Inspector.updateAll(), 10);
    },

    async showMaqamInfo(maqamId) {
        const panel = document.getElementById('panel-info');
        const content = document.getElementById('info-content');
        try {
            const details = await API.getMaqamDetails(maqamId);
            content.innerHTML = this.renderMaqamInfo(details);
            panel.classList.add('visible');
        } catch (error) {
            console.error('Error fetching maqam details:', error);
        }
    },

    async showIqaInfo(iqaId) {
        const panel = document.getElementById('panel-info');
        const content = document.getElementById('info-content');
        try {
            const details = await API.getIqaDetails(iqaId);
            content.innerHTML = this.renderIqaInfo(details);
            panel.classList.add('visible');
        } catch (error) {
            console.error('Error fetching iqa details:', error);
        }
    },

    renderMaqamInfo(maqam) {
        const scaleNotes = maqam.scale_notes || [];
        const scaleDisplay = scaleNotes.map((note, i) => {
            const alterSymbol = note.alter === 0.5 ? '\u00BD\u266F' :
                               note.alter === -0.5 ? '\u00BD\u266D' :
                               note.alter === 1 ? '\u266F' :
                               note.alter === -1 ? '\u266D' : '';
            const isTonic = i === 0;
            return `<span class="scale-note ${isTonic ? 'tonic' : ''}">${note.step}${alterSymbol}</span>`;
        }).join('');
        const ajnas = maqam.ajnas || [];
        const ajnasList = ajnas.map(j =>
            `<li>${j.jins_id} (${j.position}, degree ${j.start_degree})</li>`
        ).join('');
        const mood = maqam.characteristics?.mood;
        const moodText = Array.isArray(mood) ? mood.join(', ') : (mood || 'Not specified');
        return `
            <div class="info-card">
                <h3>${maqam.name}</h3>
                <div class="arabic-name">\u0645\u0642\u0627\u0645 ${maqam.name}</div>
                <div class="info-section"><h4>Family</h4><p>${maqam.family}</p></div>
                <div class="info-section"><h4>Mood</h4><p>${moodText}</p></div>
                <div class="info-section"><h4>Scale</h4><div class="scale-display">${scaleDisplay}</div></div>
                ${ajnas.length > 0 ? `<div class="info-section"><h4>Ajnas (Component Tetrachords)</h4><ul>${ajnasList}</ul></div>` : ''}
                ${maqam.description ? `<div class="info-section"><h4>Description</h4><p>${maqam.description}</p></div>` : ''}
            </div>`;
    },

    renderIqaInfo(iqa) {
        const pattern = iqa.pattern || {};
        const events = pattern.events || [];
        const patternDisplay = events.filter(e => e.stroke !== 'rest').map(e => {
            const symbol = e.stroke === 'dum' ? 'D' : e.stroke === 'tak' ? 'T' : e.stroke === 'ka' ? 'k' : '-';
            return `<span class="scale-note ${e.accent >= 2 ? 'tonic' : ''}">${symbol}</span>`;
        }).join('');
        const feel = iqa.characteristics?.feel;
        const feelText = Array.isArray(feel) ? feel.join(', ') : (feel || 'Not specified');
        return `
            <div class="info-card">
                <h3>${iqa.name}</h3>
                <div class="arabic-name">\u0625\u064A\u0642\u0627\u0639 ${iqa.name}</div>
                <div class="info-section"><h4>Time Signature</h4><p>${iqa.time_signature?.display || iqa.time_signature?.beats + '/' + iqa.time_signature?.beat_type}</p></div>
                <div class="info-section"><h4>Feel</h4><p>${feelText}</p></div>
                ${patternDisplay ? `<div class="info-section"><h4>Basic Pattern</h4><div class="scale-display">${patternDisplay}</div><p style="font-size:0.75rem;color:var(--color-text-muted);margin-top:8px">D = Dum (bass), T = Tak (treble), k = ka (ghost)</p></div>` : ''}
                ${iqa.description ? `<div class="info-section"><h4>Description</h4><p>${iqa.description}</p></div>` : ''}
            </div>`;
    },

    closeInfoPanel() { document.getElementById('panel-info').classList.remove('visible'); },
    showLoading() {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('score-container').style.display = 'none';
        document.getElementById('loading-state').style.display = 'block';
    },
    showScore() {
        document.getElementById('empty-state').style.display = 'none';
        document.getElementById('loading-state').style.display = 'none';
        document.getElementById('score-container').style.display = 'block';
    },
    showEmpty() {
        document.getElementById('empty-state').style.display = 'block';
        document.getElementById('score-container').style.display = 'none';
        document.getElementById('loading-state').style.display = 'none';
    },
    enablePlayback() {
        document.getElementById('btn-play').disabled = false;
        document.getElementById('btn-stop').disabled = false;
        document.getElementById('btn-loop').disabled = false;
        document.getElementById('slider-tempo').disabled = false;
        document.getElementById('btn-download').disabled = false;
    },
    disablePlayback() {
        document.getElementById('btn-play').disabled = true;
        document.getElementById('btn-stop').disabled = true;
        document.getElementById('btn-loop').disabled = true;
        document.getElementById('slider-tempo').disabled = true;
        document.getElementById('btn-download').disabled = true;
    },
    showModal(modalId) { document.getElementById(modalId).classList.add('visible'); },
    hideModal(modalId) { document.getElementById(modalId).classList.remove('visible'); }
};

// ============================================
// Score Display (OpenSheetMusicDisplay)
// ============================================

const Score = {
    async render(musicxml) {
        const container = document.getElementById('osmd-container');
        container.innerHTML = '';
        state.osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(container, {
            autoResize: true, backend: 'svg', drawTitle: true, drawComposer: true,
            drawingParameters: 'compacttight', drawPartNames: true,
            drawMeasureNumbers: true, drawTimeSignatures: true, drawKeySignatures: true
        });
        try {
            await state.osmd.load(musicxml);
            state.osmd.EngravingRules.RenderSingleHorizontalStaffline = false;
            state.osmd.render();
            UI.showScore();
            UI.enablePlayback();
            Playback.parseNotesFromMusicXML(musicxml);
        } catch (error) {
            console.error('Error rendering score:', error);
            alert('Error rendering score: ' + error.message);
        }
    },
    zoomIn() { if (state.osmd) { state.osmd.Zoom *= 1.2; state.osmd.render(); } },
    zoomOut() { if (state.osmd) { state.osmd.Zoom *= 0.8; state.osmd.render(); } }
};

// ============================================
// Playback (Tone.js) - Improved Nay + Percussion
// ============================================

const Playback = {
    melodyNotes: [],
    percussionNotes: [],
    scheduledIds: [],
    endTimeoutId: null,

    async initAudio() {
        if (state.audioInitialized) return;

        try {
            await Tone.start();
            console.log('Audio context started');

            // ============================================
            // NAY (Arabic flute) — Enhanced signal chain:
            // Oscillators → Formant → Vibrato → Chorus → Tremolo → Reverb → Dest
            // Breath noise → breathFilter (dynamic) → Reverb → Dest
            // ============================================

            const nayReverb = new Tone.Reverb({ decay: 2.2, wet: 0.22 }).toDestination();

            // Breath-like tremolo for natural variation
            const nayTremolo = new Tone.Tremolo({
                frequency: 3.5, depth: 0.15, spread: 0, wet: 0.4
            }).connect(nayReverb);
            nayTremolo.start();

            // Gentle chorus for warmth
            const nayChorus = new Tone.Chorus({
                frequency: 1.2, delayTime: 3.5, depth: 0.25, wet: 0.15
            }).connect(nayTremolo);
            nayChorus.start();

            // Vibrato characteristic of nay
            const nayVibrato = new Tone.Vibrato({
                frequency: 5.2, depth: 0.08, wet: 0.6
            }).connect(nayChorus);

            // Formant resonance: simulates nay wooden body (~900Hz peak)
            const nayFormant = new Tone.Filter({
                frequency: 900, type: 'peaking', Q: 2.5, gain: 3
            }).connect(nayVibrato);

            // Main tone: sine wave — the pure, hollow nay core
            // portamento: subtle 35ms pitch glide simulating finger slides
            state.naySine = new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: 'sine' },
                envelope: { attack: 0.12, decay: 0.3, sustain: 0.7, release: 0.6 },
                portamento: 0.035
            }).connect(nayFormant);
            state.naySine.volume.value = -6;

            // Breath layer: filtered noise for airy quality (dynamically controlled)
            const breathFilter = new Tone.Filter({
                frequency: 2200, type: 'bandpass', Q: 1.2
            }).connect(nayReverb);
            state.nayBreath = new Tone.NoiseSynth({
                noise: { type: 'pink' },
                envelope: { attack: 0.08, decay: 0.15, sustain: 0.05, release: 0.3 }
            }).connect(breathFilter);
            state.nayBreath.volume.value = -22;
            state.breathFilter = breathFilter;  // Store for dynamic frequency control

            // Overtone 1: octave up, slightly detuned for natural beating
            state.nayOvertone = new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: 'sine' },
                envelope: { attack: 0.15, decay: 0.2, sustain: 0.3, release: 0.5 },
                portamento: 0.035
            }).connect(nayFormant);
            state.nayOvertone.volume.value = -20;

            // Overtone 2: 3rd harmonic (octave+fifth), very subtle
            state.nayOvertone2 = new Tone.PolySynth(Tone.Synth, {
                oscillator: { type: 'sine' },
                envelope: { attack: 0.18, decay: 0.25, sustain: 0.2, release: 0.4 },
                portamento: 0.035
            }).connect(nayFormant);
            state.nayOvertone2.volume.value = -28;

            // Store vibrato reference for dynamic depth
            state.nayVibratoNode = nayVibrato;
            // Store base volume for fade scheduling
            state.nayBaseVol = -6;

            // Combined nay synth wrapper
            state.synth = {
                triggerAttackRelease: (freq, duration, time) => {
                    const freqVal = typeof freq === 'string' ? Tone.Frequency(freq).toFrequency() : freq;
                    const dur = typeof duration === 'number' ? duration : Tone.Time(duration).toSeconds();

                    // Dynamic vibrato: higher register = more vibrato
                    const vibratoDepth = 0.06 + Math.min(0.08, (freqVal - 200) / 4000);
                    if (state.nayVibratoNode) {
                        state.nayVibratoNode.depth.setValueAtTime(vibratoDepth, time);
                    }

                    // Per-note attack variation: ±30ms for human-like irregularity
                    const attackVar = 0.10 + (Math.random() * 0.06 - 0.03);
                    state.naySine.set({ envelope: { attack: attackVar } });

                    // Register-dependent breath: higher notes = louder, brighter breath
                    const breathVol = -24 + Math.min(10, (freqVal - 200) / 80);
                    const breathFreq = 1800 + Math.min(2200, (freqVal - 200) * 2);
                    if (state.nayBreath) {
                        state.nayBreath.volume.setValueAtTime(breathVol, time);
                    }
                    if (state.breathFilter) {
                        state.breathFilter.frequency.setValueAtTime(breathFreq, time);
                    }

                    // Trigger all layers
                    if (state.naySine) state.naySine.triggerAttackRelease(freqVal, duration, time);
                    if (state.nayBreath) state.nayBreath.triggerAttackRelease(duration, time);
                    if (state.nayOvertone) state.nayOvertone.triggerAttackRelease(freqVal * 2.003, duration, time);
                    if (state.nayOvertone2) state.nayOvertone2.triggerAttackRelease(freqVal * 3.005, duration, time);

                    // Note-end volume fade: simulate breath running out on longer notes
                    if (dur > 0.5 && state.naySine) {
                        try {
                            const fadeStart = time + dur * 0.75;
                            const fadeEnd = time + dur * 0.95;
                            state.naySine.volume.cancelScheduledValues(fadeStart);
                            state.naySine.volume.setValueAtTime(state.nayBaseVol, fadeStart);
                            state.naySine.volume.linearRampToValueAtTime(state.nayBaseVol - 8, fadeEnd);
                            // Restore volume after note ends
                            state.naySine.volume.setValueAtTime(state.nayBaseVol, fadeEnd + 0.05);
                        } catch (e) { /* ignore scheduling conflicts */ }
                    }
                },
                releaseAll: () => {
                    if (state.naySine) state.naySine.releaseAll();
                    if (state.nayOvertone) state.nayOvertone.releaseAll();
                    if (state.nayOvertone2) state.nayOvertone2.releaseAll();
                }
            };

            // ============================================
            // PERCUSSION: Riq / Cajon — acoustic layered
            // ============================================

            const drumReverb = new Tone.Reverb({ decay: 0.6, wet: 0.12 }).toDestination();
            const drumComp = new Tone.Compressor({
                threshold: -18, ratio: 3, attack: 0.002, release: 0.15
            }).connect(drumReverb);

            // DUM (bass centre hit)
            state.dumSkin = new Tone.MembraneSynth({
                pitchDecay: 0.06, octaves: 5,
                oscillator: { type: 'sine' },
                envelope: { attack: 0.002, decay: 0.35, sustain: 0.0, release: 0.25 }
            }).connect(drumComp);
            state.dumSkin.volume.value = -2;

            const dumBodyFilter = new Tone.Filter({ frequency: 180, type: 'lowpass', rolloff: -24 }).connect(drumComp);
            state.dumBody = new Tone.NoiseSynth({
                noise: { type: 'brown' },
                envelope: { attack: 0.001, decay: 0.12, sustain: 0, release: 0.08 }
            }).connect(dumBodyFilter);
            state.dumBody.volume.value = -8;

            const dumTransientFilter = new Tone.Filter({ frequency: 800, type: 'bandpass', Q: 0.8 }).connect(drumComp);
            state.dumTransient = new Tone.NoiseSynth({
                noise: { type: 'white' },
                envelope: { attack: 0.001, decay: 0.015, sustain: 0, release: 0.01 }
            }).connect(dumTransientFilter);
            state.dumTransient.volume.value = -16;

            // TAK (edge slap)
            const takSkinFilter = new Tone.Filter({ frequency: 4500, type: 'bandpass', Q: 1.5 }).connect(drumComp);
            state.takSkin = new Tone.MembraneSynth({
                pitchDecay: 0.008, octaves: 3,
                oscillator: { type: 'triangle' },
                envelope: { attack: 0.001, decay: 0.06, sustain: 0.0, release: 0.04 }
            }).connect(takSkinFilter);
            state.takSkin.volume.value = -4;

            const takCrackFilter = new Tone.Filter({ frequency: 6000, type: 'highpass', rolloff: -12 }).connect(drumComp);
            state.takCrack = new Tone.NoiseSynth({
                noise: { type: 'white' },
                envelope: { attack: 0.001, decay: 0.025, sustain: 0, release: 0.015 }
            }).connect(takCrackFilter);
            state.takCrack.volume.value = -10;

            const jingleFilter = new Tone.Filter({ frequency: 8000, type: 'highpass', rolloff: -12 }).connect(drumComp);
            state.takJingle = new Tone.MetalSynth({
                frequency: 300,
                envelope: { attack: 0.001, decay: 0.08, release: 0.05 },
                harmonicity: 5.1, modulationIndex: 16, resonance: 5000, octaves: 1.5
            }).connect(jingleFilter);
            state.takJingle.volume.value = -22;

            // KA (ghost finger tap)
            const kaSkinFilter = new Tone.Filter({ frequency: 2000, type: 'bandpass', Q: 1 }).connect(drumComp);
            state.kaSkin = new Tone.MembraneSynth({
                pitchDecay: 0.005, octaves: 1.5,
                oscillator: { type: 'sine' },
                envelope: { attack: 0.001, decay: 0.035, sustain: 0, release: 0.025 }
            }).connect(kaSkinFilter);
            state.kaSkin.volume.value = -10;

            const kaNoiseFilter = new Tone.Filter({ frequency: 3000, type: 'bandpass', Q: 0.6 }).connect(drumComp);
            state.kaNoise = new Tone.NoiseSynth({
                noise: { type: 'pink' },
                envelope: { attack: 0.001, decay: 0.02, sustain: 0, release: 0.015 }
            }).connect(kaNoiseFilter);
            state.kaNoise.volume.value = -18;

            state.audioInitialized = true;
        } catch (error) {
            console.error('Failed to initialize audio:', error);
            throw error;
        }
    },

    parseNotesFromMusicXML(musicxml) {
        this.melodyNotes = [];
        this.percussionNotes = [];
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(musicxml, 'text/xml');
            const parts = xmlDoc.querySelectorAll('part');
            parts.forEach((part) => {
                const divisions = parseInt(part.querySelector('divisions')?.textContent) || 8;
                let currentTime = 0;
                const notes = part.querySelectorAll('note');
                notes.forEach(note => {
                    const isRest = note.querySelector('rest') !== null;
                    const isChord = note.querySelector('chord') !== null;
                    const duration = parseInt(note.querySelector('duration')?.textContent) || divisions;
                    const durationBeats = duration / divisions;
                    const ties = note.querySelectorAll('tie');
                    let hasTieStop = false;
                    let hasTieStart = false;
                    ties.forEach(tie => {
                        if (tie.getAttribute('type') === 'stop') hasTieStop = true;
                        if (tie.getAttribute('type') === 'start') hasTieStart = true;
                    });
                    const unpitched = note.querySelector('unpitched');
                    const pitch = note.querySelector('pitch');
                    if (!isRest) {
                        if (unpitched) {
                            const displayStep = unpitched.querySelector('display-step')?.textContent || 'E';
                            const displayOctave = parseInt(unpitched.querySelector('display-octave')?.textContent) || 4;
                            let strokeType = 'ka';
                            if (displayStep === 'F' && displayOctave === 4) strokeType = 'dum';
                            else if (displayStep === 'C' && displayOctave === 5) strokeType = 'tak';
                            else if (displayStep === 'E' && displayOctave === 4) strokeType = 'ka';
                            // Audit v3: read velocity/accent from the
                            // MusicXML so the audio playback gets the
                            // same dynamic shape as the visual score.
                            // MusicXML stores <velocity>1-127</velocity>
                            // and an optional <accent/> articulation.
                            const velText = note.querySelector('velocity')?.textContent;
                            const vel = velText ? parseInt(velText) : 80;
                            const hasAccent = note.querySelector('notations articulations accent') !== null;
                            const accent = hasAccent ? 1.0 : 0.6;
                            this.percussionNotes.push({
                                time: currentTime,
                                duration: durationBeats,
                                strokeType,
                                velocity: vel,
                                accent,
                            });
                        } else if (pitch) {
                            const step = pitch.querySelector('step')?.textContent || 'C';
                            const octave = parseInt(pitch.querySelector('octave')?.textContent) || 4;
                            const alterEl = pitch.querySelector('alter');
                            const alter = alterEl ? parseFloat(alterEl.textContent) : 0;
                            const freq = this.noteToFrequency(step, octave, alter);
                            if (hasTieStop && this.melodyNotes.length > 0) {
                                this.melodyNotes[this.melodyNotes.length - 1].duration += durationBeats;
                            } else {
                                this.melodyNotes.push({
                                    time: currentTime, duration: durationBeats, frequency: freq,
                                    noteName: `${step}${alter === -0.5 ? 'half-flat' : alter === 0.5 ? 'half-sharp' : alter === -1 ? 'b' : alter === 1 ? '#' : ''}${octave}`
                                });
                            }
                        }
                    }
                    if (!isChord) currentTime += durationBeats;
                });
            });
            console.log(`Parsed ${this.melodyNotes.length} melody notes and ${this.percussionNotes.length} percussion notes`);
        } catch (error) {
            console.error('Error parsing MusicXML:', error);
        }
    },

    noteToFrequency(step, octave, alter) {
        const noteMap = { 'C': 0, 'D': 2, 'E': 4, 'F': 5, 'G': 7, 'A': 9, 'B': 11 };
        const semitone = noteMap[step] + alter;
        const midiNote = (octave + 1) * 12 + semitone;
        return 440 * Math.pow(2, (midiNote - 69) / 12);
    },

    async play() {
        if (state.isPlaying) { this.pause(); return; }
        try { await this.initAudio(); } catch (error) {
            alert('Could not start audio. Please click the page first to enable audio playback.');
            return;
        }
        if (this.melodyNotes.length === 0 && this.percussionNotes.length === 0) {
            alert('No notes to play. Please generate a melody first.');
            return;
        }
        state.isPlaying = true;
        this.updatePlayButton();
        this.clearScheduled();
        const now = Tone.now();
        const secondsPerBeat = 60 / state.tempo;
        this.melodyNotes.forEach((note) => {
            const startTime = now + (note.time * secondsPerBeat);
            const dur = Math.max(0.1, note.duration * secondsPerBeat * 0.9);
            const id = Tone.Transport.schedule((time) => {
                if (state.synth && state.isPlaying) state.synth.triggerAttackRelease(note.frequency, dur, time);
            }, startTime - now);
            this.scheduledIds.push(id);
        });
        this.percussionNotes.forEach((note) => {
            const startTime = now + (note.time * secondsPerBeat);
            // Audit v3: scale the synth velocity from the
            // MusicXML velocity + accent. velocity 1-127 maps
            // to Tone.js gain 0-1 (roughly: gain = vel/127).
            // Accent multiplies the velocity so downbeats are
            // louder. Without this, every hit is the same
            // loudness, which sounds mechanical.
            const vel = (note.velocity || 80) / 127;
            const accent = note.accent || 0.6;
            const gain = Math.max(0.1, Math.min(1.0, vel * accent));
            const id = Tone.Transport.schedule((time) => {
                if (!state.isPlaying) return;
                switch (note.strokeType) {
                    case 'dum':
                        if (state.dumSkin) {
                            state.dumSkin.volume.value = -2 + (1 - gain) * -10;
                            state.dumSkin.triggerAttackRelease('G1', '8n', time);
                        }
                        if (state.dumBody) {
                            state.dumBody.volume.value = -8 + (1 - gain) * -10;
                            state.dumBody.triggerAttackRelease('8n', time);
                        }
                        if (state.dumTransient) {
                            state.dumTransient.volume.value = -16 + (1 - gain) * -8;
                            state.dumTransient.triggerAttackRelease('64n', time);
                        }
                        break;
                    case 'tak':
                        if (state.takSkin) {
                            state.takSkin.volume.value = -4 + (1 - gain) * -10;
                            state.takSkin.triggerAttackRelease('A4', '32n', time);
                        }
                        if (state.takCrack) {
                            state.takCrack.volume.value = -10 + (1 - gain) * -8;
                            state.takCrack.triggerAttackRelease('32n', time);
                        }
                        if (state.takJingle) {
                            state.takJingle.volume.value = -22 + (1 - gain) * -8;
                            state.takJingle.triggerAttackRelease('64n', time);
                        }
                        break;
                    case 'ka':
                        if (state.kaSkin) {
                            state.kaSkin.volume.value = -10 + (1 - gain) * -10;
                            state.kaSkin.triggerAttackRelease('D4', '32n', time);
                        }
                        if (state.kaNoise) {
                            state.kaNoise.volume.value = -18 + (1 - gain) * -8;
                            state.kaNoise.triggerAttackRelease('64n', time);
                        }
                        break;
                }
            }, startTime - now);
            this.scheduledIds.push(id);
        });
        let totalDuration = 0;
        if (this.melodyNotes.length > 0) {
            const last = this.melodyNotes[this.melodyNotes.length - 1];
            totalDuration = Math.max(totalDuration, (last.time + last.duration) * secondsPerBeat);
        }
        if (this.percussionNotes.length > 0) {
            const last = this.percussionNotes[this.percussionNotes.length - 1];
            totalDuration = Math.max(totalDuration, (last.time + last.duration) * secondsPerBeat);
        }
        this.endTimeoutId = setTimeout(() => {
            if (state.isLooping && state.isPlaying) { this.stop(); setTimeout(() => this.play(), 100); }
            else this.stop();
        }, totalDuration * 1000 + 500);
        Tone.Transport.start();
    },

    pause() {
        state.isPlaying = false;
        this.updatePlayButton();
        Tone.Transport.pause();
        if (this.endTimeoutId) { clearTimeout(this.endTimeoutId); this.endTimeoutId = null; }
    },

    stop() {
        state.isPlaying = false;
        this.updatePlayButton();
        this.clearScheduled();
        Tone.Transport.stop();
        Tone.Transport.cancel();
        if (state.synth) state.synth.releaseAll();
        if (this.endTimeoutId) { clearTimeout(this.endTimeoutId); this.endTimeoutId = null; }
    },

    clearScheduled() {
        this.scheduledIds.forEach(id => { try { Tone.Transport.clear(id); } catch (e) {} });
        this.scheduledIds = [];
    },

    toggleLoop() {
        state.isLooping = !state.isLooping;
        document.getElementById('btn-loop').classList.toggle('active', state.isLooping);
    },

    setTempo(bpm) {
        state.tempo = bpm;
        document.getElementById('tempo-value').textContent = `${bpm} BPM`;
        Tone.Transport.bpm.value = bpm;
    },

    updatePlayButton() {
        const btn = document.getElementById('btn-play');
        const icon = btn.querySelector('i');
        if (state.isPlaying) { icon.className = 'mdi mdi-pause'; btn.title = 'Pause'; }
        else { icon.className = 'mdi mdi-play'; btn.title = 'Play'; }
    }
};

// ============================================
// Generation — Full parameter payload
// ============================================

async function generateMelody() {
    Playback.stop();

    // Collect ALL parameters using canonical ui_parameters.json key names.
    // Values are sent as raw integers (0-100). The backend norm() divides by 100.
    const params = {
        // Core selections
        maqam_selection: document.getElementById('select-maqam').value,
        iqa_selection: document.getElementById('select-iqa').value,
        // Audit v2: the slider value is now in BARS (1..32), not
        // beats. Convert to beats using the selected iqa's time
        // signature so the backend sees the same shape as before.
        // The iqa_select preview's text is "4/4", "7/8", etc.
        duration_bars: parseInt(document.getElementById('slider-beats').value),
        duration_beats: (() => {
            const bars = parseInt(document.getElementById('slider-beats').value);
            const timeText = (document.getElementById('iqa-time')?.textContent || '4/4').trim();
            const m = timeText.match(/^(\d+)\s*\/\s*(\d+)$/);
            if (!m) return bars * 4;  // fallback: assume 4/4
            const beatsPerBar = parseInt(m[1]);
            return bars * beatsPerBar;
        })(),

        // Global style
        tradition_vs_experimental: parseInt(document.getElementById('slider-tradition').value),
        energy_level: parseInt(document.getElementById('slider-energy-level').value),

        // Melodic behavior
        melodic_density: parseInt(document.getElementById('slider-density').value),
        melodic_balance: parseInt(document.getElementById('slider-melodic-balance').value),
        step_vs_jump: parseInt(document.getElementById('slider-step-vs-jump').value),
        jins_adherence: parseInt(document.getElementById('slider-jins-adherence').value),
        contour_type: document.getElementById('select-contour-type').value,
        phrase_length: parseInt(document.getElementById('slider-phrase-length').value),
        repetition_amount: parseInt(document.getElementById('slider-repetition-amount').value),

        // Structure
        form_type: document.getElementById('select-form-type').value,
        phase_mode: parseInt(document.getElementById('slider-phase-mode').value),
        section_count: parseInt(document.getElementById('slider-section-count').value),
        phrase_length_measures: parseInt(document.getElementById('slider-phrase-measures').value),
        tension_curve: document.getElementById('select-tension-curve').value,

        // Rhythm
        rhythmic_alignment: parseInt(document.getElementById('slider-rhythmic-alignment').value),
        duration_variety: parseInt(document.getElementById('slider-duration-variety').value),
        tempo_stability: parseInt(document.getElementById('slider-tempo-stability').value),

        // Modulation
        modulation_frequency: parseInt(document.getElementById('slider-modulation-frequency').value),
        modulation_distance: parseInt(document.getElementById('slider-modulation-distance').value),
        max_maqamat: parseInt(document.getElementById('slider-max-maqamat').value),

        // Expression
        ornamentation_density: parseInt(document.getElementById('slider-ornaments').value),
        vibrato_amount: parseInt(document.getElementById('slider-vibrato-amount').value),
        dynamics_range: parseInt(document.getElementById('slider-dynamics-range').value),

        // Advanced
        pitch_gravity_strength: parseInt(document.getElementById('slider-pitch-gravity').value),
        transition_matrix_weight: parseInt(document.getElementById('slider-transition-weight').value),
        randomness_seed: document.getElementById('input-randomness-seed').value || '',

        // Misc
        include_percussion: document.getElementById('check-percussion').checked
    };

    UI.showLoading();

    try {
        const result = await API.generate(params);
        if (result.success) {
            state.generatedMusicXML = result.musicxml;
            state.fileId = result.file_id;
            await Score.render(result.musicxml);
        } else {
            alert('Generation failed: ' + result.error);
            UI.showEmpty();
        }
    } catch (error) {
        console.error('Generation error:', error);
        alert('Error generating melody: ' + error.message);
        UI.showEmpty();
    }
}

// ============================================
// Download
// ============================================

function downloadMusicXML() {
    if (!state.generatedMusicXML) return;
    const blob = new Blob([state.generatedMusicXML], { type: 'application/xml' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `maqam_${state.currentMaqam}_${state.fileId}.musicxml`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// ============================================
// Event Handlers
// ============================================

function setupEventHandlers() {
    // Generate button
    document.getElementById('btn-generate').addEventListener('click', generateMelody);

    // Maqam / Iqa select
    document.getElementById('select-maqam').addEventListener('change', (e) => UI.updateMaqamPreview(e.target.value));
    document.getElementById('select-iqa').addEventListener('change', (e) => UI.updateIqaPreview(e.target.value));

    // Info buttons
    document.getElementById('btn-maqam-info').addEventListener('click', () => UI.showMaqamInfo(document.getElementById('select-maqam').value));
    document.getElementById('btn-iqa-info').addEventListener('click', () => UI.showIqaInfo(document.getElementById('select-iqa').value));
    document.getElementById('btn-close-info').addEventListener('click', () => UI.closeInfoPanel());

    // Beats slider
    document.getElementById('slider-beats').addEventListener('input', (e) => {
        document.getElementById('beats-value').textContent = `${e.target.value} bars`;
    });

    // Wire ALL sliders to the inspector
    [
        'slider-tradition', 'slider-energy-level',
        'slider-density', 'slider-melodic-balance', 'slider-step-vs-jump',
        'slider-jins-adherence', 'slider-phrase-length', 'slider-repetition-amount',
        'slider-phase-mode', 'slider-section-count', 'slider-phrase-measures',
        'slider-rhythmic-alignment', 'slider-duration-variety', 'slider-tempo-stability',
        'slider-modulation-frequency', 'slider-modulation-distance', 'slider-max-maqamat',
        'slider-ornaments', 'slider-vibrato-amount', 'slider-dynamics-range',
        'slider-pitch-gravity', 'slider-transition-weight'
    ].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('input', () => Inspector.updateAll());
    });

    // Wire dropdowns to inspector
    ['select-contour-type', 'select-form-type', 'select-tension-curve'].forEach(id => {
        const el = document.getElementById(id);
        if (el) el.addEventListener('change', () => Inspector.updateAll());
    });

    // Composed form iqa override indicator
    const formSelect = document.getElementById('select-form-type');
    if (formSelect) {
        formSelect.addEventListener('change', () => {
            updateComposedFormIndicator();
        });
    }

    // Numeric value displays for integer sliders
    const numericSliders = {
        'slider-phrase-length': 'val-phrase-length',
        'slider-section-count': 'val-section-count',
        'slider-phrase-measures': 'val-phrase-measures',
        'slider-max-maqamat': 'val-max-maqamat'
    };
    Object.entries(numericSliders).forEach(([sliderId, valId]) => {
        const slider = document.getElementById(sliderId);
        const display = document.getElementById(valId);
        if (slider && display) {
            slider.addEventListener('input', () => { display.textContent = slider.value; });
        }
    });

    // Tempo slider
    document.getElementById('slider-tempo').addEventListener('input', (e) => Playback.setTempo(parseInt(e.target.value)));

    // Collapsible sections
    document.querySelectorAll('.section-header.collapsible').forEach(header => {
        header.addEventListener('click', () => {
            const targetId = header.dataset.target;
            const content = document.getElementById(targetId);
            header.classList.toggle('collapsed');
            content.classList.toggle('collapsed');
        });
    });

    // Playback controls
    document.getElementById('btn-play').addEventListener('click', () => Playback.play());
    document.getElementById('btn-stop').addEventListener('click', () => Playback.stop());
    document.getElementById('btn-loop').addEventListener('click', () => Playback.toggleLoop());

    // Download
    document.getElementById('btn-download').addEventListener('click', downloadMusicXML);

    // Zoom
    document.getElementById('btn-zoom-in').addEventListener('click', () => Score.zoomIn());
    document.getElementById('btn-zoom-out').addEventListener('click', () => Score.zoomOut());

    // Reset all controls to defaults
    document.getElementById('btn-reset').addEventListener('click', () => {
        // Core
        document.getElementById('slider-beats').value = 8;
        document.getElementById('beats-value').textContent = '8 bars';
        // Global style
        document.getElementById('slider-tradition').value = 70;
        document.getElementById('slider-energy-level').value = 50;
        // Melodic
        document.getElementById('slider-density').value = 50;
        document.getElementById('slider-melodic-balance').value = 75;
        document.getElementById('slider-step-vs-jump').value = 70;
        document.getElementById('slider-jins-adherence').value = 60;
        document.getElementById('select-contour-type').value = 'arch';
        document.getElementById('slider-phrase-length').value = 8;
        document.getElementById('slider-repetition-amount').value = 50;
        // Structure
        document.getElementById('select-form-type').value = 'free';
        document.getElementById('slider-phase-mode').value = 30;
        document.getElementById('slider-section-count').value = 4;
        document.getElementById('slider-phrase-measures').value = 1;
        document.getElementById('select-tension-curve').value = 'arch';
        // Rhythm
        document.getElementById('slider-rhythmic-alignment').value = 70;
        document.getElementById('slider-duration-variety').value = 50;
        document.getElementById('slider-tempo-stability').value = 70;
        // Modulation
        document.getElementById('slider-modulation-frequency').value = 30;
        document.getElementById('slider-modulation-distance').value = 30;
        document.getElementById('slider-max-maqamat').value = 2;
        // Expression
        document.getElementById('slider-ornaments').value = 50;
        document.getElementById('slider-vibrato-amount').value = 40;
        document.getElementById('slider-dynamics-range').value = 60;
        // Advanced
        document.getElementById('slider-pitch-gravity').value = 70;
        document.getElementById('slider-transition-weight').value = 60;
        document.getElementById('input-randomness-seed').value = '';
        // Percussion
        document.getElementById('check-percussion').checked = true;

        // Update numeric value displays
        updateNumericDisplays();
        updateComposedFormIndicator();

        document.querySelectorAll('.preset-btn').forEach(btn => btn.classList.remove('active'));
        state.currentPreset = null;
        Inspector.updateAll();
    });

    // Modals
    document.getElementById('btn-about').addEventListener('click', () => UI.showModal('modal-about'));
    document.getElementById('btn-help').addEventListener('click', () => UI.showModal('modal-help'));
    document.querySelectorAll('.btn-close-modal').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.modal').forEach(modal => modal.classList.remove('visible'));
        });
    });
    document.querySelectorAll('.modal-backdrop').forEach(backdrop => {
        backdrop.addEventListener('click', () => backdrop.parentElement.classList.remove('visible'));
    });

    // Help tabs
    document.querySelectorAll('.help-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabId = tab.dataset.tab;
            document.querySelectorAll('.help-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');
            document.querySelectorAll('.help-content').forEach(content => {
                content.style.display = content.id === `help-${tabId}` ? 'block' : 'none';
            });
        });
    });

    // Fullscreen
    document.getElementById('btn-fullscreen').addEventListener('click', () => {
        const viewer = document.querySelector('.panel-viewer');
        if (document.fullscreenElement) document.exitFullscreen();
        else viewer.requestFullscreen();
    });

    // Initialize audio on first user interaction
    document.body.addEventListener('click', () => {
        if (!state.audioInitialized) Playback.initAudio().catch(() => {});
    }, { once: true });
}

// ============================================
// Parameter Inspector — Full derived values
// ============================================

const Inspector = {
    updateAll() {
        const tradition = parseInt(document.getElementById('slider-tradition').value);
        const energy = parseInt(document.getElementById('slider-energy-level').value);
        const density = parseInt(document.getElementById('slider-density').value);
        const balance = parseInt(document.getElementById('slider-melodic-balance').value);
        const stepJump = parseInt(document.getElementById('slider-step-vs-jump').value);
        const ornaments = parseInt(document.getElementById('slider-ornaments').value);
        const modFreq = parseInt(document.getElementById('slider-modulation-frequency').value);
        const modDist = parseInt(document.getElementById('slider-modulation-distance').value);
        const rhythmAlign = parseInt(document.getElementById('slider-rhythmic-alignment').value);
        const tempoStab = parseInt(document.getElementById('slider-tempo-stability').value);
        const gravity = parseInt(document.getElementById('slider-pitch-gravity').value);
        const transWeight = parseInt(document.getElementById('slider-transition-weight').value);

        // --- Tradition-derived ---
        let ruleStrictness, violationProb;
        if (tradition <= 30) { ruleStrictness = 'soft'; violationProb = 0.40; }
        else if (tradition <= 70) {
            ruleStrictness = 'medium';
            violationProb = 0.40 - ((tradition - 31) / 39) * 0.25;
        } else {
            ruleStrictness = 'hard';
            violationProb = 0.15 - ((tradition - 71) / 29) * 0.13;
        }
        this._set('insp-rule-strictness', ruleStrictness);
        this._set('insp-violation-prob', violationProb.toFixed(2));
        this._setBar('insp-bar-violation', violationProb * 100);

        // --- Energy ---
        let energyStyle;
        if (energy <= 25) energyStyle = 'calm';
        else if (energy <= 60) energyStyle = 'moderate';
        else if (energy <= 80) energyStyle = 'lively';
        else energyStyle = 'intense';
        this._set('insp-energy-style', energyStyle);

        // --- Step probability ---
        const stepProb = (0.4 + (stepJump / 100) * 0.4);
        this._set('insp-step-prob', stepProb.toFixed(2));
        this._setBar('insp-bar-step-prob', stepProb * 100);

        // --- Density ---
        const densityNorm = density / 100;
        let packing;
        if (density <= 25) packing = 'very sparse';
        else if (density <= 45) packing = 'sparse';
        else if (density <= 55) packing = 'normal';
        else if (density <= 75) packing = 'dense';
        else packing = 'very dense';
        this._set('insp-density', densityNorm.toFixed(2));
        this._setBar('insp-bar-density', density);
        this._set('insp-packing', packing);

        // --- Contour ---
        this._set('insp-contour', document.getElementById('select-contour-type').value);

        // --- Jins Adherence ---
        const jinsAdh = parseInt(document.getElementById('slider-jins-adherence').value);
        const jinsLabel = jinsAdh <= 30 ? 'free' : jinsAdh <= 65 ? 'moderate' : 'strict';
        this._setBar('insp-bar-jins', jinsAdh);
        this._set('insp-jins', jinsLabel);

        // --- Structure ---
        const formVal = document.getElementById('select-form-type').value;
        const composedInfo = COMPOSED_FORMS[formVal];
        if (composedInfo) {
            this._set('insp-form', `${composedInfo.name} (K×4 + T)`);
            this._set('insp-sections', '8 (fixed)');
        } else {
            this._set('insp-form', formVal);
            this._set('insp-sections', document.getElementById('slider-section-count').value);
        }
        this._set('insp-tension', document.getElementById('select-tension-curve').value);

        // --- Rhythm ---
        let rhythmStyle;
        if (rhythmAlign <= 30) rhythmStyle = 'syncopated';
        else if (rhythmAlign <= 70) rhythmStyle = 'mixed';
        else rhythmStyle = 'on-beat';
        this._set('insp-rhythm-style', rhythmStyle);

        let tempoFeel;
        if (tempoStab <= 30) tempoFeel = 'rubato';
        else if (tempoStab <= 70) tempoFeel = 'moderate';
        else tempoFeel = 'strict';
        this._set('insp-tempo-feel', tempoFeel);

        // --- Ornament-derived ---
        let ornPreset, ornMult;
        if (ornaments <= 25) { ornPreset = 'plain'; ornMult = 0.2; }
        else if (ornaments <= 50) { ornPreset = 'moderate'; ornMult = 0.6; }
        else if (ornaments <= 75) { ornPreset = 'ornate'; ornMult = 1.0; }
        else { ornPreset = 'virtuosic'; ornMult = 1.5; }
        this._set('insp-ornament-preset', ornPreset);
        this._set('insp-ornament-mult', ornMult.toFixed(1));
        this._setBar('insp-bar-ornament', (ornMult / 1.5) * 100);

        // --- Modulation-derived ---
        if (modFreq <= 15) {
            this._set('insp-mod-count', '0');
            this._set('insp-mod-depth', 'none');
        } else if (modFreq <= 40) {
            this._set('insp-mod-count', '1');
            this._set('insp-mod-depth', 'brief tonicization');
        } else if (modFreq <= 70) {
            this._set('insp-mod-count', '2');
            this._set('insp-mod-depth', 'short modulation');
        } else {
            this._set('insp-mod-count', '4');
            this._set('insp-mod-depth', 'full modulation');
        }

        let modDistLabel;
        if (modDist <= 30) modDistLabel = 'close';
        else if (modDist <= 70) modDistLabel = 'moderate';
        else modDistLabel = 'distant';
        this._set('insp-mod-distance', modDistLabel);

        // --- Advanced ---
        this._set('insp-gravity', (gravity / 100).toFixed(2));
        this._setBar('insp-bar-gravity', gravity);
        this._set('insp-transition-weight', (transWeight / 100).toFixed(2));
        this._setBar('insp-bar-transition', transWeight);
    },

    _set(id, value) {
        const el = document.getElementById(id);
        if (!el) return;
        if (el.textContent !== String(value)) {
            el.textContent = value;
            el.classList.add('changed');
            clearTimeout(el._flashTimeout);
            el._flashTimeout = setTimeout(() => el.classList.remove('changed'), 600);
        }
    },

    _setBar(id, percent) {
        const el = document.getElementById(id);
        if (el) el.style.width = Math.max(0, Math.min(100, percent)) + '%';
    }
};

// ============================================
// Initialization
// ============================================

async function init() {
    try {
        const [maqamat, iqaat, presets, parameters] = await Promise.all([
            API.getMaqamat(), API.getIqaat(), API.getPresets(), API.getParameters()
        ]);
        state.maqamat = maqamat;
        state.iqaat = iqaat;
        state.presets = presets;
        state.parameters = parameters;
        UI.populateMaqamat(maqamat);
        UI.populateIqaat(iqaat);
        UI.populatePresets(presets);
        setupEventHandlers();
        Inspector.updateAll();
        UI.disablePlayback();
        console.log('Maqamatic initialized successfully');
        console.log(`Loaded ${maqamat.length} maqamat, ${iqaat.length} iqa'at, ${Object.keys(presets).length} presets`);
    } catch (error) {
        console.error('Initialization error:', error);
        alert('Error loading application data. Please refresh the page.');
    }
}

document.addEventListener('DOMContentLoaded', init);
