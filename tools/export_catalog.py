"""Discover chapter.json files and generate the complete public deck catalog."""
from __future__ import annotations

import argparse
from hashlib import sha256
from html import escape
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(path, default=None):
    return json.loads(path.read_text()) if path.exists() else default


def text(value):
    return escape(str(value)).replace('\n', '<br>')


def build_chapter(definition):
    meta = read(definition)
    if not all(isinstance(meta.get(k), str) and meta[k].strip() for k in ('deck_id', 'title')):
        raise ValueError(f'{definition}: deck_idとtitleを指定してください')
    folder = definition.parent / 'data'
    if not folder.is_dir():
        folder = definition.parent
    records = read(folder / 'cards.json', [])
    if not records:
        return None
    knowledge = {item['id']: item for item in read(folder / 'knowledge.json', [])}
    sources = read(folder / 'sources.json', {})
    policy = read(folder / 'review_policy.json', {})
    sections = {s['id']: s['title'] for s in policy.get('sections', [])}
    if knowledge:
        records = sorted(records, key=lambda c: (
            knowledge[c['knowledge_ids'][0]]['section'], c['knowledge_ids'][0],
            not c['id'].endswith('-B'), c['id']))
    cards = []
    for card in records:
        if not all(isinstance(card.get(k), str) and card[k].strip() for k in ('id', 'question', 'answer')):
            raise ValueError(f'{definition}: カードのid・question・answerが必要です')
        facts = [knowledge[k] for k in card.get('knowledge_ids', [])]
        links = card.get('sources', []) + [sources[s]['url'] for f in facts for s in f.get('source_ids', [])]
        answer = '<div class="answer-text">' + text(card['answer']) + '</div>'
        if card.get('required'):
            answer += '<div class="answer-criteria"><div class="answer-heading">正解に必要な要素</div><ul>'
            answer += ''.join('<li>' + text(value) + '</li>' for value in card['required']) + '</ul></div>'
        if card.get('accepted'):
            answer += '<div class="answer-accepted"><div class="answer-heading">許容表現の例</div>' + text('、'.join(card['accepted'])) + '</div>'
        if card.get('explanation'):
            answer += '<div class="answer-explanation"><div class="answer-heading">補足</div>' + text(card['explanation']) + '</div>'
        if facts:
            answer += '<details class="answer-details"><summary>前提・対応する知識</summary><p>カード：' + text(card['id']) + '<br>知識：' + text('、'.join(card['knowledge_ids'])) + '</p>'
            answer += ''.join('<p>' + text(f.get('conditions', '')) + '</p>' for f in facts) + '</details>'
        section = facts[0]['section'] if facts else card.get('section', '')
        cards.append({'id': card['id'], 'question': text(card['question']), 'answer': answer,
                      'html': True, 'section': section, 'section_title': card.get('section_title', sections.get(section, '')),
                      'sources': list(dict.fromkeys(links)), 'kind': card.get('kind', ''),
                      'knowledge_ids': card.get('knowledge_ids', [])})
    if len({c['id'] for c in cards}) != len(cards):
        raise ValueError(f'{definition}: カードIDが重複しています')
    files = [definition] + [folder / name for name in ('cards.json', 'knowledge.json', 'sources.json', 'review_policy.json') if (folder / name).exists()]
    revision = sha256(b'\0'.join(p.read_bytes() for p in files)).hexdigest()
    return {'deck_id': meta['deck_id'], 'revision': revision, 'title': meta['title'],
            'subtitle': meta.get('subtitle', ''), 'knowledge_count': len(knowledge),
            'question_count': len(cards), 'sections': len(sections) or len({c['section_title'] for c in cards if c['section_title']}),
            'cards': cards}


def build_catalog(root):
    definitions = sorted(p for p in root.rglob('chapter.json')
                         if not any(part.startswith('.') for part in p.relative_to(root).parts))
    decks = [deck for path in definitions if (deck := build_chapter(path)) is not None]
    decks.sort(key=lambda deck: deck['deck_id'])
    if not decks:
        raise ValueError('公開する章がありません。以前の公開データを維持します')
    if len({deck['deck_id'] for deck in decks}) != len(decks):
        raise ValueError('章のdeck_idが重複しています')
    revision = sha256('\n'.join(deck['deck_id'] + ':' + deck['revision'] for deck in decks).encode()).hexdigest()
    return {'revision': revision, 'decks': decks}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    catalog = build_catalog(args.root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(catalog, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps({'file': str(args.output), 'chapters': len(catalog['decks']),
                      'cards': sum(len(deck['cards']) for deck in catalog['decks'])}, ensure_ascii=False))
