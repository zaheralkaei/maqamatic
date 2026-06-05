#!/usr/bin/env python3
"""
Maqamatic - Quick Start Script
Run this to start the web application locally.
"""

import os
import sys
import webbrowser
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def main():
    print("""
    ╔══════════════════════════════════════════════════════════╗
    ║                                                          ║
    ║     ███╗   ███╗ █████╗  ██████╗  █████╗ ███╗   ███╗     ║
    ║     ████╗ ████║██╔══██╗██╔═══██╗██╔══██╗████╗ ████║     ║
    ║     ██╔████╔██║███████║██║   ██║███████║██╔████╔██║     ║
    ║     ██║╚██╔╝██║██╔══██║██║▄▄ ██║██╔══██║██║╚██╔╝██║     ║
    ║     ██║ ╚═╝ ██║██║  ██║╚██████╔╝██║  ██║██║ ╚═╝ ██║     ║
    ║     ╚═╝     ╚═╝╚═╝  ╚═╝ ╚══▀▀═╝ ╚═╝  ╚═╝╚═╝     ╚═╝     ║
    ║                                                          ║
    ║           Arabic Maqam Melody Generator                  ║
    ║                    مقامات عربية                          ║
    ║                                                          ║
    ╚══════════════════════════════════════════════════════════╝
    """)

    print("Starting Maqamatic web server...")
    print("=" * 60)

    # Check dependencies
    try:
        from flask import Flask
        from flask_cors import CORS
    except ImportError:
        print("\n⚠️  Missing dependencies. Installing...")
        os.system(f"{sys.executable} -m pip install flask flask-cors")
        print("Dependencies installed. Please run again.\n")
        return

    # Import and run the app
    os.chdir(project_root)

    from web.app import app

    url = "http://localhost:5025"
    print(f"\n🎵 Maqamatic is running at: {url}")
    print("   Press Ctrl+C to stop the server\n")

    # Open browser after a short delay
    import threading
    threading.Timer(1.5, lambda: webbrowser.open(url)).start()

    # Run the Flask app
    app.run(debug=True, host='0.0.0.0', port=5025, use_reloader=False)


if __name__ == '__main__':
    main()
