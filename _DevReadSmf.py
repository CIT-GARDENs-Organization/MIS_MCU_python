from SmfQueue import DataType
import MT25QL01GBBB_20231023 as MT25QL01GBBB

import os


flash = MT25QL01GBBB.flash()
PACKET_SIZE = 64
HEADER_SIZE = 3
DATA_SIZE = PACKET_SIZE - HEADER_SIZE 


def read_data(data_type: DataType, output_path: str, output_file_name: str, output_extention: str):
    size_data_address, body_data_address, _ = data_type.value
    current_size_data_ptr = size_data_address
    current_body_area_ptr = body_data_address
    data_index = 0
    
    while True:
        # read data size area (4bytes)
        size_header = [flash.READ_DATA_BYTE_SMF(current_size_data_ptr + i) for i in range(4)]
        
        # detect of end
        if all(b == 0xFF for b in size_header[:3]):
            print(f"[END] Terminator found at {hex(current_size_data_ptr)}")
            break

        img_size = int.from_bytes(size_header, 'big')
        print(f"\n[data {data_index}] Header at {hex(current_size_data_ptr)}, Size: {img_size} bytes")

        
        img_data = bytearray()
        bytes_remaining = img_size
        read_ptr = current_body_area_ptr
        packet_num = 0

        while bytes_remaining > 0:
            # skip header data
            read_ptr += HEADER_SIZE

            # actual read data size
            chunk_size = min(DATA_SIZE, bytes_remaining)
            
            # read data
            for _ in range(chunk_size):
                byte = flash.READ_DATA_BYTE_SMF(read_ptr)
                img_data.append(byte)
                read_ptr += 1
                bytes_remaining -= 1

            packet_num += 1
            print(f"  Packet {packet_num}: Read {chunk_size} bytes from {hex(read_ptr - chunk_size)}")

            # パケット境界調整（64バイトアライメント）
            remaining_in_packet = PACKET_SIZE - (chunk_size + HEADER_SIZE)
            if remaining_in_packet > 0:
                read_ptr += remaining_in_packet

        # save the file
        output_name = os.path.join(output_path, output_file_name) + f"{data_index+1:03d}" + "." + output_extention
        try:
            with open(output_name, 'wb') as f:
                f.write(img_data)
            print(f"[SAVED] {output_name} ({len(img_data)} bytes)")
        except FileNotFoundError as e:
            print(f"Invalid path :{e}")
            break


        # ポインタ更新（4KB境界にアライメント）
        current_size_data_ptr += 4
        current_body_area_ptr = ((read_ptr + 4095) // 4096) * 4096
        data_index += 1



if __name__ == "__main__":
    read_data_type = DataType.EXAMPLE_EARTH_PHOTO_THUMB
    ouput_path = "/foo/bar"
    output_file_name = "data"
    output_extention = "png"


    print("\r\nThis is DataRead.py run for development test.")
    print("Please run main.py for actual operation.\r\n")

    read_data(read_data_type, ouput_path, output_file_name, output_extention)

    
