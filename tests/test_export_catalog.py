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
    def test_authoring_metadata_is_kept_out_of_the_learning_answer(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            card = {'id': 'Q01', 'question': '問題', 'answer': '短い解答',
                    'knowledge_ids': ['K1'], 'required': ['要素'], 'explanation': '補足',
                    'accepted': ['許容表現']}
            folder = add_chapter(root, 1, [card]) / 'data'
            (folder / 'knowledge.json').write_text(json.dumps([{'id': 'K1', 'section': '01', 'source_ids': ['S1'], 'conditions': '前提'}]))
            (folder / 'sources.json').write_text(json.dumps({'S1': {'url': 'https://example.com/source'}}))
            (folder / 'review_policy.json').write_text(json.dumps({'deck_title': '本文準拠版', 'sections': [{'id': '01', 'title': '節の名前'}]}))
            chapter = build_catalog(root)['decks'][0]
            self.assertEqual(chapter['deck_id'], 'chapter-01')
            self.assertEqual(chapter['cards'][0]['section_title'], '節の名前')
            self.assertEqual(chapter['title'], '本文準拠版')
            self.assertEqual(chapter['cards'][0]['id'], 'Q01')
            self.assertEqual(chapter['cards'][0]['question'], '問題')
            self.assertEqual(chapter['cards'][0]['answer'], '<div class="answer-text">短い解答</div>')
            self.assertEqual(chapter['cards'][0]['sources'], ['https://example.com/source'])

    def test_learning_text_is_escaped_and_empty_catalog_does_not_replace_output(self):
        import subprocess
        with TemporaryDirectory() as directory:
            root = Path(directory)
            folder = add_chapter(root, 1, [{'id': 'Q01', 'question': '問題 <tag>', 'answer': '答え & 補記'}])
            card = build_catalog(root)['decks'][0]['cards'][0]
            self.assertEqual(card['question'], '問題 &lt;tag&gt;')
            self.assertEqual(card['answer'], '<div class="answer-text">答え &amp; 補記</div>')
            (folder / 'data/cards.json').write_text('[]')
            output = root / 'published.json'
            output.write_text('previous publication')
            result = subprocess.run([sys.executable, str(ROOT / 'tools/export_catalog.py'), '--root', str(root), '--output', str(output)], capture_output=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(output.read_text(), 'previous publication')

    def test_minimal_cards_do_not_require_links_to_older_knowledge_records(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            records = [{'id': 'Q02', 'question': '最初の問題', 'answer': '答え', 'section_title': '本文の節'},
                       {'id': 'Q01', 'question': '次の問題', 'answer': '答え'}]
            folder = add_chapter(root, 3, records) / 'data'
            (folder / 'knowledge.json').write_text(json.dumps([{'id': 'OLD', 'section': '01'}]))
            cards = build_catalog(root)['decks'][0]['cards']
            self.assertEqual([card['id'] for card in cards], ['Q02', 'Q01'])
            self.assertEqual(cards[0]['section_title'], '本文の節')
            self.assertEqual(cards[0]['answer'], '<div class="answer-text">答え</div>')

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
