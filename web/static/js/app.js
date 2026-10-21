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
        // Audit v3: a bare fetch() during a scale-to-zero cold start
        // can hit a delay where the service takes 30+ seconds to
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
            throw new Error('Network error: ' + err.message + '. Check your connection and try again.');
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
        // Audit R2-10: OSMD measures its container while laying out the
        // score, so make it visible first (it is hidden while loading).
        // Rendering into a hidden, zero-width container produced squeezed
        // scores and NaN layout errors.
        UI.showScore();
        state.osmd = new opensheetmusicdisplay.OpenSheetMusicDisplay(container, {
            autoResize: true, backend: 'svg', drawTitle: true, drawComposer: true,
            drawingParameters: 'compacttight', drawPartNames: true,
            drawMeasureNumbers: true, drawTimeSignatures: true, drawKeySignatures: true
        });
        try {
            await state.osmd.load(musicxml);
            state.osmd.EngravingRules.RenderSingleHorizontalStaffline = false;
            // Mid-system rehearsal marks sit left of the note, so the maqam
            // text printed beside them ("Sikah on E½♭") stays readable.
            state.osmd.EngravingRules.RehearsalMarkXOffsetDefault = -20;
            state.osmd.render();
            UI.enablePlayback();
            Playback.parseNotesFromMusicXML(musicxml);
        } catch (error) {
            console.error('Error rendering score:', error);
            alert('Error rendering score: ' + error.message);
            UI.showEmpty();
        }
    },
    zoomIn() { if (state.osmd) { state.osmd.Zoom *= 1.2; state.osmd.render(); } },
    zoomOut() { if (state.osmd) { state.osmd.Zoom *= 0.8; state.osmd.render(); } }
};

// ============================================
// Form map: the piece's sections and maqamat, above the score
// ============================================

const FormMap = {
    sections: [],

    clear() {
        this.sections = [];
        document.getElementById('form-map').hidden = true;
        document.getElementById('form-map-strip').innerHTML = '';
        document.getElementById('form-map-path').textContent = '';
    },

    render(form) {
        this.clear();
        if (!Array.isArray(form) || form.length === 0) return;
        this.sections = form;
        const home = form[0].maqam;
        // home maqam in gold, each other maqam its own colour (fm-1..fm-4)
        const colour = {};
        let next = 1;
        form.forEach((s) => {
            if (!(s.maqam in colour)) colour[s.maqam] = s.maqam === home ? 0 : Math.min(4, next++);
        });

        const strip = document.getElementById('form-map-strip');
        form.forEach((s, i) => {
            const block = document.createElement('button');
            block.type = 'button';
            block.className = 'form-block fm-' + colour[s.maqam];
            block.setAttribute('role', 'listitem');
            block.style.setProperty('--beats', s.beats || 1);
            const showMaqam = s.change !== 'continue';
            block.innerHTML = '<span class="fb-label"></span><span class="fb-maqam"></span>';
            block.querySelector('.fb-label').textContent = s.label || '·';
            block.querySelector('.fb-maqam').textContent = showMaqam ? `${s.maqam_name} · ${s.tonic}` : '';
            block.title = this._describe(s);
            block.setAttribute('aria-label', this._describe(s));
            block.addEventListener('click', () => this.scrollTo(s.measure));
            strip.append(block);
        });

        // The path through the maqamat, e.g. "Rast on C → Sikah on E½♭ (bar 9) → Rast (bar 17)"
        const path = document.getElementById('form-map-path');
        const steps = form.filter((s) => s.change !== 'continue');
        if (steps.length === 1) {
            path.innerHTML = '<b></b> throughout';
            path.querySelector('b').textContent = `${steps[0].maqam_name} on ${steps[0].tonic}`;
        } else {
            steps.forEach((s, i) => {
                if (i) path.append(' → ');
                const b = document.createElement('b');
                b.textContent = s.change === 'return' ? s.maqam_name : `${s.maqam_name} on ${s.tonic}`;
                path.append(b);
                if (i && s.measure) path.append(` (bar ${s.measure})`);
            });
        }
        document.getElementById('form-map').hidden = false;
    },

    _describe(s) {
        const bars = s.measure ? (s.end_measure && s.end_measure !== s.measure
            ? `bars ${s.measure}–${s.end_measure}` : `bar ${s.measure}`) : '';
        const how = {
            start: 'home maqam',
            continue: 'continues',
            return: 'returns home',
            modulation: s.pivot ? `modulation, starting on the ${s.pivot.text}` : 'modulation',
        }[s.change] || '';
        return [s.label, `${s.maqam_name} on ${s.tonic}`, how, bars].filter(Boolean).join(' · ');
    },

    // Highlight the section being played (index into sections; null = none).
    setActive(index) {
        document.querySelectorAll('#form-map-strip .form-block').forEach((b, i) => {
            b.classList.toggle('active', i === index);
        });
    },

    // Scroll the score so the section's first measure sits under the map.
    scrollTo(measure) {
        const sheet = state.osmd && state.osmd.GraphicSheet;
        const row = measure && sheet && sheet.MeasureList[measure - 1];
        const gm = row && row.find((m) => m);
        if (!gm) return;
        const scroller = document.getElementById('score-container');
        const osmdBox = document.getElementById('osmd-container');
        const map = document.getElementById('form-map');
        // OSMD positions are in units of 10 px at zoom 1
        const y = gm.PositionAndShape.AbsolutePosition.y * 10 * (state.osmd.Zoom || 1);
        const top = osmdBox.offsetTop + y - map.offsetHeight - 24;
        scroller.scrollTo({ top: Math.max(0, top), behavior: 'smooth' });
    }
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
        // The page-wide first-click handler and the Play button can both
        // call this on the same click; share one initialisation instead of
        // building every instrument twice (which made Tone.js throw
        // "Start time must be strictly greater than previous start time").
        if (!this._audioInit) {
            this._audioInit = this._buildAudio().catch((error) => {
                this._audioInit = null;
                throw error;
            });
        }
        return this._audioInit;
    },

    async _buildAudio() {
        try {
            await Tone.start();
            console.log('Audio context started');

            // ============================================
            // NAY (Arabic flute) — Enhanced signal chain:
            // Oscillators → Formant → Vibrato → Chorus → Tremolo → Reverb → Dest
            // Breath noise → breathFilter (dynamic) → Reverb → Dest
            // ============================================

            // Master: a limiter just below full scale, so nay and drums
            // playing loud together never clip.
            const master = new Tone.Limiter(-1).toDestination();

            const nayReverb = new Tone.Reverb({ decay: 2.2, wet: 0.22 }).connect(master);

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
                // velocity follows the score's dynamics; `fast` gives the
                // short notes of ornaments (trills, grace notes) a crisp
                // attack instead of the nay's slow breath-in (audit R2-12).
                triggerAttackRelease: (freq, duration, time, velocity = 1, fast = false) => {
                    const freqVal = typeof freq === 'string' ? Tone.Frequency(freq).toFrequency() : freq;
                    const dur = typeof duration === 'number' ? duration : Tone.Time(duration).toSeconds();

                    // Dynamic vibrato: higher register = more vibrato
                    const vibratoDepth = 0.06 + Math.min(0.08, (freqVal - 200) / 4000);
                    if (state.nayVibratoNode) {
                        state.nayVibratoNode.depth.setValueAtTime(vibratoDepth, time);
                    }

                    // Per-note attack variation: ±30ms for human-like irregularity
                    const attackVar = fast ? 0.01 : 0.10 + (Math.random() * 0.06 - 0.03);
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
                    if (state.naySine) state.naySine.triggerAttackRelease(freqVal, duration, time, velocity);
                    if (state.nayBreath) state.nayBreath.triggerAttackRelease(duration, time, velocity);
                    if (state.nayOvertone) state.nayOvertone.triggerAttackRelease(freqVal * 2.003, duration, time, velocity);
                    if (state.nayOvertone2) state.nayOvertone2.triggerAttackRelease(freqVal * 3.005, duration, time, velocity);

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
            // PERCUSSION: darbuka (dum / tak / ka) with riq jingles on tak.
            // Strokes are synthesised once into sample buffers (drumkit.js)
            // and each hit plays one of them, so hits overlap and ring out
            // instead of cutting each other off.
            // Voices → bus compressor → master, plus a small room (send).
            // ============================================

            const drumRoom = new Tone.Reverb({ decay: 1.1, preDelay: 0.008, wet: 1 }).connect(master);
            const drumBus = new Tone.Compressor({
                threshold: -16, ratio: 2.5, attack: 0.004, release: 0.12
            }).connect(master);
            drumBus.connect(new Tone.Gain(0.16).connect(drumRoom));

            const sampleRate = Tone.getContext().sampleRate;
            state.drumVoices = {};
            state.drumBuffers = {};
            for (const [name, db] of Object.entries(MaqamaticDrums.LEVELS)) {
                state.drumVoices[name] = new Tone.Gain(Tone.dbToGain(db)).connect(drumBus);
                state.drumBuffers[name] = [];
                for (let v = 0; v < MaqamaticDrums.VARIANTS; v++) {
                    state.drumBuffers[name].push(
                        Tone.ToneAudioBuffer.fromArray(MaqamaticDrums.render(name, sampleRate, v)));
                }
                // let the page breathe between strokes (~20 ms of work each)
                await new Promise((resolve) => setTimeout(resolve, 0));
            }
            await drumRoom.ready;

            state.audioInitialized = true;
        } catch (error) {
            console.error('Failed to initialize audio:', error);
            throw error;
        }
    },

    parseNotesFromMusicXML(musicxml) {
        this.melodyNotes = [];
        this.percussionNotes = [];
        // Dynamic marking -> melody velocity (audit R2-12).
        const DYNAMIC_VELOCITY = { pp: 0.4, p: 0.5, mp: 0.65, mf: 0.8, f: 0.9, ff: 1.0 };
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(musicxml, 'text/xml');
            const parts = xmlDoc.querySelectorAll('part');
            parts.forEach((part) => {
                const divisions = parseInt(part.querySelector('divisions')?.textContent) || 8;
                const keyFifths = parseInt(part.querySelector('key fifths')?.textContent) || 0;
                let currentTime = 0;
                let velocity = DYNAMIC_VELOCITY.mf;
                let pendingGrace = null;
                const partNotes = [];
                // Walk each measure in document order so a <direction>
                // (dynamics) applies to the notes after it.
                part.querySelectorAll('measure').forEach(measure => {
                    for (const el of measure.children) {
                        if (el.tagName === 'direction') {
                            const dyn = el.querySelector('dynamics > *');
                            if (dyn && DYNAMIC_VELOCITY[dyn.tagName] !== undefined) {
                                velocity = DYNAMIC_VELOCITY[dyn.tagName];
                            }
                            continue;
                        }
                        if (el.tagName !== 'note') continue;
                        const note = el;
                        const pitch = note.querySelector('pitch');
                        // Grace notes take no time: play them just before
                        // the next note.
                        if (note.querySelector('grace')) {
                            if (pitch) pendingGrace = this._readPitch(pitch);
                            continue;
                        }
                        const isRest = note.querySelector('rest') !== null;
                        const isChord = note.querySelector('chord') !== null;
                        const duration = parseInt(note.querySelector('duration')?.textContent) || divisions;
                        const durationBeats = duration / divisions;
                        const ties = note.querySelectorAll('tie');
                        let hasTieStop = false;
                        ties.forEach(tie => {
                            if (tie.getAttribute('type') === 'stop') hasTieStop = true;
                        });
                        const unpitched = note.querySelector('unpitched');
                        if (!isRest) {
                            if (unpitched) {
                                const displayStep = unpitched.querySelector('display-step')?.textContent || 'E';
                                const displayOctave = parseInt(unpitched.querySelector('display-octave')?.textContent) || 4;
                                let strokeType = 'ka';
                                if (displayStep === 'F' && displayOctave === 4) strokeType = 'dum';
                                else if (displayStep === 'C' && displayOctave === 5) strokeType = 'tak';
                                else if (displayStep === 'E' && displayOctave === 4) strokeType = 'ka';
                                // Read velocity/accent from the MusicXML so the
                                // audio playback gets the same dynamic shape as
                                // the visual score. Velocity is the standard
                                // `dynamics` attribute on <note> (percent of the
                                // forte velocity 90; audit F-2/R2-04). Older
                                // files carried a <velocity>1-127</velocity>.
                                const dynAttr = parseFloat(note.getAttribute('dynamics'));
                                const velText = note.querySelector('velocity')?.textContent;
                                const vel = Number.isFinite(dynAttr) ? Math.round(dynAttr * 0.9)
                                          : velText ? parseInt(velText) : 80;
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
                                const p = this._readPitch(pitch);
                                if (hasTieStop && this.melodyNotes.length > 0) {
                                    this.melodyNotes[this.melodyNotes.length - 1].duration += durationBeats;
                                } else {
                                    const orn = note.querySelector(
                                        'notations ornaments trill-mark, notations ornaments mordent, ' +
                                        'notations ornaments inverted-mordent, notations ornaments turn');
                                    const entry = {
                                        time: currentTime, duration: durationBeats, frequency: p.frequency,
                                        noteName: `${p.step}${p.alter === -0.5 ? 'half-flat' : p.alter === 0.5 ? 'half-sharp' : p.alter === -1 ? 'b' : p.alter === 1 ? '#' : ''}${p.octave}`,
                                        step: p.step, octave: p.octave, alter: p.alter,
                                        velocity,
                                        ornament: orn ? orn.tagName : null,
                                        grace: pendingGrace ? pendingGrace.frequency : null,
                                    };
                                    this.melodyNotes.push(entry);
                                    partNotes.push(entry);
                                }
                                pendingGrace = null;
                            }
                        }
                        if (!isChord) currentTime += durationBeats;
                    }
                });
                this._resolveOrnamentNeighbours(partNotes, keyFifths);
            });
            console.log(`Parsed ${this.melodyNotes.length} melody notes and ${this.percussionNotes.length} percussion notes`);
        } catch (error) {
            console.error('Error parsing MusicXML:', error);
        }
    },

    _readPitch(pitchEl) {
        const step = pitchEl.querySelector('step')?.textContent || 'C';
        const octave = parseInt(pitchEl.querySelector('octave')?.textContent) || 4;
        const alterEl = pitchEl.querySelector('alter');
        const alter = alterEl ? parseFloat(alterEl.textContent) : 0;
        return { step, octave, alter, frequency: this.noteToFrequency(step, octave, alter) };
    },

    // Trills, mordents and turns use the scale neighbours of the note. The
    // score only names their letter, so take each neighbour's accidental
    // from the nearest melody note on that letter (which keeps the maqam's
    // quarter tones), falling back to the key signature.
    _resolveOrnamentNeighbours(notes, keyFifths) {
        notes.forEach((n, i) => {
            if (!n.ornament) return;
            if (['trill-mark', 'inverted-mordent', 'turn'].includes(n.ornament)) {
                n.upperFrequency = this._neighbour(notes, i, +1, keyFifths);
            }
            if (['mordent', 'turn'].includes(n.ornament)) {
                n.lowerFrequency = this._neighbour(notes, i, -1, keyFifths);
            }
        });
    },

    _neighbour(notes, i, direction, keyFifths) {
        const LETTERS = 'CDEFGAB';
        const index = LETTERS.indexOf(notes[i].step) + direction;
        const step = LETTERS[(index + 7) % 7];
        const octave = notes[i].octave + Math.floor(index / 7);
        let alter = null;
        for (let d = 1; d < notes.length && alter === null; d++) {
            for (const j of [i - d, i + d]) {
                if (j >= 0 && j < notes.length && notes[j].step === step) { alter = notes[j].alter; break; }
            }
        }
        if (alter === null) {
            const flats = 'BEADGCF', sharps = 'FCGDAEB';
            alter = keyFifths < 0 && flats.slice(0, -keyFifths).includes(step) ? -1
                  : keyFifths > 0 && sharps.slice(0, keyFifths).includes(step) ? 1 : 0;
        }
        return this.noteToFrequency(step, octave, alter);
    },

    // Turn one melody note into the sounding events: an optional grace note,
    // the ornament figure, then the main note for the remaining time.
    _expandOrnaments(note, totalSeconds, secondsPerBeat) {
        const vel = note.velocity ?? 0.8;
        const events = [];
        let offset = 0;
        let remaining = totalSeconds;
        if (note.grace) {
            const g = Math.min(0.08, totalSeconds * 0.3);
            events.push({ offset: 0, dur: g, freq: note.grace, vel: vel * 0.85, fast: true });
            offset = g;
            remaining -= g;
        }
        // Ornament notes are about a 32nd note, kept between 50 and 90 ms.
        const seg = Math.min(0.09, Math.max(0.05, secondsPerBeat / 8));
        const play = (freqs) => freqs.forEach(f => {
            events.push({ offset, dur: seg, freq: f, vel, fast: true });
            offset += seg;
            remaining -= seg;
        });
        const main = note.frequency, up = note.upperFrequency, low = note.lowerFrequency;
        if (note.ornament === 'trill-mark' && up && remaining > seg * 4) {
            const n = Math.floor((remaining - seg) / seg);
            play(Array.from({ length: n }, (_, k) => (k % 2 === 0 ? main : up)));
        } else if (note.ornament === 'mordent' && low && remaining > seg * 3) {
            play([main, low]);
        } else if (note.ornament === 'inverted-mordent' && up && remaining > seg * 3) {
            play([main, up]);
        } else if (note.ornament === 'turn' && up && low && remaining > seg * 5) {
            play([up, main, low]);
        }
        events.push({ offset, dur: Math.max(0.05, remaining), freq: main, vel, fast: false });
        return events;
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
        // Resuming after pause continues from the paused position, so the
        // end-of-piece timer must only cover what is left (audit R2-17).
        const resumeFrom = Tone.Transport.state === 'paused' ? Tone.Transport.seconds : 0;
        state.isPlaying = true;
        this.updatePlayButton();
        this.clearScheduled();
        const now = Tone.now();
        const secondsPerBeat = 60 / state.tempo;
        this.melodyNotes.forEach((note) => {
            const startTime = now + (note.time * secondsPerBeat);
            const dur = Math.max(0.1, note.duration * secondsPerBeat * 0.9);
            // Grace notes and ornaments become extra short notes; a plain
            // note is a single event, as before.
            this._expandOrnaments(note, dur, secondsPerBeat).forEach((ev) => {
                const id = Tone.Transport.schedule((time) => {
                    if (state.synth && state.isPlaying) {
                        state.synth.triggerAttackRelease(ev.freq, ev.dur, time, ev.vel, ev.fast);
                    }
                }, startTime - now + ev.offset);
                this.scheduledIds.push(id);
            });
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
            // Loudness is passed as each hit's velocity. Setting the shared
            // .volume at scheduling time (as before) also changed hits that
            // were still sounding (audit R2-17).
            const id = Tone.Transport.schedule((time) => {
                if (!state.isPlaying) return;
                switch (note.strokeType) {
                    case 'dum':
                        this._stroke('dum', time, gain);
                        break;
                    case 'tak':
                        this._stroke('tak', time, gain);
                        this._stroke('jingle', time, gain);
                        break;
                    case 'ka':
                        this._stroke('ka', time, gain);
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
        }, Math.max(0, totalDuration - resumeFrom) * 1000 + 500);
        // Light up each section of the form map as it is played.
        FormMap.sections.forEach((s, i) => {
            if (s.start_beat === null || s.start_beat === undefined) return;
            // A timer, not Tone.Draw: Draw runs on animation frames and
            // drops late callbacks, so throttled tabs skipped sections.
            const id = Tone.Transport.schedule((time) => {
                setTimeout(() => { if (state.isPlaying) FormMap.setActive(i); },
                           Math.max(0, (time - Tone.now()) * 1000));
            }, s.start_beat * secondsPerBeat);
            this.scheduledIds.push(id);
        });
        Tone.Transport.start();
    },

    // One percussion hit: a randomly chosen variant of the stroke, played
    // at the hit's loudness, with a hair of pitch variation like a hand
    // never striking quite the same spot.
    _stroke(name, time, gain) {
        const bank = state.drumBuffers && state.drumBuffers[name];
        if (!bank || !bank.length) return;
        const source = new Tone.ToneBufferSource({
            url: bank[Math.floor(Math.random() * bank.length)],
            playbackRate: 1 + (Math.random() - 0.5) * 0.02,
        }).connect(state.drumVoices[name]);
        source.onended = () => { if (!source.disposed) source.dispose(); };
        source.start(time, 0, undefined, gain);
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
        FormMap.setActive(null);
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
        register_excursion: parseInt(document.getElementById('slider-register-excursion').value),
        characteristic_phrase_adherence: parseInt(document.getElementById('slider-char-phrases').value),
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
            FormMap.clear();
            await Score.render(result.musicxml);
            FormMap.render(result.form);
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
        'slider-beats', 'slider-phase-mode', 'slider-phrase-measures',
        'slider-rhythmic-alignment', 'slider-duration-variety', 'slider-tempo-stability',
        'slider-modulation-frequency', 'slider-modulation-distance', 'slider-max-maqamat',
        'slider-ornaments', 'slider-vibrato-amount', 'slider-dynamics-range',
        'slider-pitch-gravity', 'slider-transition-weight',
        'slider-register-excursion', 'slider-char-phrases'
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
        document.getElementById('slider-register-excursion').value = 35;
        document.getElementById('slider-char-phrases').value = 70;
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
    // Every value below mirrors the backend formula named in its comment,
    // so the panel shows what generation will actually use (audit R2-09).
    updateAll() {
        const val = (id) => parseInt(document.getElementById(id).value);
        const t = val('slider-tradition') / 100;
        const energy = val('slider-energy-level') / 100;
        const density = val('slider-density') / 100;
        const stepJump = val('slider-step-vs-jump') / 100;
        const jinsAdh = val('slider-jins-adherence') / 100;
        const ornaments = val('slider-ornaments') / 100;
        const modFreq = val('slider-modulation-frequency') / 100;
        const modDist = val('slider-modulation-distance') / 100;
        const rhythmAlign = val('slider-rhythmic-alignment') / 100;
        const tempoStab = val('slider-tempo-stability') / 100;
        const gravity = val('slider-pitch-gravity') / 100;
        const transWeight = val('slider-transition-weight') / 100;

        // --- Style ---
        // PhraseStructureRules.should_pair_antecedent_consequent
        this._set('insp-pairing', (t * 0.6).toFixed(2));
        // MaqamGenerator._enforce_tonic_ending
        const tonicEnding = t < 0.4 ? 0 : Math.min(1, t * 1.3);
        this._set('insp-tonic-ending', tonicEnding.toFixed(2));
        this._setBar('insp-bar-tonic-ending', tonicEnding * 100);
        // DurationRules.get_style_for_energy
        this._set('insp-energy-style',
            energy < 0.25 ? 'sustained' : energy < 0.75 ? 'flowing' : 'agitated');

        // --- Melodic ---
        // MelodicMotionRules.get_interval_type_probs
        const stepProb = 0.4 + stepJump * 0.4;
        this._set('insp-step-prob', stepProb.toFixed(2));
        this._setBar('insp-bar-step-prob', stepProb * 100);
        // PhraseGenerator.generate_phrase: clamp(phrase_length) x (0.5 + density)
        const phraseLen = Math.max(4, Math.min(16, val('slider-phrase-length')));
        const notesPerPhrase = Math.max(4, Math.min(16, Math.trunc(phraseLen * (0.5 + density))));
        this._set('insp-density', density.toFixed(2));
        this._setBar('insp-bar-density', density * 100);
        this._set('insp-notes-per-phrase', notesPerPhrase);
        this._set('insp-contour', document.getElementById('select-contour-type').value);
        // JinsRules.get_jins_boundary_adjustment: weight of a cross-jins step
        this._setBar('insp-bar-jins', jinsAdh * 100);
        this._set('insp-jins', '×' + Math.max(0.1, 1 - 0.8 * jinsAdh).toFixed(2));

        // --- Structure ---
        const formVal = document.getElementById('select-form-type').value;
        const composedInfo = COMPOSED_FORMS[formVal];
        if (composedInfo) {
            this._set('insp-form', `${composedInfo.name} (K×4 + T)`);
            this._set('insp-sections', '8 (fixed)');
        } else {
            // StructureGrammarRules._compute_target_section_count
            const bars = val('slider-beats');
            const measuresPerSection = 2 * Math.max(1, val('slider-phrase-measures'));
            const sections = Math.max(1, Math.min(24, this._pyRound(bars / measuresPerSection)));
            this._set('insp-form', formVal);
            this._set('insp-sections', sections);
        }
        this._set('insp-tension', document.getElementById('select-tension-curve').value);

        // --- Rhythm ---
        // DurationRules.get_syncopation_probability / get_tempo_variance
        this._set('insp-syncopation', (0.6 - rhythmAlign * 0.5).toFixed(2));
        this._set('insp-tempo-variance', (0.4 - tempoStab * 0.35).toFixed(2));

        // --- Expression ---
        // OrnamentationRules.get_style_preset_name + config multipliers
        const [ornPreset, ornMult] =
            ornaments < 0.25 ? ['plain', 0.2] :
            ornaments < 0.5  ? ['moderate', 0.6] :
            ornaments < 0.75 ? ['ornate', 1.0] : ['virtuosic', 1.5];
        this._set('insp-ornament-preset', ornPreset);
        this._set('insp-ornament-mult', ornMult.toFixed(1));
        this._setBar('insp-bar-ornament', (ornMult / 1.5) * 100);

        // --- Modulation ---
        // ModulationRules.get_modulation_depth_category / filter_targets_by_distance
        this._set('insp-mod-depth',
            modFreq <= 0.15 ? 'none' : modFreq <= 0.4 ? 'brief tonicization'
            : modFreq <= 0.7 ? 'short modulation' : 'full modulation');
        this._set('insp-max-maqamat', val('slider-max-maqamat'));
        this._set('insp-mod-distance',
            modDist < 0.3 ? 'same family' : modDist < 0.7 ? 'related' : 'any');

        // --- Advanced ---
        this._set('insp-gravity', gravity.toFixed(2));
        this._setBar('insp-bar-gravity', gravity * 100);
        this._set('insp-transition-weight', transWeight.toFixed(2));
        this._setBar('insp-bar-transition', transWeight * 100);
    },

    // Python's round(): halves go to the even neighbour.
    _pyRound(x) {
        const floor = Math.floor(x);
        const diff = x - floor;
        if (diff > 0.5) return floor + 1;
        if (diff < 0.5) return floor;
        return floor % 2 === 0 ? floor : floor + 1;
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
