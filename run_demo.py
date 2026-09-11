"""Convenience launcher: uses project-local demo dependencies if available."""
import os
import sys
from pathlib import Path

root = Path(__file__).resolve().parent
packages = root.parent.parent / 'work' / 'packages'
if packages.exists():
    sys.path.insert(0, str(packages))
sys.path.insert(0, str(root))
os.chdir(root)
from streamlit.web import cli

sys.argv = ['streamlit', 'run', str(root / 'app.py'), '--server.address=127.0.0.1', '--server.headless=true', '--browser.gatherUsageStats=false']
cli.main()
