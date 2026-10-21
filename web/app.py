"""
Maqamatic Web Application - Flask Backend
A modern web interface for Arabic Maqam melody generation.
"""

import os
import uuid
from pathlib import Path
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix

# Add parent directory to path for imports
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from maqam_generator import MaqamGenerator, DataLoader
from params_expanded import (GeneratorParams, ParamValidationError,
                             create_generator_from_ui_params, sanitize_ui_values)
from generator_to_musicxml import generate_musicxml

app = Flask(__name__,
            static_folder='static',
            template_folder='templates')

# Audit R2-02: in production the app sits behind the Azure Container Apps
# ingress proxy, so request.remote_addr is the proxy, not the user, and the
# per-IP rate limiter became one shared global bucket. Trust the
# X-Forwarded-For entries added by that many proxy hops (1 on Azure). Set
# TRUSTED_PROXY_HOPS=0 when running without a proxy so clients can't spoof it.
TRUSTED_PROXY_HOPS = int(os.environ.get('TRUSTED_PROXY_HOPS', '1'))
if TRUSTED_PROXY_HOPS > 0:
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=TRUSTED_PROXY_HOPS,
                            x_proto=TRUSTED_PROXY_HOPS)

# Audit R2-03: a generation request is a small JSON object; refuse bodies
# larger than this outright.
app.config['MAX_CONTENT_LENGTH'] = 64 * 1024
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
# Load every data file once at startup. Requests (and the generator, see
# create_generator_from_ui_params(data=...)) share this read-only copy
# instead of re-reading the JSON per request from a relative path (R2-13).
for _name in ("maqamat", "ajnas", "iqaat", "sayr_definitions",
              "transition_matrices", "generator_config", "ui_parameters"):
    getattr(data_loader, _name)

@app.route('/')
def index():
    """Serve the main application page"""
    return render_template('index.html')


_ACCIDENTALS = {-1.5: '\u00be\u266d', -1: '\u266d', -0.5: '\u00bd\u266d',
                0: '', 0.5: '\u00bd\u266f', 1: '\u266f', 1.5: '\u00be\u266f'}


def _tonic(maqam_data):
    """Tonic as written in the score, e.g. 'D4' or 'E\u00bd\u266d4' (R2-14)."""
    notes = maqam_data.get('musicxml', {}).get('scale_notes', [])
    if not notes:
        return None
    n = notes[0]
    return f"{n['step']}{_ACCIDENTALS.get(n.get('alter', 0), '')}{n['octave']}"


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
            'tonic': _tonic(maqam_data)
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
            'characteristics': iqa_data.get('characteristics', {})
        })
    return jsonify(iqaat)


@app.route('/api/presets', methods=['GET'])
def get_presets():
    """Get available generation presets"""
    try:
        return jsonify(data_loader.ui_parameters.get('presets', {}))
    except Exception as e:
        app.logger.error(f"Failed to load presets: {e}")
        return jsonify({'error': 'Failed to load presets'}), 500


@app.route('/api/parameters', methods=['GET'])
def get_parameters():
    """Get UI parameter definitions"""
    try:
        ui_params = data_loader.ui_parameters
        return jsonify({
            'parameters': ui_params.get('parameters', {}),
            'parameter_groups': ui_params.get('parameter_groups', [])
        })
    except Exception as e:
        app.logger.error(f"Failed to load parameters: {e}")
        return jsonify({'error': 'Failed to load parameters'}), 500


def _bad_request(message, **extra):
    return jsonify({'success': False, 'error': message, **extra}), 400


@app.errorhandler(413)
def payload_too_large(_error):
    return jsonify({'success': False,
                    'error': 'Request body is too large.'}), 413


@app.route('/api/generate', methods=['POST'])
def generate_melody():
    """Generate a melody based on provided parameters"""
    # Rate limiting: 10 requests per minute per IP
    client_ip = request.remote_addr or 'unknown'
    if not rate_limiter.is_allowed(client_ip):
        return jsonify({'success': False,
                        'error': 'Rate limit exceeded. Please wait and try again.'}), 429

    # Audit R2-11: malformed or mistyped input is the client's error (400),
    # not a server failure (500).
    data = request.get_json(silent=True)
    if data is None:
        if request.get_data(cache=True):
            return _bad_request('Request body must be valid JSON.')
        data = {}
    if not isinstance(data, dict):
        return _bad_request('Request body must be a JSON object.')
    try:
        data = sanitize_ui_values(
            data,
            data_loader.ui_parameters.get('parameters', {}),
            valid_forms=data_loader.generator_config.get(
                'structure_grammar', {}).get('base_forms', {}).keys())
    except ParamValidationError as e:
        return _bad_request(str(e), field=e.field)

    try:
        # Validate maqam_id and iqa_id up front so a typo returns 400
        # instead of silently falling back to defaults.
        maqam_id = data.get("maqam_selection") or data.get("maqam", "bayati")
        if maqam_id not in data_loader.maqamat:
            return jsonify({
                'success': False,
                'error': f'Unknown maqam: {maqam_id}',
                'valid_maqamat': sorted(data_loader.maqamat.keys()),
            }), 400
        iqa_id = data.get("iqa_selection") or data.get("iqa", "maqsum")
        if iqa_id not in data_loader.iqaat:
            return jsonify({
                'success': False,
                'error': f'Unknown iqa: {iqa_id}',
                'valid_iqaat': sorted(data_loader.iqaat.keys()),
            }), 400

        # Pass full UI JSON through to create_generator_from_ui_params
        # which maps all 20+ UI parameters to GeneratorParams fields.
        # Also accept legacy field names for backward compatibility.
        params = create_generator_from_ui_params(data, data=data_loader).params

        # The score is built in memory and returned in the response; the UI
        # saves it client-side, so nothing is written to disk (R2-13).
        file_id = str(uuid.uuid4())[:8]
        output_filename = f"maqam_{params.maqam_id}_{file_id}.musicxml"
        include_percussion = data.get('include_percussion', True)
        musicxml_content = generate_musicxml(params, include_percussion,
                                             data=data_loader)

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
        'tonic': _tonic(maqam),
        'scale_notes': maqam.get('musicxml', {}).get('scale_notes', []),
        'ajnas': maqam.get('ajnas', []),
        'important_degrees': maqam.get('important_degrees', {}),
        'modulations': maqam.get('modulations', {}).get('common_modulations', [])
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
        'pattern': iqa.get('pattern', {})
    })


@app.after_request
def add_no_cache_headers(response):
    """Prevent the browser from caching the HTML and JS during
    development / hot-fix deploys. Otherwise users see the old
    "Failed to fetch" alert even after we ship a fix.
    """
    if request.path.endswith('.html') or request.path == '/' \
       or '/static/js/' in request.path or '/static/css/' in request.path:
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'
    return response


if __name__ == '__main__':
    # Audit F-9: never hard-code debug=True. Production serves via
    # gunicorn (which doesn't run this block); for local use, opt into
    # the Flask debugger explicitly with FLASK_DEBUG=1.
    debug = os.environ.get('FLASK_DEBUG', '').lower() in ('1', 'true', 'yes')
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=debug, host='0.0.0.0', port=port)
