"""
A g1 virtual machine implementation made with pygame.

By Miles Burkart
https://github.com/7Limes
"""

import os
import json
import sys
from tabulate import tabulate

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = "hide"
import pygame
pygame.init()

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

def ins_print(_: ProgramContext, args: list[int|str]):
    print(args[0])


INSTRUCTIONS = {
    'mov': ins_mov,
    'movp': ins_movp,
    'add': ins_add,
    'sub': ins_sub,
    'mul': ins_mul,
    'div': ins_div,
    'mod': ins_mod,

    'less': ins_less,
    'equal': ins_equal,
    'not': ins_not,

    'jmp': ins_jmp,

    'color': ins_color,
    'point': ins_point,
    'line': ins_line,
    'rect': ins_rect,

    'print': ins_print
}


def run_step_command(program_context: ProgramContext, command: str):
    if command.strip() == '':
        return 1
    command_split = command.strip().split()
    command = command_split[0]
    args = command_split[1:]
    if command == 'step':
        print(f'Stepping {int(args[0])}')
        return int(args[0])
    if command == 'pm':
        lower, upper = map(int, args[:2])
        table = [list(range(lower, upper)), program_context.memory[lower:upper]]
        print(tabulate(table, headers='firstrow'))
        return None


def start_program_thread(program_context: ProgramContext, index: int, step: bool=False):
    program_context.program_counter = index
    instructions = program_context.program_data['instructions']
    source_lines = program_context.program_data.get('source')
    step_amount = 0
    while program_context.program_counter < len(instructions):
        instruction_name, instruction_args = instructions[program_context.program_counter][:2]  # only grab the first 2 in case of debug mode
        parsed_arguments = parse_arguments(program_context, instruction_args)
        new_program_counter = INSTRUCTIONS[instruction_name](program_context, parsed_arguments)
        
        if step:
            if source_lines is not None:
                line_number = instructions[program_context.program_counter][2]
                print(f'Running {program_context.program_counter}: {source_lines[line_number].lstrip()}')
            else:
                print(f'Running {program_context.program_counter}: {instruction_name} {" ".join(map(str, instruction_args))}')
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



def parse_flags(flags: str|None):
    pixel_size = 1
    show_fps = False
    step = False

    if flags is not None:
        args = iter(flags.split())
        for value in args:
            if value == '-s':
                pixel_size = int(next(args))
            elif value == '-f':
                show_fps = True
            elif value == '-S':
                step = True

    return (pixel_size, show_fps, step)


def run_file(file_path: str, flags: str):
    json_string = None
    with open(file_path, 'r') as f:
        json_string = f.read()

    run_string(json_string, flags)


def run_string(json_string: str, flags: str):
    program_data = json.loads(json_string)
    run(program_data, flags)


def run(program_data: dict, flags: str|None):
    """
    Run an assembled program.

    Flags:
        `-s [size]` -- Set the pixel size.\n
        `-f` -- Show framerate.\n
    """
    pixel_size, show_fps, step = parse_flags(flags)

    width = program_data['meta']['width']
    height = program_data['meta']['height']
    tickrate = program_data['meta']['tickrate']
    win = pygame.display.set_mode((width*pixel_size, height*pixel_size))
    draw_surface = pygame.Surface((width, height))
    pygame.display.set_caption('g1py')
    font = pygame.font.SysFont('Arial', 15)

    program_context = ProgramContext(program_data, draw_surface, program_data.get('data'))
    if 'start' in program_data:
        update_reserved_memory(program_context, 0.0)
        start_program_thread(program_context, program_data['start'], step)

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
        start_program_thread(program_context, tick_label_index)

        resized_draw_surface = pygame.transform.scale(draw_surface, (width*pixel_size, height*pixel_size))
        win.blit(resized_draw_surface, (0, 0))

        if show_fps:
            fps_surf = font.render(f'{clock.get_fps():.2f}', True, (255, 0, 0))
            win.blit(fps_surf, (0, 0))
        
        pygame.display.flip()

        delta_ms = clock.tick(tickrate)


def main():
    args = sys.argv
    flags = ''
    if len(args) == 1:
        print('Usage: g1 [path] (-s [scale factor]|-f|-S)')
        return
    if len(args) > 2:
        flags = ' '.join(args[2:])
    run_file(args[1], flags)


if __name__ == '__main__':
    main()