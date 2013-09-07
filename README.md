ozf2-disasm
===========

This is an application to disassemble `*.ozf` files generated in the Mozart/Oz 2.0 platform.

Usage:

```bash
./disasm.py [input.ozf]
```

The output format is an Oz-like ASM dialect. This is not the standard ASM though.

There is no guarantee yet that the produced ASM will be the same as the real code.

-----

The disassembler will produce the following instructions:

* `A <- B`. Assign the register A as the same as B.
* `A <- _`. Make the register A to be a variable.
* `A = B`. Unify the two registers A and B.
* `alloc Y0 Y1 Y2 …`. Allocate the listed persistent registers.
* `{P X0 X1 X2 …}`. Call a procedure.
* `tail {P X0 X1 X2 …}`. Call a procedure as tail.
* `goto 123`. Jump to instruction in the current code area at PC 123.
* `goto case A of xyz(?X5 ?X6 ?X7) then 1234 [] … end`. Conditionally jump to an instruction, only if A matches the pattern `xyz(?X5 ?X6 ?X7)`. The part after `goto` has the same syntax as a normal Oz case/of construction.
* `setup_eh`. Setup exception-handler.
* `pop_eh`. Pop exception-handler.
* `return`. Return and quit the code area.

