"""Host-side real process restart suite. Requires Python 3 and running Docker."""
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]
COMPOSE = ['docker', 'compose', '-f', 'lab/compose.yaml']

def run(*args, **kwargs):
    return subprocess.run(COMPOSE + list(args), cwd=ROOT, check=True, **kwargs)

def ready():
    end = time.monotonic() + 120
    while time.monotonic() < end:
        result = subprocess.run(COMPOSE + ['exec', '-T', 'ha', 'python', '-c',
            "import sys;sys.path.insert(0,'/lab');import smoke;assert smoke.state('binary_sensor.heating_lab_ready')['state']=='on';assert smoke.state('input_boolean.heating_controller_ready')['state']=='on'"],
            cwd=ROOT, capture_output=True)
        if result.returncode == 0:
            return
        time.sleep(2)
    raise RuntimeError('Lab HA not ready within 120 seconds; inspect compose logs ha')

if __name__ == '__main__':
    ready()
    run('exec', '-T', 'ha', 'python', '/lab/smoke.py', 'scenarios')
    run('exec', '-T', 'ha', 'python', '/lab/smoke.py', 'prepare-restart')
    run('restart', 'ha')
    ready()
    run('exec', '-T', 'ha', 'python', '/lab/smoke.py', 'verify-restart')
    run('exec', '-T', 'ha', 'python', '/lab/smoke.py', 'prepare-expired-restart')
    run('stop', 'ha')
    time.sleep(16)
    run('start', 'ha')
    ready()
    run('exec', '-T', 'ha', 'python', '/lab/smoke.py', 'verify-expired-restart')
    print('All live lab checks passed; heating is disabled.')
