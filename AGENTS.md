# 作問と公開

すべての章に共通の公開処理です。新しい章は `chapters/chapterXX/chapter.json` と `chapters/chapterXX/data/cards.json` を作成します。章情報の必須項目は `deck_id` と `title`、カードの必須項目は `id`・`question`・`answer` です。詳細はREADME.mdを参照してください。

既存の第3章は `revision/chapter.json` と `revision/data/` にあります。移動せず、ほかの章と同じように自動検出されます。

問題を追加・修正したら、通常のcommitと `git push` で公開します。`.github/workflows/publish-cards.yml` が `tools/export_catalog.py` を実行し、全章の `catalog.json` を `published` ブランチに配信します。問題データだけの更新に、APKG再生成・Sites再デプロイ・章の登録リストの編集は不要です。

章のdeck_idはリポジトリ全体で一意にします。カードIDは章内で一意にし、既存カードの修正では維持します。章の追加にサイトコードの変更は必要ありません。空の章は公開されません。

学習サイト: https://hitotsuzutsu-nw-study.amiablesheep8.chatgpt.site
作問リポジトリ: https://github.com/ken1999udon/hitotsuzutsu-cards
