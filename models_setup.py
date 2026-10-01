"""Download official Vosk models into a writable app folder; no arbitrary URLs or archive paths."""
import hashlib
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile
from pathlib import Path

MODELS = ('vosk-model-el-gr-0.7', 'vosk-model-small-en-us-0.15')
CATALOG = 'https://alphacephei.com/vosk/models/model-list.json'
ROOT = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
DEST = ROOT / 'models'


def catalog_entries(data):
    if isinstance(data, list):
        for item in data:
            yield from catalog_entries(item)
    elif isinstance(data, dict):
        if 'name' in data and 'url' in data:
            yield data
        for key, value in data.items():
            if isinstance(value, (dict, list)):
                yield from catalog_entries(value)


def download(name, entry):
    DEST.mkdir(parents=True, exist_ok=True)
    target = DEST/name
    if (target/'am'/'final.mdl').is_file():
        print(f'Already installed: {name}', flush=True)
        return
    url = str(entry['url'])
    if not (url.startswith('https://alphacephei.com/vosk/models/') or
            url.startswith('https://alphacephei.com/vosk/models/')):
        raise RuntimeError(f'Unexpected download URL; check the official catalog manually: {url}')
    expected = str(entry.get('md5', '')).lower()
    if len(expected) != 32:
        raise RuntimeError(f'No MD5 hash supplied for {name}; cannot verify download')
    print(f'Downloading {name} from official Vosk catalog...', flush=True)
    with tempfile.TemporaryDirectory(prefix='badwordbeep-', dir=DEST) as tmp:
        zip_path = Path(tmp)/'model.zip'
        req = urllib.request.Request(url, headers={'User-Agent': 'BadWordBeep/1.0'})
        h = hashlib.md5()
        total = 0
        with urllib.request.urlopen(req, timeout=90) as response, zip_path.open('wb') as f:
            while True:
                block = response.read(1024*1024)
                if not block:
                    break
                f.write(block)
                h.update(block)
                total += len(block)
                if total // (100*1024*1024) != (total-len(block)) // (100*1024*1024):
                    print(f'  {total/(1024*1024):.0f} MiB downloaded', flush=True)
        if h.hexdigest().lower() != expected:
            raise RuntimeError(f'Hash mismatch for {name}; refusing to extract (expected {expected}, got {h.hexdigest()})')
        print(f'Verified {name} ({total/(1024*1024):.0f} MiB). Extracting...', flush=True)
        staging = Path(tmp)/'staging'
        staging.mkdir()
        with zipfile.ZipFile(zip_path) as z:
            for info in z.infolist():
                path = Path(info.filename)
                if path.is_absolute() or '..' in path.parts or not path.parts or path.parts[0] != name:
                    raise RuntimeError(f'Unexpected archive path: {info.filename}')
                if info.is_dir():
                    (staging/path).mkdir(parents=True, exist_ok=True)
                else:
                    dest = staging/path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with z.open(info) as src, dest.open('wb') as dst:
                        shutil.copyfileobj(src, dst)
        extracted = staging/name
        if not (extracted/'am'/'final.mdl').is_file():
            raise RuntimeError(f'Missing am/final.mdl inside {name}')
        if target.exists():
            shutil.rmtree(target)
        shutil.move(str(extracted), str(target))
    print(f'Installed: {target}', flush=True)


def main():
    print(f'Fetching official catalog: {CATALOG}', flush=True)
    with urllib.request.urlopen(CATALOG, timeout=45) as response:
        data = json.load(response)
    found = {x['name']: x for x in catalog_entries(data) if x.get('name') in MODELS}
    for name in MODELS:
        if name not in found:
            raise RuntimeError(f'Model {name} missing from official catalog; download manually from Vosk model page')
        download(name, found[name])
    print('Both models ready. Install VB-CABLE and OBS separately before streaming.', flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception as exc:
        print(f'ERROR: {exc}', file=sys.stderr, flush=True)
        sys.exit(1)
