"""
A g1 virtual machine implementation made with pygame.

By Miles Burkart
https://github.com/7Limes
"""

import os
import json
import sys
import argparse
from g1.binary.binary_format import SIGNATURE as BINARY_FORMAT_SIGNATURE, parse_to_program_data
from g1.instructions.instructions import INSTRUCTIONS

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame

class G1PyException(Exception):
    pass

class ProgramContext:
    def __init__(self, program_data: dict, surface: pygame.Surface, data: list[list]|None=None):
        self.program_data = program_data
        amount_memory = program_data['meta']['memory']
        self.memory = [0] * amount_memory
        if data is not None:
            for address, data_numbers in data:
                upper_bound = address+len(data_numbers)
                if upper_bound > amount_memory:
                    raise G1PyException(f'ERROR: Data entry spans from {address} to {upper_bound} but only {amount_memory} slots were allocated. Consider allocating more memory.')
                self.memory[address:upper_bound] = data_numbers

        self.program_counter = 0
        self.color = (0, 0, 0)
        self.surface = surface


def error(program_context: ProgramContext, message: str):
    print('RUNTIME ERROR:', message)
    source_lines = program_context.program_data.get('source')
    if source_lines is not None:
        program_counter = program_context.program_counter
        line_number = program_context.program_data['instructions'][program_counter][2]
        print(f'{line_number+1} | {source_lines[line_number]}')
    sys.exit()


def memget(program_context: ProgramContext, index: int) -> int:
    if index < 0 or index >= len(program_context.memory):
        error(program_context, f'Cannot get at address {index} since it is out of bounds.')
    return program_context.memory[index]

def memset(program_context: ProgramContext, index: int, value: int):
    if index < 0 or index >= len(program_context.memory):
        error(program_context, f'Cannot set at address {index} since it is out of bounds.')
    program_context.memory[index] = value


def parse_arguments(program_context: ProgramContext, args: list[int|str]):
    return [memget(program_context, int(arg[1:])) if isinstance(arg, str) else arg for arg in args]

def ins_mov(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], args[1])
 
def ins_movp(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], memget(program_context, args[1]))

def ins_add(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], args[1] + args[2])

def ins_sub(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], args[1] - args[2])

def ins_mul(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], args[1] * args[2])

def ins_div(program_context: ProgramContext, args: list[int|str]):
    if args[2] == 0:
        error(program_context, 'Division by zero.')
    memset(program_context, args[0], args[1] // args[2])

def ins_mod(program_context: ProgramContext, args: list[int|str]):
    if args[2] == 0:
        error(program_context, 'Division by zero.')
    memset(program_context, args[0], args[1] % args[2])

def ins_less(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], int(args[1] < args[2]))

def ins_equal(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], int(args[1] == args[2]))

def ins_not(program_context: ProgramContext, args: list[int|str]):
    memset(program_context, args[0], int(not args[1]))

def ins_jmp(_: ProgramContext, args: list[int|str]):
    if args[1]:
        return args[0]

def ins_color(program_context: ProgramContext, args: list[int|str]):
    program_context.color = (args[0], args[1], args[2])

def ins_point(program_context: ProgramContext, args: list[int|str]):
    program_context.surface.set_at((args[0], args[1]), program_context.color)

def ins_line(program_context: ProgramContext, args: list[int|str]):
    pygame.draw.line(program_context.surface, program_context.color, (args[0], args[1]), (args[2], args[3]))

def ins_rect(program_context: ProgramContext, args: list[int|str]):
    pygame.draw.rect(program_context.surface, program_context.color, (args[0], args[1], args[2], args[3]))

def ins_log(_: ProgramContext, args: list[int|str]):
    print(args[0])


INSTRUCTION_FUNCTIONS = [
    ins_mov, ins_movp,
    ins_add, ins_sub, ins_mul, ins_div, ins_mod,
    ins_less, ins_equal, ins_not,
    ins_jmp,
    ins_color, ins_point, ins_line, ins_rect,
    ins_log
]

INSTRUCTION_LOOKUP = {ins: func for ins, func in zip(INSTRUCTIONS, INSTRUCTION_FUNCTIONS)}


def print_memory(memory: list[int], lower: int, upper: int):
    max_length = max(max([len(str(memory[i])) for i in range(lower, upper)]), 5)
    print('Address  ', end='')
    for i in range(lower, upper):
        print(f"{i:<{max_length+1}}", end='')
    print()
    print('Value    ', end='')
    for i in range(lower, upper):
        print(f"{memory[i]:<{max_length+1}}", end='')
    print()


def run_step_command(program_context: ProgramContext, command: str) -> int | None:
    if command.strip() == '':
        return 1
    command_split = command.strip().split()
    command = command_split[0]
    args = command_split[1:]
    if command == 'step':
        print(f'Stepping {int(args[0])}')
        return int(args[0])
    elif command == 'pm':
        if len(args) == 1:
            lower = int(args[0])
            upper = lower+1
        else:
            lower, upper = map(int, args[:2])
        print_memory(program_context.memory, lower, upper)
        return None


def start_program_thread(program_context: ProgramContext, index: int, step: bool=False, disable_log: bool=False):
    program_context.program_counter = index
    instructions = program_context.program_data['instructions']
    source_lines = program_context.program_data.get('source')
    step_amount = 0
    while program_context.program_counter < len(instructions):
        instruction_name, instruction_args = instructions[program_context.program_counter][:2]  # only grab the first 2 in case of debug mode
        if disable_log and instruction_name == 'log':
            program_context.program_counter += 1
            continue
        
        parsed_arguments = parse_arguments(program_context, instruction_args)
        new_program_counter = INSTRUCTION_LOOKUP[instruction_name](program_context, parsed_arguments)
        
        if step:
            if source_lines is not None:
                line_number = instructions[program_context.program_counter][2]
                print(f'Ran {program_context.program_counter}: {source_lines[line_number].lstrip()}')
            else:
                print(f'Ran {program_context.program_counter}: {instruction_name} {" ".join(map(str, instruction_args))}')
            if step_amount > 1:
                step_amount -= 1
            else:
                while True:
                    step_amount = run_step_command(program_context, input('> '))
                    if step_amount is not None:
                        break
        
        if new_program_counter is not None:
            program_context.program_counter = new_program_counter
        else:
            program_context.program_counter += 1


def update_reserved_memory(program_context: ProgramContext, delta_ms: int):
    meta = program_context.program_data['meta']
    keys = pygame.key.get_pressed()
    values = [
        int(keys[pygame.K_RETURN]),
        int(keys[pygame.K_RSHIFT]),
        int(keys[pygame.K_z]),
        int(keys[pygame.K_x]),
        int(keys[pygame.K_UP]),
        int(keys[pygame.K_DOWN]),
        int(keys[pygame.K_LEFT]),
        int(keys[pygame.K_RIGHT]),

        meta['memory'],
        meta['width'],
        meta['height'],
        meta['tickrate'],
        delta_ms
    ]
    program_context.memory[0:len(values)] = values


def run(program_data: dict, render_scale: int=1, show_fps: bool=False, enable_step: bool=False, disable_log: bool=False):
    """
    Run an assembled program.

    Flags:
        `-s [size]` -- Set the pixel size.\n
        `-f` -- Show framerate.\n
    """
    pygame.init()

    width = program_data['meta']['width']
    height = program_data['meta']['height']
    tickrate = program_data['meta']['tickrate']
    win = pygame.display.set_mode((width*render_scale, height*render_scale))
    draw_surface = pygame.Surface((width, height))
    pygame.display.set_caption('g1py')
    font = pygame.font.SysFont('Arial', 15)

    program_context = ProgramContext(program_data, draw_surface, program_data.get('data'))
    if 'start' in program_data:
        update_reserved_memory(program_context, 0)
        start_program_thread(program_context, program_data['start'], enable_step, disable_log)

    if 'tick' not in program_data:
        return
    tick_label_index = program_data['tick']

    clock = pygame.time.Clock()
    delta_ms: int = 0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        update_reserved_memory(program_context, delta_ms)
        start_program_thread(program_context, tick_label_index, step=False, disable_log=disable_log)

        resized_draw_surface = pygame.transform.scale(draw_surface, (width*render_scale, height*render_scale))
        win.blit(resized_draw_surface, (0, 0))

        if show_fps:
            fps_surf = font.render(f'{clock.get_fps():.2f}', True, (255, 0, 0))
            win.blit(fps_surf, (0, 0))
        
        pygame.display.flip()

        delta_ms = clock.tick(tickrate)


def run_file(file_path: str, render_scale: int=1, show_fps: bool=False, enable_step: bool=False, disable_log: bool=False):
    program_data = None
    with open(file_path, 'rb') as f:
        file_content = f.read()
        if file_content.startswith(BINARY_FORMAT_SIGNATURE):
            program_data = parse_to_program_data(file_content)
        else:
            program_data = json.loads(file_content.decode())

    run(program_data, render_scale, show_fps, enable_step, disable_log)


def main():
    parser = argparse.ArgumentParser(description='Run a g1 program')
    parser.add_argument('program_path', help='Path to the g1 program')
    parser.add_argument('--show_fps', '-fps', action='store_true', help='Display frames per second while the program is running')
    parser.add_argument('--scale', '-s', type=int, default=1, help='Set the render scale for the program window')
    parser.add_argument('--enable_step', '-S', action='store_true', help='Enable step mode for debugging')
    parser.add_argument('--disable_log', '-dl', action='store_true', help='Disable the log instruction. Disables messages being printed to stdout')
    args = parser.parse_args()
    
    run_file(args.program_path, args.scale, args.show_fps, args.enable_step, args.disable_log)


if __name__ == '__main__':
    main()