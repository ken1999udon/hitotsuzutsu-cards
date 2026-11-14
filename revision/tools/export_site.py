"""Export a single chapter through the shared chapter converter."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT.parent / 'tools'))
from export_catalog import build_chapter


def build(output):
    deck = build_chapter(ROOT / 'chapter.json')
    if deck is None:
        raise ValueError('公開するカードがありません')
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(deck, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'file': str(output), 'cards': len(deck['cards'])}, ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT / 'dist/deck.json')
    build(parser.parse_args().output)
