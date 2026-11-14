# 作問と公開

作問データは `revision/data/`、公開用の変換は `revision/tools/export_site.py` です。

問題を追加・修正したら、通常のcommitと `git push` で公開します。`.github/workflows/publish-cards.yml` がJSONを生成し、`published` ブランチに配信します。Anki/APKGの再生成やSitesの再デプロイは、問題データだけの更新には不要です。

既存カードの修正ではIDを維持します。新規カードには新しいIDを付けます。作問方針や編集項目は `revision/README.txt` を参照してください。

学習サイト: https://hitotsuzutsu-nw-study.amiablesheep8.chatgpt.site
作問リポジトリ: https://github.com/ken1999udon/hitotsuzutsu-cards
