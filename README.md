# g1

A minimal virtual machine designed for simple graphical applications.

Designed to be easy to implement on any platform.

## Specs

- Arbitrary amount of memory, controllable per program
  - Minimum 32 slots
  - Consists of signed 32 bit integers
- Simple graphics operations
  - Point
  - Line
  - Rect


## Reserved Memory Locations

Memory addresses are denoted with dollar signs (`$`) and use *decimal* numbers, not hex.

- `$0-8`: Input button states (updated every tick)
  - `$0`: CONTROL1
  - `$1`: CONTROL2
  - `$2`: A
  - `$3`: B
  - `$4`: UP
  - `$5`: DOWN
  - `$6`: LEFT
  - `$7`: RIGHT
- `$8`: Program memory size
- `$9`: Display Width
- `$10`: Display Height
- `$11`: Display Tickrate
- `$12`: Frame delta time (ms)


## Reserved Label Names

- `start`: Optional, jumped to once when the program is first run.
- `tick`: Required, jumped to on every tick.


## Instruction List

### Memory
- `mov [dest address] [src]`
  - Moves value from `src` to `dest`

### Math
- `add [dest address] [a] [b]`
- `sub [dest address] [a] [b]`
- `mul [dest address] [a] [b]`
- `div [dest address] [a] [b]`
- `mod [dest address] [a] [b]`

### Boolean
- `less [dest address] [a] [b]`
- `equal [dest address] [a] [b]`
- `not [dest address] [value]`

### Control Flow
- `jmp [label name | instruction index] [boolean value]`
  - If `boolean value` is nonzero, jump to the specified label or index.

### Graphics
- `color [r] [g] [b]`
- `point [x] [y]`
- `line [x1] [y1] [x2] [y2]`
- `rect [x] [y] [width] [height]`
