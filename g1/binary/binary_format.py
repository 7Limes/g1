from construct import Struct, Const, Int32ub, Int32sb, Int16ub, Int8ub, Array, this, Computed
from typing import Any
from construct.lib import Container, ListContainer
from io import BytesIO

from ..instructions.instructions import INSTRUCTIONS, ARGUMENT_COUNTS


INSTRUCTION_IDS = {ins: i for i, ins in enumerate(INSTRUCTIONS)}
SIGNATURE = b'g1'

ARG_TYPE_LITERAL = 0
ARG_TYPE_ADDRESS = 1


G1Argument = Struct(
    'type' / Int8ub,
    'value' / Int32sb
)


G1Instruction = Struct(
    'id' / Int8ub,
    'argument_count' / Computed(lambda ctx: ARGUMENT_COUNTS[ctx.id]),
    'arguments' / Array(this.argument_count, G1Argument)
)


G1DataEntry = Struct(
    'address' / Int32ub,
    'size' / Int32ub,
    'values' / Array(this.size, Int32sb)
)


G1BinaryFormat = Struct(
    'signature' / Const(SIGNATURE),
    'meta' / Struct(
        'memory' / Int32ub,
        'width' / Int16ub,
        'height' / Int16ub,
        'tickrate' / Int16ub
    ),
    'tick' / Int32sb,
    'start' / Int32sb,
    'instruction_count' / Int32ub,
    'instructions' / Array(this.instruction_count, G1Instruction),
    'data_entry_count' / Int32ub,
    'data' / Array(this.data_entry_count, G1DataEntry)
)


def format_json(program_json: dict):
    """
    Converts a program JSON into one that can be parsed into a binary.
    """
    output_json = program_json.copy()
    output_json['instruction_count'] = len(program_json['instructions'])
    output_json.setdefault('start', -1)
    output_json.setdefault('tick', -1)

    verbose_instructions = []
    for instruction_data in program_json['instructions']:
        instruction_name, arguments = instruction_data[:2]  # only grab the first 2 in case of debug mode
        verbose_arguments = []
        for argument in arguments:
            if isinstance(argument, int):
                verbose_arguments.append({'type': ARG_TYPE_LITERAL, 'value': argument})
            else:
                verbose_arguments.append({'type': ARG_TYPE_ADDRESS, 'value': int(argument[1:])})
        instruction_id = INSTRUCTION_IDS[instruction_name]
        verbose_instruction = {
            'id': instruction_id,
            'arguments': verbose_arguments
        }
        verbose_instructions.append(verbose_instruction)
    output_json['instructions'] = verbose_instructions

    if 'data' in program_json:
        verbose_data_entries = []
        for address, data_values in program_json['data']:
            verbose_data_entries.append({'address': address, 'size': len(data_values), 'values': data_values})
        output_json['data_entry_count'] = len(verbose_data_entries)
        output_json['data'] = verbose_data_entries
    else:
        output_json['data_entry_count'] = 0
        output_json['data'] = {}

    return output_json


def container_to_dict(container: Any):
    if isinstance(container, Container):
        return {key: container_to_dict(value) for key, value in container.items() if not key.startswith('_')}
    elif isinstance(container, ListContainer):
        return [container_to_dict(item) for item in container]
    elif isinstance(container, BytesIO):
        return int.from_bytes(container, 'big')
    else:
        return container
    

def parse_to_program_data(file_content: bytes) -> dict:
    parsed_data = G1BinaryFormat.parse(file_content)
    program_data = container_to_dict(parsed_data)

    # Remove unnecessary fields
    del program_data['signature']
    del program_data['instruction_count']
    if program_data['start'] == -1:
        del program_data['start']
    if program_data['tick'] == -1:
        del program_data['tick']
    if not program_data['data']:
        del program_data['data_entry_count']
        del program_data['data']
    
    def convert_argument(arg_data: dict) -> int|str:
        if arg_data['type'] == ARG_TYPE_LITERAL:
            return arg_data['value']
        return f'${arg_data["value"]}'
    
    new_instructions = []
    for instruction_data in program_data['instructions']:
        instruction_name = INSTRUCTIONS[instruction_data['id']]
        converted_args = [convert_argument(a) for a in instruction_data['arguments']]
        new_instructions.append([instruction_name, converted_args])
    program_data['instructions'] = new_instructions
    
    if program_data.get('data'):
        new_data_entries = []
        for data_entry in program_data['data']:
            new_data_entries.append([data_entry['address'], data_entry['values']])
        program_data['data'] = new_data_entries

    return program_data