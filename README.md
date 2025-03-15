# MIS_MCU_default
## 概要
本リポジトリは、GARDENsのMIS MCUに実装するソースコードの根幹となる部分を実装したものである。
これを以下に従って各ミッションに派生させることで、容易なMIS MCUの実装と搭載されるMCUの挙動の統一による試験、運用におけるMIS MCU内のシステムの共通認識目的を円滑にすることを目的とする。

## 実装方法
- main.py
  - 22行目`SELF_DEVICE_ID`の変数を自身のMIS MCUのDevice IDに変更する。
- DataCopy.py
  - `DataType`クラスのクラス変数に、保存するデータの種類とアドレスを列挙する。データの種類、アドレスはIICDのメモリマップに準拠すること
- Mission.py
  - `ExecuteMission`クラスの変数`_mission`にコマンドIDとそれに対応する関数を列挙する
  - `ExecuteMission`クラス内に、先ほど書いた関数名の動作を実装する。

## 制約、その他
- `main.py`の処理は変更しないこと
- `Mission.py`内、`ExecueteMission`クラスの`execute_mission`メソッドの処理は変更しないこと
- SMFに保存したいデータは、`ExecuteMisson`クラスのインスタンス変数である`smf_data`に以下に準拠する辞書型を`append()`すること
  - Keyは`DataType`のクラス変数であること
  - Valueは保存するデータが格納されるパスをstr型で示したリスト型であること
- SMFに保存したい、同じ種類のデータは一度に`append()`すること
- 新規のクラス作成、ファイル作成は制限しない
