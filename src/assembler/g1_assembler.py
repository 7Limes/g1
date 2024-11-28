"""
Assembler implementation for g1 assembly programs.

By Miles Burkart
https://github.com/7Limes
"""

import sys
import os
import json
from enum import Enum
from typing import List, Dict
from rply import LexerGenerator, Token, LexingError

if __name__ == '__main__':
    from data import parse_data
else:
    from assembler.data import parse_data


class CompilerState(Enum):
    META = 1
    PROCEDURES = 2


lg = LexerGenerator()
lg.add('META_VARIABLE', r'#[A-z]+')
lg.add('NUMBER', r'-?\d+')
lg.add('ADDRESS', r'\$\d+')
lg.add('LABEL_NAME', r'[A-z0-9_]+:')
lg.add('NAME', r'[A-z_][A-z0-9_]*')
lg.add('COMMENT', r'\([^)]*\)')
lg.add('NEWLINE', r'\n')
lg.ignore(r' ')
lexer = lg.build()

META_VARIABLES = {
    'memory': 128,
    'width': 100,
    'height': 100,
    'tickrate': 60
}

INSTRUCTIONS = {
    'mov': 2,
    'movp': 2,

    'add': 3,
    'sub': 3,
    'mul': 3,
    'div': 3,
    'mod': 3,
    'less': 3,
    'equal': 3,
    'not': 2,

    'jmp': 2,

    'color': 3,
    'point': 2,
    'line': 4,
    'rect': 4,

    'print': 1
}

ASSIGNMENT_INSTRUCTIONS = {'mov', 'movp', 'add', 'sub', 'mul', 'div', 'mod', 'less', 'equal', 'not'}


def error(token: Token, source_lines: List[str], message: str):
    line_number = token.source_pos.lineno-1
    column_number = token.source_pos.colno-1
    print('ASSEMBLER ERROR:', message)
    print(f'{line_number+1} | {source_lines[line_number]}')
    print(f'{" " * (len(str(line_number))+3+column_number)}^')
    sys.exit()


def warn(token: Token, source_lines: List[str], message: str):
    line_number = token.source_pos.lineno-1
    column_number = token.source_pos.colno-1
    print('ASSEMBLER WARNING:', message)
    print(f'{line_number+1} | {source_lines[line_number]}')
    print(f'{" " * (len(str(line_number))+3+column_number)}^')


def get_until_newline(tokens: list[Token]) -> list[Token]:
    returned_tokens = []
    while True:
        token = tokens.next()
        if token.name == 'COMMENT':
            continue
        if token.name == 'NEWLINE':
            break
        returned_tokens.append(token)
    return returned_tokens


def parse_argument_token(token: Token, labels: Dict[str, int], source_lines: list[str]) -> str | int:
    if token.name == 'NUMBER':
        return int(token.value)
    if token.name == 'NAME':
        if token.value not in labels:
            error(token, source_lines, f'Undefined label "{token.value}".')
        return labels[token.value]
    return token.value


def assemble_tokens(tokens: list[Token], source_lines: List[str], compiler_state: CompilerState, debug: bool=False) -> Dict:
    output_json = {'meta': META_VARIABLES.copy()}
    
    labels = {}
    raw_instructions = []
    instruction_index = 0

    for token in tokens:
        if token.name == 'META_VARIABLE':
            if compiler_state != CompilerState.META:
                error(token, source_lines, f'Found meta variable outside file header.')
            meta_variable_name = token.value[1:]
            if meta_variable_name not in META_VARIABLES:
                error(token, source_lines, f'Unrecognized meta variable "{meta_variable_name}".')
            output_json['meta'][meta_variable_name] = int(tokens.next().value)
        
        elif token.name == 'LABEL_NAME':
            if compiler_state != CompilerState.PROCEDURES:
                compiler_state = CompilerState.PROCEDURES
            label_name = token.value[:-1]
            if label_name in labels:
                warn(token, source_lines, f'Label "{label_name}" declared more than once.')
            else:
                labels[label_name] = instruction_index
        
        elif token.name == 'NAME':
            if token.value not in INSTRUCTIONS.keys():
                error(token, source_lines, f'Unrecognized instruction "{token.value}".')

            instruction_name_token = token.value
            instruction_arg_amount = INSTRUCTIONS[token.value]
            instruction_args = get_until_newline(tokens)
            if len(instruction_args) != instruction_arg_amount:
                error(token, source_lines, f'Expected {instruction_arg_amount} argument(s) for instruction "{instruction_name_token}" but got {len(instruction_args)}.')
            raw_instructions.append([token, instruction_args])
            instruction_index += 1
        
        elif token.name in {'NUMBER', 'ADDRESS'}:
            error(token, source_lines, 'Value outside of instruction.')
        
        elif token.name in {'COMMENT', 'NEWLINE'}:
            continue
    
    # parse instruction args
    instructions = []
    for instruction_name_token, instruction_args_tokens in raw_instructions:
        instruction_name = instruction_name_token.value 
        instruction_args = [parse_argument_token(t, labels, source_lines) for t in instruction_args_tokens]
        instruction_data = [instruction_name, instruction_args]
        first_argument = instruction_args[0]
        if instruction_name in ASSIGNMENT_INSTRUCTIONS and isinstance(first_argument, int) and first_argument <= 11:
            warn(instruction_args_tokens[0], source_lines, 'Assignment to a reserved memory location.')
        if debug:
            instruction_data.append(instruction_name_token.source_pos.lineno-1)
        instructions.append(instruction_data)
    
    output_json['instructions'] = instructions
    if 'tick' in labels:
        output_json['tick'] = labels['tick']
    else:
        print('WARNING: "tick" label not found in program.')
    if 'start' in labels:
        output_json['start'] = labels['start']
    
    if debug:
        output_json['source'] = source_lines
    return output_json


def assemble(input_path: str, output_path: str, data_file_path: str|None=None, debug: bool=False):
    if not os.path.isfile(input_path):
        raise FileNotFoundError(f'File "{input_path}" does not exist.')
    with open(input_path, 'r') as f:
        source_code = f.read()
    
    source_lines = source_code.split('\n')
    tokens = lexer.lex(source_code + '\n')
    try:
        output_json = assemble_tokens(tokens, source_lines, CompilerState.META, debug)
    except LexingError as e:
        error(e, source_lines, 'Unrecognized token.')
    
    if data_file_path is not None and os.path.isfile(data_file_path):
        with open(data_file_path, 'r') as f:
            data = parse_data(f.read(), output_json['meta']['memory'])
            output_json['data'] = data

    file_content = json.dumps(output_json, separators=(',', ':'))
    with open(output_path, 'w') as f:
        f.write(file_content)


def parse_cli_flags(flags: str):
    flags_split = iter(flags.split())
    parsed_flags = {
        'debug': False
    }
    for flag in flags_split:
        if flag == '-d':
            parsed_flags['data'] = next(flags_split)
        elif flag == '-dbg':
            parsed_flags['debug'] = True
        else:
            print(f'Unrecognized flag "{flag}"')
    return parsed_flags


def main():
    args = sys.argv
    if len(args) == 1:
        print('Usage: g1_assembler [outfile] [infile] (-d [data file]) (-dbg)')
        return
    elif len(args) == 2:
        print('Expected infile at argument 2.')
        return
    if not os.path.isfile(args[2]):
        print(f'Could not find file "{args[2]}"')
        return
    flags = parse_cli_flags(' '.join(args[3:]))
    assemble(args[2], args[1], flags.get('data'), flags.get('debug'))


if __name__ == '__main__':
    main()