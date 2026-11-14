"""Build an auditable Chapter 3 deck from separately curated facts and cards.

Run from any directory. No network access is needed for builds.
The source JSON files are the editable authority; the CSV/HTML/APKG are outputs.
"""
from __future__ import annotations

from collections import Counter
import csv
from datetime import datetime, timezone
from html import escape
import json
from pathlib import Path
import re
import sqlite3
import tempfile
import zipfile

import genanki


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DIST = ROOT / "dist"
MODEL_ID = 1988524361
DECK_ID = 1988524362
DECK_NAME = "ネスペイージス::第3章 Ethernet LAN 改訂版"
MODEL_NAME = "ネスペイージス 一問一答 改訂版 v2"
FIELDS = ["ID", "問題", "解答", "必須要素", "補足", "許容表現", "知識ID", "分野", "形式", "優先度", "出典", "過去問接点", "前提"]
FRONT = '<div class="wrap"><div class="label">第3章 Ethernet LAN · {{ID}}</div><div class="question">{{問題}}</div></div>'
BACK = """{{FrontSide}}
<div class="wrap">
  <hr id="answer">
  <div class="label">解答</div><div class="answer-text">{{解答}}</div>
  <div class="label block">正解に必要な要素</div>{{必須要素}}
  {{#許容表現}}<div class="label block">表記の例・許容表現</div>{{許容表現}}{{/許容表現}}
  <div class="label block">補足</div><div class="explanation">{{補足}}</div>
  <details class="references"><summary>前提・出典・対応する知識</summary>
    <p>{{前提}}</p><p>知識ID：{{知識ID}}</p><p>{{分野}} ／ {{形式}} ／ {{優先度}}</p>
    {{出典}}
    {{#過去問接点}}<p class="label">過去問との接点（代表例・頻度ではありません）</p>{{過去問接点}}{{/過去問接点}}
  </details>
</div>"""
CSS = """
.card { font-family: -apple-system, BlinkMacSystemFont, "Noto Sans JP", "Yu Gothic", Meiryo, sans-serif;
  font-size: 21px; line-height: 1.7; text-align: left; color: #1e293b; background: #fff;
  padding: 22px 16px; overflow-wrap: anywhere; }
.wrap { max-width: 780px; margin: 0 auto; }
.label { font-size: 13px; color: #64748b; }
.question { font-weight: 600; margin-top: 14px; }
#answer { border: 0; border-top: 1px solid #cbd5e1; margin: 26px 0 18px; }
.answer-text { color: #075985; font-size: 25px; font-weight: 600; margin-top: 6px; }
.block { margin-top: 22px; }
ul { padding-left: 1.3em; margin-top: 5px; }
.explanation { font-size: 17px; }
.references { font-size: 13px; color: #64748b; margin-top: 25px; }
.references summary { cursor: pointer; }
a { color: #0369a1; }
.nightMode, .night_mode { color: #e2e8f0; background: #172033; }
.nightMode .label, .night_mode .label, .nightMode .references, .night_mode .references { color: #b0c1d5; }
.nightMode .answer-text, .night_mode .answer-text, .nightMode a, .night_mode a { color: #7dd3fc; }
@media (max-width: 480px) { .card { font-size: 19px; padding: 15px 10px; } .answer-text { font-size: 23px; } }
"""


def read(name):
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def text(value):
    return escape(str(value)).replace("\n", "<br>")


def bullets(values):
    return "<ul>" + "".join("<li>" + text(v) + "</li>" for v in values) + "</ul>"


def oracle(scenario, answer):
    """Calculate concrete answers independently of prose and serialized card fields."""
    kind = scenario["type"]
    if kind == "switch":
        table = dict(scenario["table"])
        table[f'{scenario["vlan"]}:{scenario["source"]}'] = scenario["ingress"]
        if scenario["check_learning"]:
            actual = table[f'{scenario["vlan"]}:{scenario["source"]}']
        else:
            eligible = sorted(int(p) for p, vlan in scenario["ports"].items()
                              if vlan == scenario["vlan"] and int(p) != scenario["ingress"]
                              and int(p) in scenario["forwarding"])
            dst = None if scenario["broadcast"] else table.get(f'{scenario["vlan"]}:{scenario["dst"]}')
            actual = eligible if dst is None else ([dst] if dst in eligible else [])
        assert actual == scenario["expected"], (actual, scenario)
        numbers = [int(s) for s in re.findall(r"\d+", answer)]
        assert numbers == ([actual] if isinstance(actual, int) else actual), (answer, actual)
    elif kind == "rate":
        assert scenario["mbps"] / 8 == scenario["expected_MBps"]
        assert float(answer.removesuffix("MB/s。")) == scenario["expected_MBps"]
    elif kind == "padding":
        assert max(0, scenario["minimum"] - scenario["payload"]) == scenario["expected_padding"]
        assert int(answer.removesuffix("バイト。")) == scenario["expected_padding"]
    elif kind == "frame":
        assert sum(scenario[k] for k in ["payload", "header", "fcs"]) == scenario["expected_frame"]
        assert int(answer.removesuffix("バイト。").replace(",", "")) == scenario["expected_frame"]
    elif kind == "mac_bit":
        assert int(bool(int(scenario["octet"], 16) & scenario["mask"])) == scenario["expected_bit"]
        assert answer == ("グループ宛て。" if scenario["mask"] == 1 else "ローカル管理。")
    elif kind == "ttl":
        assert scenario["last_received"] + scenario["ttl"] == scenario["expected_expiry"]
        assert int(answer.removesuffix("秒時点。")) == scenario["expected_expiry"]
    elif kind == "budget":
        total = scenario["reserved_per_device"] * scenario["devices"]
        assert total == scenario["expected_total"]
        assert (total <= scenario["budget"]) == scenario["expected_fits"]
        assert answer == ("満たす。" if scenario["expected_fits"] else "満たさない。")
    elif kind == "capacity":
        assert scenario["budget"] // scenario["reserved_per_device"] == scenario["expected_count"]
        assert int(answer.removesuffix("台。")) == scenario["expected_count"]
    else:
        raise ValueError(kind)


def validate_sources(facts, cards, sources, evidence, policy):
    fact_map = {f["id"]: f for f in facts}
    assert len(fact_map) == len(facts)
    assert len({c["id"] for c in cards}) == len(cards)
    assert len({c["question"] for c in cards}) == len(cards), "exact duplicate questions"
    assert len({f["section"] for f in facts}) == 14
    assert {s["id"] for s in policy["sections"]} == {f["section"] for f in facts}
    ev = {e["id"]: e for e in evidence}
    for f in facts:
        assert f["statement"] and f["source_ids"] and f["conditions"] and f["priority_reason"]
        assert all(s in sources for s in f["source_ids"])
        assert f["card_ids"] == [c["id"] for c in cards if f["id"] in c["knowledge_ids"]]
        assert f["card_ids"], f"uncovered knowledge: {f['id']}"
        for e in f["exam_evidence"]:
            assert e["unit_id"] in ev and ev[e["unit_id"]]["valid"]
            assert e["relation"] in ["直接", "適用", "前提", "関連"] and e["note"]
        assert f["priority"].startswith("A") == any(e["relation"] in ["直接", "適用"] for e in f["exam_evidence"])
    for c in cards:
        assert c["question"].strip() and c["answer"].strip() and c["required"] and c["explanation"]
        assert all(k in fact_map for k in c["knowledge_ids"])
        assert not any(w in c["question"] for w in ["前問", "前の問題", "上記と同じ条件", "前述の構成"])
        if c["scenario"]:
            oracle(c["scenario"], c["answer"])
    for s in policy["sections"]:
        assert s["covered_knowledge"] == sum(f["section"] == s["id"] for f in facts)
    old = read_legacy()
    assert set(old) == {q for f in facts for q in f["legacy_ids"]}
    return fact_map


def read_legacy():
    return {c["id"]: c for c in json.loads((ROOT.parents[0] / "一問一答データ.json").read_text())["cards"]}


def fields_for(c, fact_map, sources, section_map):
    facts = [fact_map[k] for k in c["knowledge_ids"]]
    ids = list(dict.fromkeys(s for f in facts for s in f["source_ids"]))
    links = "<br>".join(f'<a href="{escape(sources[s]["url"], quote=True)}">{text(sources[s]["title"])}</a>' for s in ids)
    evs = []
    for f in facts:
        for e in f["exam_evidence"]:
            evs.append(text(e["unit_id"] + "（" + e["relation"] + "）：" + e["note"]))
    return [
        c["id"], text(c["question"]), text(c["answer"]), bullets(c["required"]), text(c["explanation"]),
        "、".join(text(s) for s in c["accepted"]), "、".join(c["knowledge_ids"]),
        text(section_map[facts[0]["section"]]["title"]), text(c["kind"]), text(facts[0]["priority"]),
        links, "<br>".join(dict.fromkeys(evs)), "<br>".join(dict.fromkeys(text(f["conditions"]) for f in facts)),
    ]


def write_csv(path, header, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)


def build_reports(facts, cards, sources, policy):
    fact_map = {f["id"]: f for f in facts}
    write_csv(DIST / "知識一覧とカード対応.csv",
              ["知識ID", "節", "覚える内容", "前提・条件", "優先度", "優先度の理由", "カードID", "旧版の問題番号", "参考URL", "過去問との接点（代表例）"],
              [[f["id"], f["section"], f["statement"], f["conditions"], f["priority"], f["priority_reason"],
                " / ".join(f["card_ids"]), " / ".join(f["legacy_ids"]), " / ".join(sources[s]["url"] for s in f["source_ids"]),
                " / ".join(e["unit_id"] + "（" + e["relation"] + "）" + e["note"] for e in f["exam_evidence"])] for f in facts])
    write_csv(DIST / "改訂版_全カード.csv",
              ["カードID", "知識ID", "節", "形式", "問題", "短い解答", "必須要素", "補足", "許容表現", "優先度"],
              [[c["id"], " / ".join(c["knowledge_ids"]), fact_map[c["knowledge_ids"][0]]["section"], c["kind"], c["question"],
                c["answer"], " / ".join(c["required"]), c["explanation"], " / ".join(c["accepted"]), fact_map[c["knowledge_ids"][0]]["priority"]] for c in cards])
    write_csv(DIST / "旧75問との対応.csv", ["旧問題番号", "旧問題", "改訂版の知識ID", "改訂版のカードID"],
              [[qid, old["question"], " / ".join(f["id"] for f in facts if qid in f["legacy_ids"]),
                " / ".join(c["id"] for c in cards if any(qid in fact_map[k]["legacy_ids"] for k in c["knowledge_ids"]))]
               for qid, old in read_legacy().items()])
    parts = ['<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">',
             '<title>第3章 改訂版の知識一覧と作問記録</title>',
             '<style>body{font-family:system-ui,sans-serif;line-height:1.8;color:#243247;max-width:1050px;margin:32px auto;padding:0 18px}h1{font-size:27px}h2{margin-top:45px;border-bottom:2px solid #d9e3ee}h3{font-size:18px}a{color:#0369a1}article{border:1px solid #d9e3ee;border-radius:8px;padding:15px;margin:14px 0}details{margin:12px 0}summary{cursor:pointer}small,.meta{color:#52657d;font-size:13px}.answer{color:#075985;font-weight:700}.card{border-left:3px solid #c8d9e8;padding-left:15px;margin:25px 0}code{font-family:monospace}li{margin:4px 0}@media print{details{display:block}article{break-inside:avoid}}</style>',
             '<h1>第3章 Ethernet LAN — 改訂版の知識一覧と作問記録</h1>',
             f'<p>採用した知識 <b>{len(facts)}項目</b> ／ カード <b>{len(cards)}枚</b> ／ 元サイトの14項目。基本カードと条件付きカードを掲載します。カード内容には解答が含まれます。</p>',
             '<p>' + text(policy["coverage_statement"]) + '</p>',
             '<p>優先度Aは過去問との接点を確認できた代表例、Bは基礎、Cは参照知識です。頻度や配点による順位ではありません。</p>',
             '<p>学習時は短い解答を思い出し、必須要素で自己判定します。補足の文章を丸ごと再現する必要はありません。</p>',
             '<nav>' + ' / '.join(f'<a href="#section-{s["id"]}">{s["id"]} {text(s["title"])}</a>' for s in policy["sections"]) + '</nav>',
             '<details><summary>作成方針・確認範囲</summary>' + bullets(policy["method"]) + '<p>' + text(policy["evidence_scope"]) + '</p>' + bullets(policy["review_limits"]) + '</details>',
             '<details><summary>出典の記述から条件を補った箇所</summary>' + bullets(policy["source_corrections"]) + '</details>']
    for section in policy["sections"]:
        parts.append(f'<h2 id="section-{section["id"]}">{section["id"]} {text(section["title"])}</h2>')
        parts.append('<details><summary>今回はカード化しない内容・その範囲</summary>' + bullets(section["deliberately_not_carded"]) + '</details>')
        for f in facts:
            if f["section"] != section["id"]:
                continue
            parts.append(f'<article id="{f["id"]}"><div class="meta">{f["id"]} ／ {f["priority"]} ／ 旧版：{text("、".join(f["legacy_ids"]) or "追加")}</div><h3>{text(f["statement"])}</h3>')
            parts.append('<p class="meta">前提：' + text(f["conditions"]) + '<br>優先度の根拠：' + text(f["priority_reason"]) + '</p>')
            for c in cards:
                if f["id"] not in c["knowledge_ids"]:
                    continue
                parts.append(f'<div class="card" id="{c["id"]}"><small>{c["id"]} ／ {text(c["kind"])}</small><p>{text(c["question"])}</p><p class="answer">答：{text(c["answer"])}</p><small>正解に必要な要素</small>{bullets(c["required"])}<p>補足：{text(c["explanation"])}</p></div>')
            parts.append('<p class="meta">参考：' + ' / '.join(f'<a href="{escape(sources[s]["url"], quote=True)}">{text(sources[s]["title"])}</a>' for s in f["source_ids"]) + '</p>')
            if f["exam_evidence"]:
                parts.append('<details><summary>過去問との接点（代表例）</summary>' + bullets(e["unit_id"] + "（" + e["relation"] + "）：" + e["note"] for e in f["exam_evidence"]) + '</details>')
            parts.append('</article>')
    parts.append('</html>')
    (DIST / "知識一覧と作問記録.html").write_text("\n".join(parts), encoding="utf-8")


def verify_package(path, notes_expected, count):
    with zipfile.ZipFile(path) as archive, tempfile.TemporaryDirectory() as tmp:
        assert archive.testzip() is None
        assert json.loads(archive.read("media")) == {}
        dbpath = Path(tmp) / "collection.anki2"
        dbpath.write_bytes(archive.read("collection.anki2"))
        with sqlite3.connect(dbpath) as db:
            assert db.execute("PRAGMA integrity_check").fetchone()[0] == "ok"
            notes = db.execute("SELECT id, guid, mid, flds, tags FROM notes").fetchall()
            cards = db.execute("SELECT nid, did, ord, type, queue, reps FROM cards").fetchall()
            assert len(notes) == len(cards) == count
            assert Counter(c[0] for c in cards) == Counter({n[0]: 1 for n in notes})
            for _, guid, mid, fields, tags in notes:
                values = fields.split("\x1f")
                expected = notes_expected[values[0]]
                assert guid == expected.guid and mid == MODEL_ID and values == expected.fields
                assert set(tags.split()) == set(expected.tags)
            assert all((did, ordinal, kind, queue, reps) == (DECK_ID, 0, 0, 0, 0) for _, did, ordinal, kind, queue, reps in cards)
            assert db.execute("SELECT count(*) FROM revlog").fetchone()[0] == 0
            stored = json.loads(db.execute("SELECT models FROM col").fetchone()[0])[str(MODEL_ID)]
            assert len(stored["tmpls"]) == 1 and stored["tmpls"][0]["qfmt"] == FRONT
            assert [f["name"] for f in stored["flds"]] == FIELDS
    assert all("{{" + field + "}}" not in FRONT for field in FIELDS if field not in ["ID", "問題"])


def main():
    facts, cards = read("knowledge.json"), read("cards.json")
    sources, evidence, policy = read("sources.json"), read("exam_evidence.json"), read("review_policy.json")
    fact_map = validate_sources(facts, cards, sources, evidence, policy)
    section_map = {s["id"]: s for s in policy["sections"]}
    ordered = sorted(cards, key=lambda c: (fact_map[c["knowledge_ids"][0]]["section"], c["knowledge_ids"][0], c["id"].endswith("-B") is False, c["id"]))
    model = genanki.Model(MODEL_ID, MODEL_NAME, fields=[{"name": n} for n in FIELDS],
                         templates=[{"name": "問題→解答と必須要素", "qfmt": FRONT, "afmt": BACK}], css=CSS, sort_field_index=0)
    deck = genanki.Deck(DECK_ID, DECK_NAME, description=(
        f'第3章の知識{len(facts)}項目に対応する{len(cards)}問。短い解答・必須要素・補足・出典を分けています。'
        '<br>元の75問版とは別のデッキです。旧版の学習履歴の移行は行いません。'
        '<br>優先度Aは確認した代表過去問との接点、Bは基礎、Cは参照知識。出題頻度・配点の評価ではありません。'))
    expected = {}
    for i, card in enumerate(ordered, 1):
        f = fact_map[card["knowledge_ids"][0]]
        note = genanki.Note(model=model, fields=fields_for(card, fact_map, sources, section_map),
                            guid=genanki.guid_for("netspecial1-chapter03-revision-v2", card["id"]), due=i,
                            tags=["ネスペイージス::第3章::改訂版", "節::" + f["section"],
                                  "形式::" + card["kind"], "優先度::" + f["priority"].split("_")[0],
                                  "役割::" + ("基本カード" if card["id"].endswith("-B") else "条件付きカード")])
        deck.add_note(note)
        expected[card["id"]] = note
    DIST.mkdir(parents=True, exist_ok=True)
    package = DIST / f"ネスペイージス_第3章_改訂版_{len(cards)}問.apkg"
    # Fixed release timestamp: repeated builds of unchanged sources keep note revisions stable.
    timestamp = datetime.fromisoformat(policy["reviewed_on"]).replace(tzinfo=timezone.utc).timestamp()
    genanki.Package(deck).write_to_file(str(package), timestamp=timestamp)
    verify_package(package, expected, len(cards))
    build_reports(facts, ordered, sources, policy)
    result = {
        "version": policy["version"], "knowledge_items": len(facts), "cards": len(cards), "sections": len(section_map),
        "covered_knowledge_items": sum(bool(f["card_ids"]) for f in facts),
        "all_legacy_75_questions_mapped": True,
        "basic_cards": sum(c["id"].endswith("-B") for c in cards),
        "scenario_cards": sum(not c["id"].endswith("-B") for c in cards),
        "independently_calculated_scenarios": sum(bool(c["scenario"]) for c in cards),
        "kinds": dict(Counter(c["kind"] for c in cards)), "priorities": dict(Counter(f["priority"] for f in facts)),
        "representative_exam_units": len(evidence), "exhaustive_exam_frequency_count": False,
        "apkg_database_integrity": "ok", "all_notes_and_fields_match_sources": True, "review_history": "empty",
        "front_answer_leak": False, "package": package.name,
    }
    (DIST / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
