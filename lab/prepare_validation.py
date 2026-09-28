"""Stage production YAML for offline HA check_config with dummy location secrets."""
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'lab/.runtime/production-check'
shutil.copytree(ROOT/'homeassistant/locations/house', OUT, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns('secrets.yaml', '.storage', '*.db*'))
(OUT/'themes').mkdir(exist_ok=True)
(OUT/'secrets.yaml').write_text('house_latitude: 50.0\nhouse_longitude: 14.0\nhouse_elevation: 200\n')
print('Prepared offline production configuration check.')
