#!/usr/bin/env python3

import array
import sys
import ozpickle
from uuid import UUID
from ozify import ozify

class OpSkip:
    def __str__(self):
        return 'skip'

class OpMove:
    def __init__(self, src, target, is_unify=False):
        self.src = src
        self.target = target
        self.is_unify = is_unify

    def __str__(self):
        return '{} {} {}'.format(
            ozify(self.target),
            '=' if self.is_unify else '<-',
            ozify(self.src)
        )

class OpMoveMove:
    def __init__(self, src1, target1, src2, target2):
        self.src1 = src1
        self.target1 = target1
        self.src2 = src2
        self.target2 = target2

    def __str__(self):
        return '{} <- {}\n{} <- {}'.format(
            ozify(self.target1), ozify(self.src1),
            ozify(self.target2), ozify(self.src2)
        )

class OpAllocate:
    def __init__(self, regs):
        self.regs = regs

    def __str__(self):
        return 'alloc ' + ' '.join(map(ozify, self.regs))

class OpCreateVar:
    def __init__(self, target):
        self.target = target

    def __str__(self):
        return '{} <- _'.format(ozify(self.target))

class OpCreateVarMove:
    def __init__(self, target1, target2):
        self.target1 = target1
        self.target2 = target2

    def __str__(self):
        return '{0} <- _\n{1} <- {0}'.format(ozify(self.target1), ozify(self.target2))

class OpSetupExceptionHandler:
    def __str__(self):
        return 'setup_eh'

class OpPopExceptionHandler:
    def __str__(self):
        return 'pop_eh'

class OpCall:
    def __init__(self, func, args, is_tail_call=False):
        self.is_tail_call = is_tail_call
        self.func = func
        self.args = args

    def __str__(self):
        retval = ('{{'+'{} {}'+'}}').format(ozify(self.func), ' '.join(map(ozify, self.args)))
        if self.is_tail_call:
            retval = 'tail ' + retval
        return retval

class OpReturn:
    def __str__(self):
        return 'return'

class OpBranch:
    def __init__(self, target_pc):
        self.target_pc = target_pc

    def __str__(self):
        return 'goto {}'.format(self.target_pc)

class OpCondBranch:
    def __init__(self, testreg, patterns, target_pcs, else_pc=None):
        self.testreg = testreg
        self.patterns = patterns
        self.target_pcs = target_pcs
        self.else_pc = else_pc

    def __str__(self):
        res = ['goto case ', ozify(self.testreg), '\n']
        is_first = True
        for pattern, target_pc in zip(self.patterns, self.target_pcs):
            if is_first:
                res.append('  of ')
                is_first = False
            else:
                res.append('  [] ')
            res.append(ozify(pattern))
            res.append(' then ')
            res.append(str(target_pc))
            res.append('\n')
        if self.else_pc is not None:
            res.append('  else ')
            res.append(str(self.else_pc))
            res.append('\n')
        res.append('end')
        return ''.join(res)

class OpUnknown:
    def __init__(self, arr):
        self.arr = arr

    def __str__(self):
        res = ['%', 'unknown', 'opcodes']
        res.extend(map('{:04x}'.format, self.arr))
        return ' '.join(res)

class OpInlineBinArith:
    def __init__(self, op1, binop, op2, result):
        self.op1 = op1
        self.binop = binop
        self.op2 = op2
        self.result = result

    def __str__(self):
        return '{} <- {} {} {}'.format(ozify(self.result),
                                       ozify(self.op1), self.binop, ozify(self.op2))

class OpInlineGetClass:
    def __init__(self, src, target):
        self.src = src
        self.target = target

    def __str__(self):
        return '{} <- {{Object.getClass {}}}'.format(ozify(self.target), ozify(self.src))


#-------------------------------------------------------------------------------

def decode(opcode, arr, pc, ks):
    def rpc(regclass, delta):
        num = arr[pc+delta]
        if regclass == 'K':
            return ks[num]
        else:
            return ['reg', regclass, num]

    def intpc(delta):
        return arr[pc+delta]

    def pattern_match(regclass):
        value = rpc(regclass, 1)
        pattern_value = ks[intpc(2)]
        patterns = []
        target_pcs = []
        for _, _, (pattern, dpc) in ks[intpc(2)][2]:
            patterns.append(pattern)
            target_pcs.append(pc + 3 + dpc)
        return OpCondBranch(value, patterns, target_pcs)

    def cond_branch(dfalse, delse):
        base = pc + 4
        return OpCondBranch(rpc('X', 1),
                            [True, False],
                            [base, base + dfalse],
                            else_pc=base + delse)

    def equals_integer():
        base = pc + 4
        return OpCondBranch(rpc('X', 1), [intpc(2)], [base], else_pc=base+intpc(3))

    def call(regclass, is_tail_call=False):
        args = [['reg', 'X', i] for i in range(intpc(2))]
        return OpCall(rpc(regclass, 1), args, is_tail_call=is_tail_call)

    def send_msg(regclass, is_tail_call=False):
        arity = rpc('K', 2)
        args = [['reg', 'X', i] for i in range(intpc(2))]
        msg = ['record/prenormalized', arity, args]
        ozpickle.normalize_record(msg)
        return OpCall(rpc(regclass, 1), [msg], is_tail_call=is_tail_call)

    def call_builtin():
        args_count = intpc(2)
        args = [rpc('X', n) for n in range(3, 3+args_count)]
        return (2 + args_count, OpCall(rpc('K', 1), args))

    DECODERS = {
        0x00: lambda: (0, OpSkip()),
        0x01: lambda: (2, OpMove(rpc('X', 1), rpc('X', 2))),
        0x02: lambda: (2, OpMove(rpc('X', 1), rpc('Y', 2))),
        0x03: lambda: (2, OpMove(rpc('Y', 1), rpc('X', 2))),
        0x04: lambda: (2, OpMove(rpc('Y', 1), rpc('Y', 2))),
        0x05: lambda: (2, OpMove(rpc('G', 1), rpc('X', 2))),
        0x06: lambda: (2, OpMove(rpc('G', 1), rpc('Y', 2))),
        0x07: lambda: (2, OpMove(rpc('K', 1), rpc('X', 2))),
        0x08: lambda: (2, OpMove(rpc('K', 1), rpc('Y', 2))),
        0x09: lambda: (4, OpMoveMove(rpc('X', 1), rpc('Y', 2), rpc('X', 3), rpc('Y', 4))),
        0x0a: lambda: (4, OpMoveMove(rpc('Y', 1), rpc('X', 2), rpc('Y', 3), rpc('X', 4))),
        0x0b: lambda: (4, OpMoveMove(rpc('Y', 1), rpc('X', 2), rpc('X', 3), rpc('Y', 4))),
        0x0c: lambda: (4, OpMoveMove(rpc('X', 1), rpc('Y', 2), rpc('Y', 3), rpc('X', 4))),
        0x0d: lambda: (1, OpAllocate([['reg', 'Y', n] for n in range(intpc(1))])),
        0x0f: lambda: (1, OpCreateVar(rpc('X', 1))),
        0x10: lambda: (1, OpCreateVar(rpc('Y', 1))),
        0x11: lambda: (2, OpCreateVarMove(rpc('X', 1), rpc('X', 2))),
        0x12: lambda: (2, OpCreateVarMove(rpc('Y', 1), rpc('X', 2))),
        0x18: lambda: (0, OpSetupExceptionHandler()),
        0x19: lambda: (0, OpPopExceptionHandler()),
        0x20: lambda: (1, OpCall(rpc('K', 1), [])),
        0x21: lambda: (2, OpCall(rpc('K', 1), [rpc('X', 2)])),
        0x22: lambda: (3, OpCall(rpc('K', 1), [rpc('X', n) for n in range(2, 4)])),
        0x23: lambda: (4, OpCall(rpc('K', 1), [rpc('X', n) for n in range(2, 5)])),
        0x24: lambda: (5, OpCall(rpc('K', 1), [rpc('X', n) for n in range(2, 6)])),
        0x25: lambda: (6, OpCall(rpc('K', 1), [rpc('X', n) for n in range(2, 7)])),
        0x26: call_builtin,
        0x27: lambda: (2, call('X')),
        0x28: lambda: (2, call('Y')),
        0x29: lambda: (2, call('G')),
        0x2a: lambda: (2, call('K')),
        0x2b: lambda: (2, call('X', is_tail_call=True)),
        0x2c: lambda: (2, call('Y', is_tail_call=True)),
        0x2d: lambda: (2, call('G', is_tail_call=True)),
        0x2e: lambda: (2, call('K', is_tail_call=True)),
        0x30: lambda: (3, send_msg('X')),
        0x31: lambda: (3, send_msg('Y')),
        0x32: lambda: (3, send_msg('G')),
        0x33: lambda: (3, send_msg('K')),
        0x34: lambda: (3, send_msg('X', is_tail_call=True)),
        0x35: lambda: (3, send_msg('Y', is_tail_call=True)),
        0x36: lambda: (3, send_msg('G', is_tail_call=True)),
        0x37: lambda: (3, send_msg('K', is_tail_call=True)),
        0x40: lambda: (0, OpReturn()),
        0x41: lambda: (1, OpBranch(pc + 2 + intpc(1))),
        0x42: lambda: (1, OpBranch(pc + 2 - intpc(1))),
        0x43: lambda: (3, cond_branch(intpc(2), intpc(3))),
        0x44: lambda: (3, cond_branch(intpc(2), -intpc(3))),
        0x45: lambda: (3, cond_branch(-intpc(2), intpc(3))),
        0x46: lambda: (3, cond_branch(-intpc(2), -intpc(3))),
        0x47: lambda: (2, pattern_match('X')),
        0x48: lambda: (2, pattern_match('Y')),
        0x49: lambda: (2, pattern_match('G')),
        0x50: lambda: (2, OpMove(rpc('X', 1), rpc('X', 2), is_unify=True)),
        0x51: lambda: (2, OpMove(rpc('X', 1), rpc('Y', 2), is_unify=True)),
        0x52: lambda: (2, OpMove(rpc('X', 1), rpc('G', 2), is_unify=True)),
        0x53: lambda: (2, OpMove(rpc('X', 1), rpc('K', 2), is_unify=True)),
        0x54: lambda: (2, OpMove(rpc('Y', 1), rpc('Y', 2), is_unify=True)),
        0x55: lambda: (2, OpMove(rpc('Y', 1), rpc('G', 2), is_unify=True)),
        0x56: lambda: (2, OpMove(rpc('Y', 1), rpc('K', 2), is_unify=True)),
        0x57: lambda: (2, OpMove(rpc('G', 1), rpc('G', 2), is_unify=True)),
        0x58: lambda: (2, OpMove(rpc('G', 1), rpc('K', 2), is_unify=True)),
        0x59: lambda: (2, OpMove(rpc('K', 1), rpc('K', 2), is_unify=True)),
        0x80: lambda: (3, equals_integer()),
        0x81: lambda: (3, OpInlineBinArith(rpc('X', 1), '+', rpc('X', 2), rpc('X', 3))),
        0x82: lambda: (3, OpInlineBinArith(rpc('X', 1), '-', rpc('X', 2), rpc('X', 3))),
        0x83: lambda: (2, OpInlineBinArith(rpc('X', 1), '+', 1, rpc('X', 2))),
        0x84: lambda: (2, OpInlineBinArith(rpc('X', 1), '-', 1, rpc('X', 2))),
        0x90: lambda: (2, OpInlineGetClass(rpc('X', 1), rpc('X', 2))),
    }

    try:
        if opcode in DECODERS:
            return DECODERS[opcode]()

        # create struct
        elif opcode & ~0x1f == 0x60:
            what = ['abstraction', 'cons', 'tuple', 'record/prenormalized'][opcode & 3]

            (target, is_unify) = [
                ('X', False),
                ('Y', False),
                ('X', True),
                ('Y', True),
                ('G', True),
                ('K', True),
            ][(opcode >> 2) & 7]

            length = intpc(2)
            label = rpc('K', 1) if what != 'cons' else None
            pre_ops = []
            contents = []

            i = 0
            pc_delta = 4
            while i < length:
                sub_op = intpc(pc_delta)

                if sub_op < 6:
                    regclass = ['X', 'Y', 'G', 'K', '?X', '?Y'][sub_op]
                    contents.append(rpc(regclass, pc_delta+1))
                    i += 1
                elif sub_op == 6:
                    count = intpc(pc_delta+1)
                    contents.extend([['patmatwildcard']] * count)
                    i += count
                else:
                    raise ValueError('Unknown sub-opcode for OpCreateStruct')

                pc_delta += 2

            if what == 'cons':
                src = contents
                src.insert(0, 'cons')
            elif what == 'abstraction':
                src = ['abstraction', None, {
                    'codearea': label,
                    'gs': contents
                }]
            else:
                src = [what, label, contents]
                ozpickle.normalize_record(src)

            return (pc_delta-1, OpMove(src, rpc(target, 3), is_unify=is_unify))

    except Exception as e:
        print(e)
        pass

    if opcode <= 0x90 and opcode not in DECODERS:
        raise ValueError(hex(opcode))

    length = len(arr) - pc - 1
    return (length, OpUnknown(arr[pc:]))


def to_opcodes(b, ks):
    arr = array.array('H')
    if arr.itemsize != 2:
        raise TypeError('"unsigned short" is not 2 bytes.')

    arr.frombytes(b)
    if sys.byteorder != 'big':
        arr.byteswap()

    program_size = len(arr)
    pc = 0

    while pc < program_size:
        opcode = arr[pc]
        (pc_inc, code) = decode(opcode, arr, pc, ks)
        yield (pc, code)
        pc += 1 + pc_inc

