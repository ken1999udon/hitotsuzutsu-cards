# カードの作成と公開

学習サイト：https://hitotsuzutsu-nw-study.amiablesheep8.chatgpt.site

各章のデータを編集し、通常どおりcommit・pushするだけで公開できます。章数の上限や、章を追加するためのサイトコード変更はありません。

## 新しい章を追加する

例えば第4章なら、この2ファイルを置きます。フォルダ名は任意です。

```text
chapters/chapter04/
  chapter.json
  data/cards.json
```

`chapter.json` は章の名前と、このリポジトリ内で重複しない識別子です。

```json
{
  "deck_id": "chapter-04",
  "title": "第4章のタイトル",
  "subtitle": "ネスペイージス 第4章"
}
```

`data/cards.json` は問題の配列です。最小構成は次の3項目です。

```json
[
  {"id": "Q01", "question": "問題文", "answer": "解答"}
]
```

カードIDは章内で重複しなければ、別の章で同じIDを使えます。`section_title`、`required`、`accepted`、`explanation`、`sources` は任意で付けられます。第3章と同様に知識一覧を使う場合は、同じdataフォルダにknowledge.json・sources.json・review_policy.jsonを置けます。

`chapter.json` を置いた章を自動検出します。空の章は公開せず、作問済みの章だけ配信します。第1章・第2章などを後から追加しても同じ手順です。

## 公開する

```sh
git add chapters
git commit -m "章・問題を追加または修正"
git push
```

GitHubのWeb編集でファイルを保存した場合も同じ処理が動きます。GitHub Actionsが `tools/export_catalog.py` を実行し、全章をまとめた `published/catalog.json` を更新します。学習サイトはそれを直接読むので、Ankiファイルの生成、サイトの再デプロイ、利用者の手動インポートは不要です。

公開結果は **Actions → Publish study cards** で確認できます。生成に失敗した場合は、それまでの公開データを引き続き配信します。追加の秘密情報の登録は不要です。

## 既存の第3章

既存データは `revision/chapter.json` と `revision/data/` に残しています。この章も特別扱いせず、同じ自動検出・生成で配信します。第3章だけを編集したときは `git add revision` でcommit・pushできます。

既存カードの修正ではカードIDを維持し、新しいカードには新しいIDを付けてください。第3章の作問方針・Anki版は [revision/README.txt](revision/README.txt) を参照してください。
