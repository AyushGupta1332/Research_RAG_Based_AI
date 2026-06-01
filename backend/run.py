"""
Research Agent — Application Entry Point

Run with: python run.py
"""

import os
import sys

# Fix Windows console encoding
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add the backend directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app

app = create_app()

if __name__ == '__main__':
    host = app.config.get('HOST', '0.0.0.0')
    port = app.config.get('PORT', 5000)
    debug = app.config.get('DEBUG', True)

    mode = 'Development' if debug else 'Production'
    print(f"\n  Research Agent - Starting Up")
    print(f"  ----------------------------")
    print(f"  Server:  http://{host}:{port}")
    print(f"  Mode:    {mode}")
    print(f"  Health:  http://localhost:{port}/api/health")
    print(f"  ----------------------------\n")

    app.run(host=host, port=port, debug=debug)
