<div align="center">
    <img src="https://github.com/user-attachments/assets/099b80dd-a6a5-4a14-940f-06401dadf024" width="200" alt="GARDENs logo" />
   <h1>MIS MCU source code<br>(Python)</h1>
   
[**English**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/README.md) | [日本語] 
</div>

## 概要  
本リポジトリは、GARDENsのMIS MCUに実装するPythonソースコードの基盤を提供するものである。
これを基に各ミッションへ派生させることによる以下の実現を目的とする。

- **開発効率の向上**  
- **担当領域の明確化**  
- **統一された挙動による試験・運用の円滑化**  


## ミッション実装方法  
1. `main.py` **19行目** → `SELF_DEVICE_ID` を自身のMIS MCUのDevice IDに設定
   - [**IICD メモリマップ**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/docs/memory_map.png)を参照すること
2. `main.py` **20行目** → `SERIAL_PORT` にシリアルポート名を文字列で記入  
   - `None` の場合、自動取得＆CLI選択機能が利用可能  
3. `SmfQueue.py` → `DataType` クラスのクラス変数に **保存するデータの種類、アドレス、ミッションフラグ** を列挙  
   - [**IICD メモリマップ**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/docs/memory_map.png) に準拠すること  
4. `Mission.py` → `Mission` クラスの `_mission_list` に **コマンドIDと対応関数** を記述  
5. `Mission.py` → `Mission` クラス内に **ミッションのメソッド** を実装  


## 制約 & その他  

### **変更禁止のファイル・メソッド**  
- `main.py`・`DataCopy.py` の処理（`print()` 関数は自由に配置、撤去して良い）  
- `Mission.py` の `Mission` クラスの `execute_mission()` メソッド

### **SMFデータの保存ルール** 
- 保存するファイルの名前は、任意の文字列とアンダースコア(`_`)2桁の0詰めした数字がアンダースコアで3つつながったものとする  

``` txt
save fine name example
- OK)
   - photo_00_01_00.png
   - 0D_00_00.bin
   - _00_FF_00
- NG)
   - photo_00_01.png // Missing digit
   - binary_00_0D_0.bin // Missing digit
   - data00_FF_00.bin // Missing underscore
```
-
   - 1つめの領域は、ミッションの実行回数とする。
   - 2つめの領域は、そのミッションごとに生成されたファイルの個数とする。
   - 3つめの領域は、切り取り写真における切り取り場所とする。
   - 写真でないファイルや写真以外の場合、3つめの領域は`00`で固定とする。
   - **フォーマットに従っていない場合、ヘッダーは`FF FF FF`となる。** 
   - **以上に従わなくても衛星上では問題ないが、正しいフォーマットでないと、将来的に実装するGARDENsの地上局ソフトウェアで円滑なデータ復元ができない可能性があることに留意する。**
- 保存する写真は、`MissionExecute` クラスの `smf_data` に `append()` する  
```py
- ex)
   - self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png", "./photo/thumb/1.png"])
   - self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, path_list)
```
---

## 今後の更新予定 (作業担当者: GARDENs)
1. printからsyslogへの移行
   - 現在はprintを使って動作をモニタリングしているが、衛星の試験時、運用時はリアルタイムのモニタリングが不可能であるため、過去号機ではsyslogモジュールを用いてログを外部出力していた。
   - 今回もそれを踏襲するが、具体的な出力フォーマットなどを定めていないため、決まり次第今後すべて統一された出力をするsyslogに移行する
   - 決まり次第、ルールを各々の団体へ通知する。



## 追記
1. SMFに書き込んだデータは同封したDataRead.pyで読み込むことができるので、SMFの中身を確認したい場合は使用してほしい
   - エントリポイントで指定した`DataType`で、保存されているすべての写真を読み取る。
   - 保存名は`ouput_path`で指定される
2. 動作理解を深めるため、3種のサンプルミッションと、BOSS PICのシミュレーターソフトを用意した。
ぜひ試しに動作させてから各々のミッション開発に取り掛かってほしい

[BOSS PIC simulater](https://github.com/CIT-GARDENs-Organization/BOSS_PIC_simulator)

| CMD ID     | 使用パラメーター         | 説明                                         |
|:-----------|:------------            |:------------                                |
| 00         | XX __ __ __ __ __ __ __ | X秒待機する                                 |
| 01         | _X __ __ __ __ __ __ __ | X枚のサムネ画像を保存する                   |
| 02         | XX XX __ __ __ __ __ __ | Xミリ秒待機し本画像、サムネ画像を1枚保存する  |
