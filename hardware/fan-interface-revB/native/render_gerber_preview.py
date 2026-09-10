"""Render unmodified manufacturing ZIP with Gerbonara 1.6.3 / Python 3.12."""
import subprocess
import sys
from pathlib import Path

root = Path(sys.argv[1]).resolve()
for side in ['top', 'bottom']:
    svg = root/f'gerber-{side}.svg'
    subprocess.run([sys.executable, '-m', 'gerbonara', 'pretty', '--'+side,
                    str(root/'GB10-Fan-RevB-20260909.zip'), str(svg)], check=True)
print('Rendered SVGs directly from unmodified manufacturing ZIP. Use render_svg_png.cjs for PNGs.')
