"""
Research Agent — Developer Friendly Bootstrapper

Runs the Flask server directly in the active Python environment.
Usage:
    python main.py
"""

import os
import sys
import subprocess

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
BACKEND_DIR = os.path.join(ROOT_DIR, 'backend')

# Check root first, fallback to backend for requirements.txt
REQUIREMENTS = os.path.join(ROOT_DIR, 'requirements.txt')
if not os.path.exists(REQUIREMENTS):
    REQUIREMENTS = os.path.join(BACKEND_DIR, 'requirements.txt')


def print_banner():
    """Print clean startup banner."""
    print("\n  ========================================")
    print("    Research Agent - AI Research Platform  ")
    print("  ========================================\n")


def check_and_install_dependencies():
    """Check if Flask is installed, install requirements if missing."""
    try:
        import flask
        # If Flask is importable, we assume dependencies are present
        return True
    except ImportError:
        print("  INFO: Flask not found in current environment.")
        choice = input("  Would you like to install dependencies from requirements.txt? (y/n): ").strip().lower()
        if choice == 'y':
            print("  Installing dependencies...")
            try:
                subprocess.run(
                    [sys.executable, '-m', 'pip', 'install', '-r', REQUIREMENTS],
                    check=True
                )
                print("  Dependencies successfully installed.")
                return True
            except subprocess.CalledProcessError as e:
                print(f"  ERROR: Failed to install dependencies: {e}")
                return False
        else:
            print("  Please install packages in requirements.txt manually: pip install -r backend/requirements.txt")
            return False


def setup_env():
    """Create .env from .env.example if missing."""
    env_file = os.path.join(BACKEND_DIR, '.env')
    env_example = os.path.join(BACKEND_DIR, '.env.example')

    if not os.path.exists(env_file) and os.path.exists(env_example):
        import shutil
        shutil.copy2(env_example, env_file)
        print("  INFO: Created backend/.env from .env.example template.")
        print("        Please customize it to set your API keys.")


def start_server():
    """Launch the Flask dev server using the active Python interpreter."""
    print("  Starting Flask server...")
    print("  ----------------------------------------")
    print("    Server URL: http://localhost:5000")
    print("    Health URL: http://localhost:5000/api/health")
    print("    Press Ctrl+C to stop")
    print("  ----------------------------------------\n")

    env = os.environ.copy()
    env['FLASK_APP'] = 'run.py'
    env['PYTHONIOENCODING'] = 'utf-8'

    try:
        subprocess.run(
            [sys.executable, 'run.py'],
            cwd=BACKEND_DIR,
            env=env
        )
    except KeyboardInterrupt:
        print("\n  Server stopped successfully.")


def main():
    """Main entry point."""
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

    print_banner()
    if not check_and_install_dependencies():
        sys.exit(1)

    setup_env()
    start_server()


if __name__ == '__main__':
    main()
