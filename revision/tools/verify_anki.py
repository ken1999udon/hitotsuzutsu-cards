"""Import and render the real APKG with Anki's own backend, in a temporary profile."""
from __future__ import annotations

from html import unescape
import json
from pathlib import Path
import re
from tempfile import TemporaryDirectory

from anki.collection import Collection
from anki.import_export_pb2 import ImportAnkiPackageOptions, ImportAnkiPackageRequest

from build_deck import DATA, DIST, read


def plain(value):
    value = re.sub(r"<style.*?</style>", "", value, flags=re.DOTALL)
    return unescape(re.sub(r"<[^>]*>", "", value))


def main():
    package = next(DIST.glob("*.apkg"))
    source = {c["id"]: c for c in read("cards.json")}
    preview = {}
    with TemporaryDirectory(prefix="nw-anki-verification-") as tmp:
        col = Collection(str(Path(tmp) / "collection.anki2"))
        try:
            request = ImportAnkiPackageRequest(
                package_path=str(package.resolve()),
                options=ImportAnkiPackageOptions(with_scheduling=False, with_deck_configs=False),
            )
            col.import_anki_package(request)
            assert col.note_count() == col.card_count() == len(source)
            assert col.db.scalar("SELECT count(*) FROM revlog") == 0
            for card_id in col.find_cards(""):
                card = col.get_card(card_id)
                note = card.note()
                record = source[note["ID"]]
                question, answer = plain(card.question()), plain(card.answer())
                assert record["question"] in question
                assert record["answer"] in answer
                assert "正解に必要な要素" in answer
                assert "正解に必要な要素" not in question
                assert "{{" not in question and "{{" not in answer
                assert card.type == card.queue == card.reps == 0
                assert note["問題"] == record["question"]
                for required in record["required"]:
                    assert required in answer
                if note["ID"] in ["K03-044-A2", "K03-073-A1", "K03-030a-B"]:
                    preview[note["ID"]] = {
                        "front": '<div class="card">' + card.question() + '</div>',
                        "back": '<div class="card">' + card.answer() + '</div>',
                    }
            # Anki must match GUIDs on re-import, and retain existing review state.
            selected_id = col.find_cards("")[0]
            selected = col.get_card(selected_id)
            selected.type = selected.queue = 2
            selected.ivl = 10
            selected.reps = 5
            col.update_card(selected)
            col.import_anki_package(request)
            assert col.note_count() == col.card_count() == len(source)
            selected = col.get_card(selected_id)
            assert (selected.type, selected.queue, selected.ivl, selected.reps) == (2, 2, 10, 5)
            result = {
                "anki_backend_version": "26.9.4",
                "fresh_import_notes": len(source), "fresh_import_cards": len(source),
                "all_cards_rendered": True, "no_unexpanded_template_fields": True,
                "reimport_duplicates": 0, "reimport_preserves_existing_review_state": True,
                "profile": "temporary profile only", "gui_import_test": False,
            }
        finally:
            col.close()
    (DIST / "anki_import_validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    # Real Anki-rendered samples, used for desktop/mobile visual inspection.
    preview_html = (
        '<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>カード表示サンプル</title>'
        + ''.join('<section style="border:1px solid #cbd5e1;margin:20px 0"><p>' + key + '：表</p>' + value['front']
                  + '<p>' + key + '：裏</p>' + value['back'] + '</section>' for key, value in preview.items()))
    (DIST / "カード表示サンプル.html").write_text(
        "\n".join(line.rstrip() for line in preview_html.splitlines()) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
