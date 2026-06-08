"""
Maqamatic Web Application - Flask Backend
A modern web interface for Arabic Maqam melody generation.
"""

import os
import json
import re
import time
import uuid
import tempfile
from collections import defaultdict
from pathlib import Path
from flask import Flask, request, jsonify, send_file, render_template
from flask_cors import CORS

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from maqam_generator import MaqamGenerator, DataLoader
from params_expanded import GeneratorParams, create_generator_from_ui_params
from generator_to_musicxml import generate_and_export, MusicXMLGenerator

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')
# Audit v3 (post-Railway): CORS was permissive but the
# Access-Control-Allow-Headers default didn't always include
# Content-Type on some proxies (Railway edge). Be explicit so
# the browser's preflight OPTIONS request always succeeds.
CORS(app, resources={r"/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Authorization"],
    "max_age": 600,
}})

# A /health endpoint that just returns 200. Railway uses this to
# detect when the service is "up" so it doesn't route traffic
# during cold start.
@app.route('/health')
def health():
    return jsonify({'status': 'ok'}), 200

# Simple in-memory rate limiter for generation endpoint
class RateLimiter:
    """Per-IP rate limiter: max `limit` requests per `window_seconds`.

    Bounded memory: cap at `max_keys` distinct IPs; evict the
    least-recently-used IP when full. Without this, an attacker
    making one request from many IPs would grow the dict forever.
    """
    def __init__(self, limit=10, window_seconds=60, max_keys=10000):
        self.limit = limit
        self.window = window_seconds
        self.max_keys = max_keys
        # OrderedDict so we can pop the oldest (LRU eviction) without
        # an extra data structure.
        from collections import OrderedDict
        self.requests = OrderedDict()

    def _evict_if_over(self):
        """Drop the least-recently-used IP until under max_keys."""
        while len(self.requests) > self.max_keys:
            self.requests.popitem(last=False)

    def is_allowed(self, key):
        import time
        now = time.time()
        # Prune this key's expired timestamps.
        self.requests[key] = [t for t in self.requests.get(key, [])
                              if now - t < self.window]
        if len(self.requests[key]) >= self.limit:
            return False
        self.requests[key].append(now)
        # Touch the key to mark it as most-recently-used.
        self.requests.move_to_end(key)
        self._evict_if_over()
        return True


rate_limiter = RateLimiter(limit=10, window_seconds=60)
# Initialize data loader
DATA_DIR = Path(__file__).parent.parent / "data"
data_loader = DataLoader(str(DATA_DIR))

# Temporary storage for generated files - use local output directory
TEMP_DIR = Path(__file__).parent.parent / "output"
try:
    TEMP_DIR.mkdir(exist_ok=True)
except PermissionError:
    # Fallback to a temp directory in the project folder
    TEMP_DIR = Path(__file__).parent / "generated"
    TEMP_DIR.mkdir(exist_ok=True)

# Maximum age for generated files (1 hour)
MAX_FILE_AGE_SECONDS = 3600


def cleanup_old_files():
    """Remove generated files older than MAX_FILE_AGE_SECONDS."""
    try:
        now = time.time()
        for f in TEMP_DIR.glob("maqam_*.musicxml"):
            if f.stat().st_mtime < now - MAX_FILE_AGE_SECONDS:
                f.unlink(missing_ok=True)
    except Exception:
        pass  # Cleanup is best-effort, don't block generation


@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')


@app.route('/api/maqamat', methods=['GET'])
def get_maqamat():
    """Get list of available maqamat with their info"""
    maqamat = []
    for maqam_id, maqam_data in sorted(data_loader.maqamat.items()):
        maqamat.append({
            'id': maqam_id,
            'name': maqam_data.get('name', maqam_id),
            'family': maqam_data.get('family', 'unknown'),
            'characteristics': maqam_data.get('characteristics', {}),
            'description': maqam_data.get('description', ''),
            'tonic': maqam_data.get('tonic', 'D')
        })
    return jsonify(maqamat)


@app.route('/api/iqaat', methods=['GET'])
def get_iqaat():
    """Get list of available iqa'at (rhythmic cycles)"""
    iqaat = []
    for iqa_id, iqa_data in sorted(data_loader.iqaat.items()):
        time_sig = iqa_data.get('time_signature', {})
        iqaat.append({
            'id': iqa_id,
            'name': iqa_data.get('name', iqa_id),
            'time_signature': time_sig.get('display', '4/4'),
            'beats': time_sig.get('beats', 4),
            'characteristics': iqa_data.get('characteristics', {}),
            'description': iqa_data.get('description', '')
        })
    return jsonify(iqaat)


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Get available generation presets"""
    ui_params_path = DATA_DIR / "ui_parameters.json"
    try:
        with open(ui_params_path, 'r', encoding='utf-8') as f:
            ui_params = json.load(f)
        return jsonify(ui_params.get('presets', {}))
    except Exception as e:
        app.logger.error(f"Failed to load presets: {e}")
        return jsonify({'error': 'Failed to load presets'}), 500


@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """Get UI parameter definitions"""
    ui_params_path = DATA_DIR / "ui_parameters.json"
    try:
        with open(ui_params_path, 'r', encoding='utf-8') as f:
            ui_params = json.load(f)
        return jsonify({
            'parameters': ui_params.get('parameters', {}),
            'parameter_groups': ui_params.get('parameter_groups', [])
        })
    except Exception as e:
        app.logger.error(f"Failed to load parameters: {e}")
        return jsonify({'error': 'Failed to load parameters'}), 500


@app.route('/api/generate', methods=['POST'])
def generate_melody():
    """Generate a melody based on provided parameters"""
    # Rate limiting: 10 requests per minute per IP
    client_ip = request.remote_addr or 'unknown'
    if not rate_limiter.is_allowed(client_ip):
        return jsonify({'error': 'Rate limit exceeded. Please wait and try again.'}), 429

    cleanup_old_files()
    try:
        data = request.get_json() or {}

        # Validate maqam_id and iqa_id up front so a typo returns 400
        # instead of silently falling back to defaults.
        maqam_id = data.get("maqam_selection") or data.get("maqam", "bayati")
        if maqam_id not in data_loader.maqamat:
            return jsonify({
                'error': f'Unknown maqam: {maqam_id}',
                'valid_maqamat': sorted(data_loader.maqamat.keys()),
            }), 400
        iqa_id = data.get("iqa_selection") or data.get("iqa", "maqsum")
        if iqa_id not in data_loader.iqaat:
            return jsonify({
                'error': f'Unknown iqa: {iqa_id}',
                'valid_iqaat': sorted(data_loader.iqaat.keys()),
            }), 400

        # Pass full UI JSON through to create_generator_from_ui_params
        # which maps all 20+ UI parameters to GeneratorParams fields.
        # Also accept legacy field names for backward compatibility.
        generator = create_generator_from_ui_params(data)
        params = generator.params

        # Generate unique filename
        file_id = str(uuid.uuid4())[:8]
        output_filename = f"maqam_{params.maqam_id}_{file_id}.musicxml"
        output_path = TEMP_DIR / output_filename

        # Generate melody
        include_percussion = data.get('include_percussion', True)
        generate_and_export(params, str(output_path), include_percussion,
                            data=data_loader)

        # Read the generated file
        with open(output_path, 'r', encoding='utf-8') as f:
            musicxml_content = f.read()

        # Get maqam and iqa names for display
        maqam_name = data_loader.maqamat.get(params.maqam_id, {}).get('name', params.maqam_id)
        iqa_name = data_loader.iqaat.get(params.iqa_id, {}).get('name', params.iqa_id)

        return jsonify({
            'success': True,
            'file_id': file_id,
            'filename': output_filename,
            'musicxml': musicxml_content,
            'title': f"{maqam_name} with {iqa_name}",
            'maqam': params.maqam_id,
            'iqa': params.iqa_id
        })

    except Exception as e:
        app.logger.error(f"Generation failed: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'Melody generation failed. Please check your parameters and try again.'
        }), 500


@app.route('/api/download/<file_id>', methods=['GET'])
def download_file(file_id):
    """Download a generated MusicXML file"""
    try:
        # Sanitize file_id: only allow alphanumeric characters and underscores
        safe_id = re.sub(r'[^a-zA-Z0-9_]', '', file_id)
        if not safe_id or safe_id != file_id:
            return jsonify({'error': 'Invalid file ID'}), 400

        # Construct expected path and verify it stays under TEMP_DIR
        for file in TEMP_DIR.glob(f"*_{safe_id}.musicxml"):
            resolved = file.resolve()
            if not str(resolved).startswith(str(TEMP_DIR.resolve())):
                return jsonify({'error': 'Invalid file path'}), 400
            return send_file(
                resolved,
                mimetype='application/vnd.recordare.musicxml+xml',
                as_attachment=True,
                download_name=file.name
            )
        return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        return jsonify({'error': 'Download failed'}), 500


@app.route('/api/maqam/<maqam_id>', methods=['GET'])
def get_maqam_details(maqam_id):
    """Get detailed information about a specific maqam"""
    maqam = data_loader.maqamat.get(maqam_id)
    if not maqam:
        return jsonify({'error': 'Maqam not found'}), 404

    return jsonify({
        'id': maqam_id,
        'name': maqam.get('name', maqam_id),
        'family': maqam.get('family', 'unknown'),
        'characteristics': maqam.get('characteristics', {}),
        'description': maqam.get('description', ''),
        'tonic': maqam.get('tonic', 'D'),
        'scale_notes': maqam.get('musicxml', {}).get('scale_notes', []),
        'ajnas': maqam.get('ajnas', []),
        'important_degrees': maqam.get('important_degrees', {}),
        'modulation_targets': maqam.get('modulation_targets', {})
    })


@app.route('/api/iqa/<iqa_id>', methods=['GET'])
def get_iqa_details(iqa_id):
    """Get detailed information about a specific iqa"""
    iqa = data_loader.iqaat.get(iqa_id)
    if not iqa:
        return jsonify({'error': 'Iqa not found'}), 404

    return jsonify({
        'id': iqa_id,
        'name': iqa.get('name', iqa_id),
        'time_signature': iqa.get('time_signature', {}),
        'characteristics': iqa.get('characteristics', {}),
        'description': iqa.get('description', ''),
        'pattern': iqa.get('pattern', {})
    })


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
