<div align="center">
    <img src="https://github.com/user-attachments/assets/099b80dd-a6a5-4a14-940f-06401dadf024" width="200" alt="GARDENs logo" />
   <h1>MIS MCU source</h1>
    
🌏
English | [**日本語**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/README.ja.md)

</div>

## 概要  
本リポジトリは、GARDENsのMIS MCUに実装するソースコードの基盤を提供するものである。
これを基に各ミッションへ派生させることによる以下の実現を目的とする。

- **開発効率の向上**  
- **担当領域の明確化**  
- **統一された挙動による試験・運用の円滑化**  

---

## 実装方法  
1. `main.py` **19行目** → `SELF_DEVICE_ID` を自身のMIS MCUのDevice IDに設定  
2. `main.py` **20行目** → `SERIAL_PORT` にシリアルポート名を文字列で記入  
   - `None` の場合、自動取得＆CLI選択機能が利用可能  
3. `DataCopy.py` → `DataType` クラスのクラス変数に **保存するデータの種類とアドレス** を列挙  
   - **IICDのメモリマップ** に準拠すること  
4. `Mission.py` → `MissionExecute` クラスの `_mission_list` に **コマンドIDと対応関数** を記述  
5. `Mission.py` → `MissionExecute` クラス内に **該当する関数の動作** を実装  

---

## 制約 & その他  

### **変更禁止のファイル・メソッド**  
- `main.py`・`DataCopy.py` の処理（`print()` 関数は自由に配置、撤去して良い）  
- `Mission.py` の `ExecuteMission` クラスの `execute_mission()` メソッド

### **SMFデータの保存ルール**  
- `MissionExecute` クラスの `smf_data` に `append()` する  
  ```python
  ex) self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png", "./photo/thumb/1.png"])
  ex) self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, path_list)

---

## 今後の更新予定 (作業担当者: GARDENs)
1. printからsyslogへの移行
   - 現在はprintを使って動作をモニタリングしているが、衛星の試験時、運用時はリアルタイムのモニタリングが不可能であるため、過去号機ではsyslogモジュールを用いてログを外部出力していた。
   - 今回もそれを踏襲するが、具体的な出力フォーマットなどを定めていないため、決まり次第今後すべて統一された出力をするsyslogに移行する
   - 決まり次第、ルールを各々の団体へ通知する。
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

## 追記
動作理解を深めるため、3種のサンプルミッションと、BOSS PICのシミュレーターソフトを用意した。
ぜひ試しに動作させてから各々のミッション開発に取り掛かってほしい

[BOSS PIC simulater](https://github.com/CIT-GARDENs-Organization/BOSS_PIC_simulator)

| CMD ID     | 使用パラメーター         | 説明                                         |
|:-----------|:------------            |:------------                                |
| 00         | XX __ __ __ __ __ __ __ | X秒待機する                                 |
| 01         | _X __ __ __ __ __ __ __ | X枚のサムネ画像を保存する                   |
| 02         | XX XX __ __ __ __ __ __ | Xミリ秒待機し本画像、サムネ画像を1枚保存する  |
