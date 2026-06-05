# Maqamatic

A Flask web app that generates Arabic maqam melodies as MusicXML. Pick a maqam (22 available), an iqa'/rhythm (23 available), tweak the parameters, hit Generate, and get a notated score you can play back, download, or edit in any MusicXML-compatible tool (MuseScore, Finale, Dorico, etc).

By Zaher Alkaei.

## Sources

All maqam and jins data in this project is verified against [MaqamWorld](https://maqamworld.com), the canonical Arabic music encyclopedia maintained by Johnny Farraj and Sami Abu Shumays. See [MAQAMATIC_REFERENCE.md](MAQAMATIC_REFERENCE.md) for the full per-maqam reference with direct MaqamWorld source links.

## Running it

Requires Python 3.10+ and pip.

```bash
cd maqamatic
pip install -r requirements.txt
python run.py
```

Then open http://localhost:5025 in a browser. `run.py` will also try to open the browser automatically after a short delay.

For production, use gunicorn (already in requirements):

```bash
gunicorn --bind 0.0.0.0:5025 --workers 2 "web.app:app"
```

Docker is also supported — see the included Dockerfile and docker-compose.yml.

## How it works

The browser UI is a single-page app served by Flask. Selecting a maqam and an iqa' populates the parameters, and clicking Generate POSTs to `/api/generate`. The backend runs the melody generator (`maqam_generator.py`) and the MusicXML serializer (`generator_to_musicxml.py`), then returns the score as a string and stores it on disk for download via `/download/<file_id>`.

The generator is driven by a probabilistic model that uses transition matrices and sayr (melodic path) rules specific to each maqam. Every maqam is loaded from `data/maqamat.json`, which encodes the scale, ajnas (tetrachord fragments), ghammaz (secondary tonic), modulations, and mood. iqa'at come from `data/iqaat.json` with sub-beat-precise rhythm patterns. ajnas come from `data/ajnas.json`.

The user's parameter choices (traditionality, energy, melodic balance, jins adherence, etc.) are mapped to internal generator weights via `params_expanded.py`. The rule engine (`rule_engine.py`) applies traditional Arabic music theory constraints on top of the probabilistic generator.

## What's in the box

- 22 maqamat across 8 families (Bayati, Rast, Hijaz, Sikah, Nahawand, Kurd, Nikriz, Saba) including quarter-tone support
- 23 iqa'at from 2/4 to 10/8
- 5 presets: Composed Piece, Energetic Dance, Meditative, Modern Fusion, Traditional Taqsim
- 20+ parameter sliders covering overall style, melodic behavior, form & structure, rhythm, and ornamentation
- 9 musical forms including traditional Sama'i, Longa, and Bashraf
- In-browser score rendering via OpenSheetMusicDisplay
- MusicXML download for use in any notation software

## Files

Core engine:
- `maqam_generator.py` — main generator (phases, phrases, pitch selector, rhythm generator, modulation handler)
- `rule_engine.py` — traditional Arabic music theory constraints layered on top of the generator
- `generator_to_musicxml.py` — converts the internal representation to MusicXML 4.0
- `maqam_to_musicxml.py` — lower-level MusicXML utilities
- `params_expanded.py` — maps UI parameters to generator parameters

Data:
- `data/maqamat.json` — 22 maqamat with scale, ajnas, sayr, modulations
- `data/ajnas.json` — jins (tetrachord) database
- `data/iqaat.json` — 23 iqa'at with sub-beat encoding
- `data/transition_matrices.json` — pitch transition probabilities per maqam
- `data/sayr_definitions.json` — melodic path rules
- `data/generator_config.json` — universal rules and defaults
- `data/ui_parameters.json` — UI parameter metadata

Web app:
- `web/app.py` — Flask backend with `/api/generate` and `/download/<file_id>` endpoints
- `web/templates/index.html` — single-page UI
- `web/static/` — CSS and JS
- `run.py` — quick-start script that runs Flask on port 5025

Documentation:
- `ARCHITECTURE.md` — high-level architecture diagram
- `MAQAMATIC_REFERENCE.md` — detailed reference of all 22 maqamat (scale, ajnas, sayr, modulations, mood)
- `docs/UI_TO_MUSIC_MAPPING.md` — how each UI setting maps to musical theory
- `knowledge/ajnas/` — markdown notes on individual ajnas

## Configuration

The default Flask port is 5025 (set in `run.py`). Override with the `PORT` environment variable if needed.

Generated scores are stored temporarily in `output/`. They are deleted when the server restarts and are not committed to git (see `.gitignore`).

## License

See LICENSE.
