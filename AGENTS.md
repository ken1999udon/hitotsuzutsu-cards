# 作問と公開

すべての章に共通の公開処理です。新しい章は `chapters/chapterXX/chapter.json` と `chapters/chapterXX/data/cards.json` を作成します。章情報の必須項目は `deck_id` と `title`、カードの必須項目は `id`・`question`・`answer` です。詳細はREADME.mdを参照してください。

既存の第3章は `revision/chapter.json` と `revision/data/` にあります。移動せず、ほかの章と同じように自動検出されます。

問題を追加・修正したら、通常のcommitと `git push` で公開します。`.github/workflows/publish-cards.yml` が `tools/export_catalog.py` を実行し、全章の `catalog.json` を `published` ブランチに配信します。問題データだけの更新に、APKG再生成・Sites再デプロイ・章の登録リストの編集は不要です。

章のdeck_idはリポジトリ全体で一意にします。カードIDは章内で一意にし、既存カードの修正では維持します。章の追加にサイトコードの変更は必要ありません。空の章は公開されません。

学習サイト: https://hitotsuzutsu-nw-study.amiablesheep8.chatgpt.site
作問リポジトリ: https://github.com/ken1999udon/hitotsuzutsu-cards


## ユーザーの最新の作問方針

- infraexpert.comの本文を基に、重要な定義・仕組み・違い・理由・数値を自然な一問一答にする。
- 作成者がネットワーク構成や数値条件を足した独自の具体問題は作らない。
- 問題数を75問などに固定しない。各問いの意味、重複、本文の主要な内容の抜けを判断して改善する。
- 学習用の表示は問題と簡潔な解答。補足・必須要素・前提・対応する知識・管理IDを表示しない。
- 理由が解答に必要なら、その理由を解答自体に短く書く。意味の薄い文章で欄を埋めない。
- 出典とIDは管理データとして保持する。既存の問いの修正ではIDを維持する。

- Cisco独自のプロトコル・機能・製品名・設定／確認コマンドは出題しない。標準技術や一般的な仕組みは、Ciscoの実装に依存しない形で問う。
