"""
Allows external data to be attached to assembled g1 programs via g1d files.
"""

import os
import re
from PIL import Image 
from io import BytesIO 


DATA_LINE_REGEX = r'^(\d+) ([fFbs]) (.+)$'
HEX_REGEX = r'([0-9a-fA-F]{2})+$'


class G1DataParserException(Exception):
    pass


def error(line_number: str, message: str):
    print(f'DATA ERROR: Line {line_number+1}: {message}')


def img_to_simg(img: Image.Image) -> list[int]:
    simg_data = [img.width, img.height]
    for i in range(img.height):
        for j in range(img.width):
            pixel = img.getpixel((j, i))
            pixel_int = pixel[2]
            pixel_int <<= 8
            pixel_int |= pixel[1]
            pixel_int <<= 8
            pixel_int |= pixel[0]
            simg_data.append(pixel_int)
    return simg_data


def parse_file(file_bytes: bytes, file_extension: str) -> list[int]:
    if file_extension.lower() in {'.png', '.jpg', '.bmp'}:
        img = Image.open(BytesIO(file_bytes))
        return img_to_simg(img)
    return list(file_bytes)


# returns True if succeeded, False otherwise
def add_data_entry(parsed_data: list, memory_size: int, line_number: int, entry: list) -> bool:
    address, numbers = entry
    if address+len(numbers) > memory_size:
        error(line_number, 'Entry data size exceeds memory capacity. Consider allocating more memory.')
        return False
    parsed_data.append(entry)
    return True


def parse_data(data_entries: str, memory_size: int) -> list | None:
    pattern = re.compile(DATA_LINE_REGEX);
    parsed_data = []
    for line_number, line in enumerate(data_entries.split('\n')):
        m = pattern.match(line)
        if not m:
            error(line_number, 'Expected [address] [f|F|b|s] [data] syntax for data entry.')
            return None
        address_str = m.group(1)
        data_type = m.group(2)
        data = m.group(3)

        if data_type == 'b':
            if not re.match(HEX_REGEX, data):
                error(line_number, 'Expected hex value for byte data.')
                return None
            data_numbers = [int(data[i:i+2], base=16) for i in range(0, len(data), 2)]
            if not add_data_entry(parsed_data, memory_size, line_number, [int(address_str), data_numbers]):
                return None
        
        elif data_type == 's':
            data_numbers = [ord(c) for c in data]
            data_numbers.insert(0, len(data))
            if not add_data_entry(parsed_data, memory_size, line_number, [int(address_str), data_numbers]):
                return None
        
        elif data_type in {'f', 'F'}:
            if not os.path.isfile(data):
                error(line_number, 'Path is either nonexistent or not a file.')
                return None
            with open(data, 'rb') as f:
                file_bytes = f.read()
            if data_type == 'F':
                parsed_data.append([int(address_str), list(file_bytes)])
                continue
            file_extension = os.path.splitext(data)[1]
            entry = [int(address_str), parse_file(file_bytes, file_extension)]
            if not add_data_entry(parsed_data, memory_size, line_number, entry):
                return None

        else:
            error(line_number, f'Invalid data type "{data_type}".')
            return None

    spans = [[a, a+len(data)-1] for a, data in parsed_data]
    spans.sort(key=lambda x: x[0])
    for i in range(len(spans)-1):
        for j in range(i+1, len(spans)):
            if spans[i][1] >= spans[j][0]:
                print(f'WARNING: Data overlap found between {spans[i]} and {spans[j]}.')
    
    return parsed_data
