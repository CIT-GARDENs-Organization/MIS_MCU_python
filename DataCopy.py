# -*- coding: utf-8 -*-

from SmfQueue import SmfQueue
from MT25QL01GBBB_20231023 import flash
from syslog import syslog
import math
from re import search


class DataCopy:
    def __init__(self):
        self._smf_data: SmfQueue = SmfQueue()
        self.flash = flash()
    
    def copy_data(self) -> None:
        syslog("Start copy to SMF")
        print("Start copy to SMF")
        data_type = None
        path_list = None
        size_erea_address = None
        body_erea_address = None
        photo_index = 0
        path = ""
        file_size = 0 
        img_data_all = 0
        img_sizeof_thisloop = 0
        PACKET_HEADER_SIZE = 3
        PACKET_IMGDATA_SIZE = 64 - PACKET_HEADER_SIZE
        wrote_size_erea_address = 0
        img_header = 0
        pckt_headernum = 0
        total_size = 0
        erase_subsector_size = 0
        adrs2writedata = 0
        next_image_address = 0
        i = 0
        erase_address = 0
        pckt_num = 0
        total_pckt_num = 0
        image_size = 0
        img_write_size = 0
        total_sector_num = 0
        start_idx = 0
        imgdata_bytes = b''
        match = None
        parts = []
        img_pckt_header = []
        header_start = 0
        data_start = 0
        byte_val = 0
        filename = ""

        while not self._smf_data.is_empty():
            data_type, path_list = self._smf_data.pop()
            print(f"Data type: {data_type.name}")
            syslog(f"Data type: {data_type.name}")
            size_erea_address, body_erea_address, _ = data_type.value

            self.flash.SUBSECTOR_4KB_ERASE_OF(size_erea_address)
            
            for photo_index, path in enumerate(path_list):
                try:
                    import os
                    file_size = os.path.getsize(path)
                    img_data_all = math.ceil(file_size / 64) * 3 
                    img_sizeof_thisloop = file_size + img_data_all
                except (FileNotFoundError, OSError) as e:
                    print(f"File not found or access error: {path}")
                    print("skip this loop")
                    syslog(f"File not found or access error: {path}")
                    syslog("skip this loop")
                    continue



                print(f"Start {path} file handle({img_sizeof_thisloop}[bytes])")
                syslog(f"Start {path} file handle({img_sizeof_thisloop}[bytes])")

                #SMF画像ヘッダエリアにphoto_index枚目の画像ヘッダを書き込む     
                PACKET_HEADER_SIZE = 3
                PACKET_IMGDATA_SIZE = 64 - PACKET_HEADER_SIZE
                wrote_size_erea_address = 4 * photo_index
                print(f"Write data size area")
                print(f"\t-> address: {size_erea_address + wrote_size_erea_address:#08x}")
                syslog(f"Write data size area")
                print(f"\t-> address: {size_erea_address + wrote_size_erea_address:#08X}")
                #ここでは、写真のデータ量を書き込んでいく。
                #つまりデータ量の10進数を16進数に直してそれを1バイトづつ切り分けてそれをビッグエンディアンの順番で書き込んでいく
                print(f"\t-> data:", end='')
                syslog(f"\t-> data:", end='')
                img_header = (img_sizeof_thisloop  >> 24 ) & 0xff
                self.flash.WRITE_DATA_BYTE_SMF(size_erea_address + 0 + wrote_size_erea_address, img_header)   #画像サイズの上32~24bitをFlashに書き込み
                print(" {:#X}".format(img_header), end='')
                syslog(" {:#X}".format(img_header), end='')

                img_header = (img_sizeof_thisloop  >> 16 ) & 0xff
                self.flash.WRITE_DATA_BYTE_SMF(size_erea_address + 1 + wrote_size_erea_address, img_header)   #画像サイズの上24~16bitをFlashに書き込み
                print(" {:#X}".format(img_header),end='')
                syslog(" {:#X}".format(img_header),end='')

                img_header = (img_sizeof_thisloop  >> 8 )  & 0xff
                self.flash.WRITE_DATA_BYTE_SMF(size_erea_address + 2 + wrote_size_erea_address, img_header)   #画像サイズの上16~8bitをFlashに書き込み
                print(" {:#X}".format(img_header),end='')
                syslog(" {:#X}".format(img_header),end='')

                img_header = img_sizeof_thisloop & 0xff
                self.flash.WRITE_DATA_BYTE_SMF(size_erea_address + 3 + wrote_size_erea_address, img_header)   #画像サイズの上8bitをFlashに書き込み
                print(" {:#X}".format(img_header))



                print(f"Write data body area")
                syslog(f"Write data body area")
                pckt_headernum = -(- img_sizeof_thisloop // PACKET_IMGDATA_SIZE )   #読み出した画像がいくつのpcktに分割できるか計算(切上げ)
                #消去するFlashのセクタ数を切上げ計算。
                #消去セクタ数合計値 += {(画像本体) + (各画像パケットヘッダの合計)} // 4KBサブセクタのサイズ(4096byte)
                # 画像サイズ + 全パケットヘッダのサイズを計算
                total_size = img_sizeof_thisloop + (PACKET_HEADER_SIZE * pckt_headernum)
                # 消去範囲を多めに確保（例: 1セクタ追加）
                erase_subsector_size = math.ceil(total_size / self.flash.SUBSECTOR_SIZE_OF_4KB) 

                if photo_index == 0:
                    adrs2writedata = body_erea_address
                else:
                    adrs2writedata = next_image_address  # 前回の終了アドレスを継承 # 画像ごとに連続したアドレスを使用（前画像の終了アドレスから開始）

                for i in range(erase_subsector_size):
                    #対象のサブセクタを消去(写真のデータが入るところを事前にけしている)
                    erase_address = adrs2writedata + i * self.flash.SUBSECTOR_SIZE_OF_4KB
                    self.flash.SUBSECTOR_4KB_ERASE_OF(erase_address)   
                    #デバック用（書き込みに必要なデータ量分のセクタを消せているのか確認できる）
                    #print("erased 4KB subsector address:{}".format(i))
                    #syslog("erase 4KB subsector address:" + str(i))

                # 各画像の書き込み前にアドレスを初期化（画像ごとに独立して書き込む）
                # 画像ごとに連続したアドレスを使用（例: 前の画像の終了アドレスから開始）

                # print(f"画像{photo_index}の書き込み開始アドレス: 0x{adrs2writedata:08X}")  # デバッグ用

                #SMFに書き込む画像をオープンし画像サイズを計算、list化する
                # メモリ効率改善：ファイルサイズは既に取得済み、不要なリスト変換を削除
                img_sizeof_thisloop = file_size  # 実際のファイルサイズを使用

                #画像パケットヘッダ初期値の設定
                pckt_num   = 0                                                                      #何番目の画像パケットなのか識別
                total_pckt_num = -(- img_sizeof_thisloop // PACKET_IMGDATA_SIZE)                    #読み出した画像がいくつのpcktに分割できるか計算(切上げ)


                #read_img_cntr番目の画像データをパケット化し、画像ヘッダと共に次々にSMFへ書き込んでいく
                print(f"\t-> address: {adrs2writedata:#08X}")
                syslog(f"address: {adrs2writedata:#08X}")

                # この画像のサイズや必要パケット数から次のアドレスを計算する準備
                image_size = img_sizeof_thisloop
                total_pckt_num = (image_size // PACKET_IMGDATA_SIZE)

                # この画像の分で書き込まれるバイト数
                total_pckt_num = math.ceil(image_size / PACKET_IMGDATA_SIZE)
                img_write_size = (PACKET_HEADER_SIZE + PACKET_IMGDATA_SIZE) * total_pckt_num

                #必要な4kbyteセクター数
                total_sector_num = -( - img_write_size //4096) 
                #次の画像は次のセクター先頭から書く仕様
                # セクターの末尾のアドレス
                
                # 次の画像の書き込み先に進めておく
                #adrs2writedata += img_write_size
                # 次の画像は4KB境界でアライメントされたアドレスから開始
                # 計算式: (必要なセクタ数 * 4096) + 現在のアドレス
                next_image_address =  total_sector_num * 4096 + adrs2writedata 

                total_pckt_num = int(math.ceil(image_size / PACKET_IMGDATA_SIZE))
                
                # ファイルを開いてストリーミング処理（メモリ効率改善）
                try:
                    with open(path, 'rb') as image_file:
                        for pckt_num in range(total_pckt_num):
                            # パス名から正規表現でヘッダ情報を抽出
                            import os
                            filename = os.path.splitext(os.path.basename(path))[0]
                            match = search(r'_([0-9A-Fa-f]{2}_[0-9A-Fa-f]{2}_[0-9A-Fa-f]{2})$', filename)
                            if match:
                                parts = match.group(1).split('_')
                            else:
                                parts = []

                            # make 3-byte header
                            if len(parts) == 3 and all(len(p) == 2 for p in parts):
                                try:
                                    img_pckt_header = [
                                        int(parts[0], 16),
                                        int(parts[1], 16),
                                        int(parts[2], 16)
                                    ]
                                except ValueError:
                                    print("[WARN] Invalid hex value in header parts")
                                    print("       Using default header: `FF FF FF`")
                                    syslog("[WARN] Invalid hex value in header parts")
                                    syslog("       Using default header: `FF FF FF`")
                                    img_pckt_header = [0xFF, 0xFF, 0xFF]
                            else:
                                print("[WARN] Invalid header format")
                                print("       Using default header: `FF FF FF`")
                                syslog("[WARN] Invalid header format")
                                syslog("       Using default header: `FF FF FF`")
                                img_pckt_header = [0xFF, 0xFF, 0xFF]

                            # ストリーミング読み込み：必要な分だけ読み込む
                            start_idx = pckt_num * PACKET_IMGDATA_SIZE
                            image_file.seek(start_idx)  # ファイルポジションを移動
                            imgdata_bytes = image_file.read(PACKET_IMGDATA_SIZE)  # 必要な分だけ読み込み
                            
                            # サイズエリア書き込み（3バイト）
                            header_start = adrs2writedata
                            for i in range(PACKET_HEADER_SIZE):
                                self.flash.WRITE_DATA_BYTE_SMF(header_start + i, img_pckt_header[i])
                        
                            # データ書き込み（最大61バイト）
                            data_start = header_start + PACKET_HEADER_SIZE
                            for i, byte_val in enumerate(imgdata_bytes):
                                self.flash.WRITE_DATA_BYTE_SMF(data_start + i, byte_val)
                        
                            # 次のパケットのアドレスを更新
                            adrs2writedata = data_start + len(imgdata_bytes)
                            #デバック用（64バイトずつ書き込まれているか確認できる）
                            #print(f"パケット{pckt_num}: ヘッダ=0x{header_start:08X}, データ=0x{data_start:08X}, サイズ={len(imgdata_bytes)}バイト")  # デバッグ用

                except (IOError, OSError) as e:
                    print(f"File read error: {path} - {e}")
                    syslog(f"File read error: {path} - {e}")
                    continue

                print() # end for each path loop


        print(f"End copy to SMF")