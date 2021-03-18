# NukoPunch
Nekoniumのフルチェーンから、署名付き残高スナップショットを作るためのツールセットです。
Pythonスクリプトで実装してあります。

残高スナップショットは、任意のブロック高に存在する全てのアカウントの、そのブロック高におけるNUKO残高のリストです。
アカウントそれぞれの残高に複数の署名アカウントで署名し、改竄不能な残高リストを生成します。

## セットアップ

ツールの使用するライブラリをセットアップして下さい。
```
pip install tqdm web3
```

nekoniumのフルノードが必要なので同期してください。
```
$ gnekonium --rpc --rpcaddr "localhost" --syncmode full console
```

lightモードで同期した場合は、最近のブロックにある残高スナップショットしか作ることができません。


## 残高リストを作る

残高リストの生成手順は4ステップです。

1. Nekoniumチェーンのブロックスキャン
2. 残高スナップショットの取得
3. 残高リストの生成と署名
4. トランザクションデータの生成

## Nekoniumチェーンのブロックスキャン
`blockScan.py`を使います。
Nekoniumチェーンからブロック、トランザクションを読みだして、チェーン内に存在する全てのアカウント情報を読みだします。
読みだした情報はsqlite形式のデータベースへ保存します。

最新のブロックまでスキャンするには、次のコマンドを実行します。
```
$python3 blockScan.py 0 --format sqlite --out ./nekonium_accounts.sqlite3
```

このコマンドはとても長い時間がかかります。ipcインタフェイスを使うと少しだけ時間を短縮できます。
`ipc-path`はgnekoniumの起動ログの中に記載されています。
```
$python3 blockScan.py 0 --format sqlite --out ./nekonium_accounts.sqlite3 --rpc ipc:[ipc-path]
```

全てのブロックをスキャンする必要がなければ、`--close`で終端ブロックを設定できます。

## 残高スナップショットの取得
`balanceSnapshot.py`を使います。
このスクリプトは、残高スナップショットを取得して、結果をデータベースへ保存します。
blockScan.pyで生成したデータベースと、Nekoniumチェーンを使います。

ブロック100000の残高スナップショットは次のコマンドで取得できます。
```
$python3 balanceSnapshot.py ./nekonium_accounts.sqlite3 100000 --format sqlite
```
結果は元のデータベースへ追記します。


## 残高リストの生成と署名
`genSignedBalanceList.py`を使います。
このスクリプトは、データベースの残高スナップショットから残高リストのJsonを生成し、それを編集することができます。

ブロック100000の残高リストは次のコマンドで生成できます。
予め`balanceSnapshot.py`でデータベースにブロック100000の残高スナップショットを生成しておいてください。
```
$python3 genSignedBalanceList.py init nekonium_accounts.sqlite3-2 10000 --message TEST --out ./signed.json
```
`--message`は署名データに埋め込む任意文字列です。16文字まで指定できます。


生成された`./signed.json`の中身です。まだ誰も署名していないので、`proofAccounts`が空になっています。
```
{
  "version": "BalanceCertification/0.1",
  "created_date": "2020-12-24 21:24:15.853105",
  "params": {
    "proofAccounts": [
  	],
    "height": 10000,
    "message": "TEST"
  },
  "balances": [
	:
    [
      "0x235D224264D23a9B15385eBBFD665f49D5519Aec",
      3518437500000000000000,
      "0x235d224264d23a9b15385ebbfd665f49d5519aec00002710000000bebc2108c4e973c00054455354000000000000000000000000",
      [
      ]
    ],
    :
  ]
}
```

次に、アカウント`0x4b647402e73185ae03b5591b43f5236eccfcff23`で署名します。
署名するアカウントは、接続先のgnekoniumのアカウントに登録されていなければなりません。

```
$python3 genSignedBalanceList.py sign ./signed.json 0x4b647402e73185ae03b5591b43f5236eccfcff23 --password "PASSWORD"
```


署名に成功すると、proofAccountsとbalancesのそれぞれの要素に署名アカウントと署名ハッシュが追記されます。

```
{
  "version": "BalanceCertification/0.1",
  "created_date": "2020-12-24 21:24:15.853105",
  "params": {
    "proofAccounts": [
      "0x4B647402e73185AE03b5591B43F5236eCcfcff23"
    ],
    "height": 10000,
    "message": "TEST"
  },
  "balances": [
	:
    [
      "0x235D224264D23a9B15385eBBFD665f49D5519Aec",
      3518437500000000000000,
      "0x235d224264d23a9b15385ebbfd665f49d5519aec00002710000000bebc2108c4e973c00054455354000000000000000000000000",
      [
        "0x415f0c29702649a76c10f1daaa9008a5f78820e92d99e99d02e62d0881a1449345a467ffc1e2d9482e53cf7378fa824ce274222ea13b990ed18f053f154d77481b"
      ]
    ],
    :
  ]
}
```

### データ構造

- `params`
	- `proofAccounts` 署名したアカウントのHEX値の配列です。署名した順に追記します。
	- `height` このリストの残高を取得したブロック高です。
	- `message` 署名に用いるメッセージの値です。

- `balances`
	- `[0]` 残高の所有アカウントです。
	- `[1]` wie単位の残高です。
	- `[2]` アカウント`[0]`(20byte)、ブロック高`height`(4byte)、残高`[1]`(12byte)、メッセージ`message`(16byte)を連結した52byteのhex値
	- `[3]` hex値にproofAccountsのそれぞれのアカウントで署名したハッシュ値(64byte)


proofAccounts[p]の署名ハッシュは、balances[n][3][p]です。
次のコードでbalances[n][2]のhexが改ざんされていないか確認することができます。
```
message = encode_defunct(hexstr=Web3.toHex(balances[n][2]))
ac=web3.eth.account.recover_message(message, signature=Web3.toHex(balances[n][3][p]))
print(ac!=proofAccounts[p])
```




## トランザクションデータの生成
`signed.json`からアカウントごとのトランザクションリストを生成します。
トランザクションデータは、残高、ブロック高、メッセージをバイナリ化したHEX値の後ろに、全ての署名ハッシュ値を連結した値です。
CSV,またはJSONで出力できます。

以下のコマンドはCSVで出力します。
```
$python3 genSignedBalanceList.py export --format csv ./sbl.json
```

生成されるCSVファイルの内容です。
```
version	created_date
SignedBalanceList/0.1;BalanceCertification/0.1	2020-12-24 21:24:15.853105
params
snapshotHeight	10000
proofAccounts	0x4B647402e73185AE03b5591B43F5236eCcfcff23
lowerLimit	0
accounts
total	active	drop
26	26	0
transactions
account	balance(NUKO)	balance(wie)	transaction
:
0x0000000000000000000000000000000000000000	0.0	0	0x000000000000000000000000000000000000000000002710000000000000000000000000544553540000000000000000000000002076a645a9703d01a9d01beae5a0f7940db453653d313945fe4944704b6c9b334db3206213b9e9f66133309b824885e84485084732bae2b826c34b50f97b2c761c
0xdcEa28Ea2Cb699bF020a6D4738EB3A94D9FAEBb7	26088.920726	26088920726000000000000	0xdcea28ea2cb699bf020a6d4738eb3a94d9faebb70000271000000586488187455c176000544553540000000000000000000000004884f34ceb81d7ff230e91ff7c3bbf9934932a71a1122de48339ed97b333343d3740ecb17b7e23779b3ab3afed5ba59702d3495513e78cd11942dfb919d4b02e1c
:
```
`--lowerLimit`オプションを指定すると、指定数未満の残高のアカウントを無視して出力します。
残高0を除外するには、`--lowerLimit 1`を指定します。
accountsの下の行は、元データのアカウントの数、出力対象の数、除外された数です。

# Web API

sqlite3形式で生成したトランザクションデータのRESTful-APIを提供するPHPスクリプトです。

データベースは以下のように生成します。
```
$python3 genSignedBalanceList.py export --format sqlite3 ./db.sqlite3
```
## 設置

web.api以下とデータベースファイルをコピーして、_libs.phpの中のDBPATHにデータベースのパスを設定します。

## API

データベースに格納されているアカウントのレコード一覧を得る。

/accountlist.php?limit=[int]&page=[int]&order=[account|id|acmount|amount_nuko]&notx&i

limit 1ページ当たりの項目数
page ページ番号
order 並べ替えキー
notx キーがある場合、txフィールドを省略する。
i キーがある場合インデントで整形する。

全てのパラメータは省略できます。

```
{
    "version": "NukoPunchREST/0.1.0;AccountListApi/1.0.0;PHP",
    "success": true,
    "timestamp": 1616074839000,
    "result": {
        "pages": {
            "total": 1907,
            "page": 0
        },
        "total": "19066",
        "list": [
            [
                6,
                "0x0000000000000000000000000000000000000000",
                "18000000000000000000",
                18,
                "0x000000000000000000000000000000000000000000559a1000000000f9ccd8a1c50800004b6f6e756b6f546f6b656e2f303030312db39e2f85f68a7e3306041d3f412897cd780a5a937ccc5b9246de31bba440d679a315b37bdc8ea95bbbf3d50599182c24cf556c161cd003b44fe6dabee60c1c1b"
            ],
            [
                1660,
                "0x0000578BD7ABc6aa99C15AA0FAB3921929f92cFa",
                "276000000000000",
                0.000276,
                "0x0000578bd7abc6aa99c15aa0fab3921929f92cfa00559a10000000000000fb0541f540004b6f6e756b6f546f6b656e2f30303031aa12489c626302748f3948641fa5020b895543f7013dec0cb1f5be0a290509747ca9dc781bb6100cdd66b87bf98e6d4f533a049aca54c64adb2e57958d8f3deb1c"
            ],
:
```

アカウントの残高証明レコードを得る。

/accountinfo.php?account=[イーサリウムアドレス]&notx&i


account 取得するレコードのアカウント
notx キーがある場合、txフィールドを省略する。
i キーがある場合インデントで整形する。

accountは省略できません。他のパラメータは省略できます。