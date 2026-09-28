"""Portable test command; Docker supplies the pinned HA/Python runtime."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
IMAGE = 'home-automation-heating-tests:2026.9.2'

def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)

if __name__ == '__main__':
    run('docker', 'build', '-f', 'tests/Dockerfile', '-t', IMAGE, '.')
    run('docker', 'run', '--rm', '--network', 'none', '--mount',
        f'type=bind,source={ROOT},target=/workspace', IMAGE, '--tb=short', *sys.argv[1:])
    run(sys.executable, 'lab/prepare_validation.py')
    run('docker', 'run', '--rm', '--network', 'none', '--mount',
        f'type=bind,source={ROOT / "lab/.runtime/production-check"},target=/config',
        'ghcr.io/home-assistant/home-assistant:2026.9.2', 'python', '-m', 'homeassistant',
        '--script', 'check_config', '-c', '/config')
