from pathlib import Path
import json
import re
import subprocess

ROOT = Path('m17')
ASSET_DIR = ROOT / 'assets/home/m1.7'
RUNTIME_FILES = [ROOT / 'index.html', ROOT / 'styles.css', ROOT / 'styles-base.css']
PHOTO_MARKERS = ('portrait', 'card-', 'polaroid', 'postcard-photo', 'travel-map')

pngs = sorted(ASSET_DIR.glob('*.png'))
if not pngs:
    raise SystemExit('No public M1.7 PNG assets found')

before = 0
after = 0
for src in pngs:
    dst = src.with_suffix('.webp')
    before += src.stat().st_size
    if any(marker in src.stem for marker in PHOTO_MARKERS):
        cmd = ['cwebp', '-quiet', '-mt', '-m', '6', '-q', '88', '-alpha_q', '100', str(src), '-o', str(dst)]
    else:
        cmd = ['cwebp', '-quiet', '-mt', '-lossless', '-z', '9', str(src), '-o', str(dst)]
    subprocess.run(cmd, check=True)
    after += dst.stat().st_size

if after >= before:
    raise SystemExit(f'WebP payload did not shrink: png={before}, webp={after}')

pattern = re.compile(r'(assets/home/m1\.7/[^\"\'\)\s]+)\.png')
for path in RUNTIME_FILES:
    text = path.read_text(encoding='utf-8')
    text = pattern.sub(r'\1.webp', text)
    path.write_text(text, encoding='utf-8')

manifest_path = ASSET_DIR / 'manifest.json'
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
for asset in manifest.get('assets', []):
    for key in ('production_path', 'public_path'):
        value = asset.get(key)
        if isinstance(value, str) and value.endswith('.png'):
            asset[key] = value[:-4] + '.webp'
manifest['delivery_format'] = 'webp'
manifest['source_master_format'] = 'png'
manifest['webp_asset_count'] = len(pngs)
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')

for path in RUNTIME_FILES:
    text = path.read_text(encoding='utf-8')
    if 'assets/home/m1.7/' in text and '.png' in text:
        bad = [line for line in text.splitlines() if 'assets/home/m1.7/' in line and '.png' in line]
        if bad:
            raise SystemExit(f'Runtime PNG reference remains in {path}: ' + bad[0])

webps = sorted(ASSET_DIR.glob('*.webp'))
if len(webps) != len(pngs):
    raise SystemExit(f'WebP count mismatch: png={len(pngs)}, webp={len(webps)}')

report = (
    f'Converted assets: {len(pngs)}\n'
    f'PNG source bytes: {before}\n'
    f'WebP delivery bytes: {after}\n'
    f'Saved bytes: {before - after}\n'
    f'Reduction: {(1 - after / before) * 100:.2f}%\n'
)
(ROOT / 'WEBP-SIZE-REPORT.txt').write_text(report, encoding='utf-8')
print(report)
