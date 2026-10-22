#!/usr/bin/env python3
"""Trim a local source into a silent, seek-friendly homepage MP4."""
import argparse
from pathlib import Path
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('source', type=Path)
parser.add_argument('--start', type=float, required=True, help='First second of the selected shot')
parser.add_argument('--duration', type=float, required=True, help='Selected shot length, 1–20 seconds')
parser.add_argument('--activate', action='store_true', help='Connect the prepared file to the homepage')
args = parser.parse_args()
if not args.source.is_file() or args.start < 0 or not 1 <= args.duration <= 20:
    parser.error('Provide an existing source, nonnegative start and duration between 1 and 20 seconds.')
root = Path(__file__).resolve().parents[1]
out = root / 'assets/pour-scroll.mp4'
temporary = out.with_name('pour-scroll.processing.mp4')
try:
    subprocess.run(['ffmpeg', '-hide_banner', '-loglevel', 'error', '-y', '-ss', str(args.start),
                    '-i', str(args.source.resolve()), '-t', str(args.duration), '-an',
                    '-vf', "scale=w='min(1440,iw)':h=-2,fps=24", '-c:v', 'libx264',
                    '-preset', 'medium', '-crf', '22', '-pix_fmt', 'yuv420p',
                    '-g', '6', '-keyint_min', '6', '-sc_threshold', '0',
                    '-movflags', '+faststart', str(temporary)], check=True)
    temporary.replace(out)
finally:
    temporary.unlink(missing_ok=True)
if args.activate:
    page = root / 'index.html'
    html = page.read_text()
    html = html.replace('class="photo-scene-video" data-src=""',
                        'class="photo-scene-video" data-src="assets/pour-scroll.mp4"')
    page.write_text(html)
print(f'Prepared {out} ({out.stat().st_size / 1024 / 1024:.1f} MB)')
