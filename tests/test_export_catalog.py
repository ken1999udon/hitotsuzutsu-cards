import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tools'))
from export_catalog import build_catalog


def add_chapter(root, number, cards):
    folder = root / 'chapters' / f'chapter{number:02d}'
    (folder / 'data').mkdir(parents=True)
    (folder / 'chapter.json').write_text(json.dumps({'deck_id': f'chapter-{number:02d}', 'title': f'第{number}章'}))
    (folder / 'data/cards.json').write_text(json.dumps(cards))
    return folder


class CatalogTest(unittest.TestCase):
    def test_rich_chapter_in_any_folder_includes_criteria_sources_and_sections(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            card = {'id': 'Q01', 'question': '問題', 'answer': '短い解答',
                    'knowledge_ids': ['K1'], 'required': ['要素'], 'explanation': '補足'}
            folder = add_chapter(root, 1, [card]) / 'data'
            (folder / 'knowledge.json').write_text(json.dumps([{'id': 'K1', 'section': '01', 'source_ids': ['S1'], 'conditions': '前提'}]))
            (folder / 'sources.json').write_text(json.dumps({'S1': {'url': 'https://example.com/source'}}))
            (folder / 'review_policy.json').write_text(json.dumps({'sections': [{'id': '01', 'title': '節の名前'}]}))
            chapter = build_catalog(root)['decks'][0]
            self.assertEqual(chapter['deck_id'], 'chapter-01')
            self.assertEqual(chapter['cards'][0]['section_title'], '節の名前')
            self.assertIn('正解に必要な要素', chapter['cards'][0]['answer'])
            self.assertIn('補足', chapter['cards'][0]['answer'])
            self.assertEqual(chapter['cards'][0]['sources'], ['https://example.com/source'])

    def test_new_chapters_are_discovered_and_edits_change_the_revision(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            card = {'id': 'Q01', 'question': '問題', 'answer': '答え'}
            chapter9 = add_chapter(root, 9, [card])
            add_chapter(root, 4, [card])
            add_chapter(root, 5, [])
            before = build_catalog(root)
            self.assertEqual([d['deck_id'] for d in before['decks']], ['chapter-04', 'chapter-09'])
            (chapter9 / 'data/cards.json').write_text(json.dumps([card, {**card, 'id': 'Q02'}]))
            after = build_catalog(root)
            self.assertNotEqual(before['revision'], after['revision'])
            self.assertEqual(len(after['decks'][1]['cards']), 2)

    def test_duplicate_chapter_and_card_ids_are_rejected(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            card = {'id': 'Q01', 'question': '問題', 'answer': '答え'}
            folder = add_chapter(root, 4, [card, card])
            with self.assertRaises(ValueError):
                build_catalog(root)
            (folder / 'data/cards.json').write_text(json.dumps([card]))
            other = add_chapter(root, 5, [card])
            (other / 'chapter.json').write_text((folder / 'chapter.json').read_text())
            with self.assertRaises(ValueError):
                build_catalog(root)


if __name__ == '__main__':
    unittest.main()
