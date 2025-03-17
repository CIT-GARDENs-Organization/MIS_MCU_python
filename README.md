# MIS_MCU_source
## 概要
本リポジトリは、GARDENsのMIS MCUに実装するソースコードの根幹となる部分を実装したものである。
これを以下に従って各ミッションに派生させることで、開発効率の上昇、担当領域の明確化を実現し、
また、挙動の統一による、試験・運用におけるMIS MCU内のシステムの理解を円滑にすることを目的とする。

## 実装方法
- `main.py` 19行目`SELF_DEVICE_ID`の変数を自身のMIS MCUのDevice IDに変更する。
- `main.py` 20行目`SERIAL_PORT` にシリアルポート名を文字列で記入する。(Noneの場合、自動で使用可能ポートを取得してCLIから選択できる開発用機能が使用される)
- `DataCopy.py` `DataType`クラスのクラス変数に、保存するデータの種類とアドレスを列挙する。データの種類、アドレスはIICDのメモリマップに準拠すること
- `Mission.py` `MissionExecute` クラスの変数`_mission_list`にコマンドIDとそれに対応する関数を列挙する
- `Mission.py` `MissionExecute` クラス内に、先ほど書いた関数名の動作を実装する。

## 制約、その他
- `main.py` `DataCopy.py`の処理は変更しないこと(print関数は除く)
- `Mission.py`内、`ExecueteMission`クラスの`execute_mission`メソッドの処理は変更しないこと
- SMFに保存したいデータは、`MissionExecute`クラスのインスタンス変数である`smf_data`に以下に準拠する辞書型を`append()`すること (`Mission.py`のコメントに同じ内容を記載している)
  - Keyは`DataType`のクラス変数であること
  - Valueは保存するデータが格納されるパスをstr型で示したリスト型であること
  - 同じ種類のデータは一度に`append()`すること
- 新規のファイル、クラス、関数の作成は自由である
- Raspberry PiではなくWindows環境で開発する場合、`main.py`の18行目の`USE_WINDOWS`を`True`にすること。シリアルの受信関数に用いるモジュールがLinux環境専用であるため、Windowsの場合代替した関数を用いる。

## 今後の更新予定
1. printからsyslogへの移行
   - 現在はprintを使って動作をモニタリングしているが、衛星の試験時、運用時はリアルタイムのモニタリングが不可能であるため、過去号機ではsyslogモジュールを用いてログを外部出力していた。今回もそれを踏襲するが、具体的な出力フォーマットなどを定めていないため、決まり次第今後すべて統一された出力をするsyslogに移行する
2. SMFへのコピー機能の実装
   - 現在は以下のようなprint出力でSMFへのコピーを模しているが、今後実際に機能を開発し統一されたSMFへのコピー機能を搭載する。
```
Start data copy thread
Start copy to SMF
        -> Data type: EXAMPLE_PHOTO_THUMB
                -> ./photo/thumb/0.png
                -> ./photo/thumb/1.png
                -> ./photo/thumb/2.png
                -> ./photo/thumb/3.png
End copy to SMF
```

## 実装されているサンプルミッション
ぜひ`BOSS_PIC_simulater`と一緒に使用しミッションの想定動作を確認してほしい

https://github.com/CIT-GARDENs-Organization/BOSS_PIC_simulator

| CMD ID     | 使用パラメーター         | 説明                                         |
|:-----------|:------------            |:------------                                |
| 00         | XX __ __ __ __ __ __ __ | X秒待機する                                 |
| 01         | _X __ __ __ __ __ __ __ | X枚のサムネ画像を保存する                   |
| 02         | XX XX __ __ __ __ __ __ | Xミリ秒待機し本画像、サムネ画像を1枚保存する  |
