# カードの作成と公開

学習サイト：https://hitotsuzutsu-nw-study.amiablesheep8.chatgpt.site

`revision/data/cards.json` などの作問データを編集し、通常どおりコミットしてpushするだけで公開できます。

```sh
git add revision/data
git commit -m "問題を追加・修正"
git push
```

GitHub Actionsが `revision/tools/export_site.py` を実行し、`published` ブランチの `deck.json` を更新します。学習サイトはそのJSONを直接読むため、Ankiファイルの生成、サイトの再デプロイ、利用者の手動インポートは不要です。GitHubのファイル編集画面から保存した場合も同じ処理が動きます。

公開処理の結果は、このリポジトリの **Actions → Publish study cards** で確認できます。生成に失敗した場合は、それまでの公開データを引き続き配信します。追加の秘密情報の登録は不要です。

作問途中の知識がカード化されていなくても、完成しているカードを公開できます。既存カードを修正する場合はカードIDを維持し、新しいカードには新しいIDを付けてください。問題の書き方・出典・Anki版については [revision/README.txt](revision/README.txt) を参照してください。
