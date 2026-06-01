"""
Research Agent — Main Entry Point

Run this file to start the entire application:
    python main.py

This script handles:
    1. Virtual environment check
    2. Dependency installation (first run)
    3. Database initialization
    4. Starting the Flask server
"""

import os
import sys
import subprocess

# ─── Path Setup ───────────────────────────────────────────────────
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')
VENV_DIR = os.path.join(BACKEND_DIR, 'venv')
REQUIREMENTS = os.path.join(BACKEND_DIR, 'requirements.txt')

# Determine venv python/pip paths based on OS
if sys.platform == 'win32':
    VENV_PYTHON = os.path.join(VENV_DIR, 'Scripts', 'python.exe')
    VENV_PIP = os.path.join(VENV_DIR, 'Scripts', 'pip.exe')
else:
    VENV_PYTHON = os.path.join(VENV_DIR, 'bin', 'python')
    VENV_PIP = os.path.join(VENV_DIR, 'bin', 'pip')


def print_banner():
    """Print a startup banner."""
    print()
    print("  ========================================")
    print("    Research Agent - AI Research Platform  ")
    print("  ========================================")
    print()


def check_venv():
    """Check if the virtual environment exists, create it if not."""
    if os.path.exists(VENV_PYTHON):
        return True

    print("  [1/3] Creating virtual environment...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'venv', VENV_DIR],
            check=True
        )
        print("        Virtual environment created.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Failed to create virtual environment: {e}")
        return False


def install_dependencies():
    """Install Python dependencies from requirements.txt."""
    if not os.path.exists(REQUIREMENTS):
        print("  WARNING: requirements.txt not found, skipping install.")
        return True

    print("  [2/3] Installing dependencies...")
    try:
        subprocess.run(
            [VENV_PIP, 'install', '-r', REQUIREMENTS, '-q'],
            check=True
        )
        print("        Dependencies installed.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"  ERROR: Failed to install dependencies: {e}")
        return False


def setup_env():
    """Copy .env.example to .env if .env doesn't exist."""
    env_file = os.path.join(BACKEND_DIR, '.env')
    env_example = os.path.join(BACKEND_DIR, '.env.example')

    if not os.path.exists(env_file) and os.path.exists(env_example):
        import shutil
        shutil.copy2(env_example, env_file)
        print("  INFO: Created .env from .env.example")
        print("        Edit backend/.env to set your API keys.")


def start_server():
    """Start the Flask development server."""
    print("  [3/3] Starting Flask server...")
    print()
    print("  ----------------------------------------")
    print("    Server:  http://localhost:5000")
    print("    Health:  http://localhost:5000/api/health")
    print("    Press Ctrl+C to stop")
    print("  ----------------------------------------")
    print()

    # Set environment variables
    env = os.environ.copy()
    env['FLASK_APP'] = 'run.py'
    env['PYTHONIOENCODING'] = 'utf-8'

    try:
        subprocess.run(
            [VENV_PYTHON, 'run.py'],
            cwd=BACKEND_DIR,
            env=env
        )
    except KeyboardInterrupt:
        print("\n  Server stopped.")


def main():
    """Main entry point — sets up environment and starts the server."""
    # Fix Windows console encoding
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print_banner()

    # Step 1: Ensure virtual environment exists
    if not check_venv():
        sys.exit(1)

    # Step 2: Install dependencies (only if venv was just created or flag set)
    # We check if Flask is importable to skip unnecessary installs
    check_cmd = subprocess.run(
        [VENV_PYTHON, '-c', 'import flask'],
        capture_output=True
    )
    if check_cmd.returncode != 0:
        if not install_dependencies():
            sys.exit(1)
    else:
        print("  [1/3] Virtual environment ready.")
        print("  [2/3] Dependencies already installed.")

    # Step 3: Ensure .env exists
    setup_env()

    # Step 4: Start the server
    start_server()


if __name__ == '__main__':
    main()
