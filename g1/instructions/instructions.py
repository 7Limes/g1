INSTRUCTIONS = ['mov', 'movp', 'add', 'sub', 'mul', 'div', 'mod', 'less', 'equal', 'not', 'jmp', 'color', 'point', 'line', 'rect', 'log']
ARGUMENT_COUNTS = [2, 2, 3, 3, 3, 3, 3, 3, 3, 2, 2, 3, 2, 4, 4, 1]
ARGUMENT_COUNT_LOOKUP = {i: c for i, c in zip(INSTRUCTIONS, ARGUMENT_COUNTS)}