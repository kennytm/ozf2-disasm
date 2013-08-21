#!/usr/bin/env python3

import ozpickle
import opcodes
import sys
try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

@singledispatch
def dump_codearea(k, visited):
    pass

@dump_codearea.register(list)
def _(lst, visited):
    if id(lst) in visited:
        return
    visited.add(id(lst))

    if lst and lst[0] == 'codearea':
        ca = lst[2]
        args = ' '.join(map('X{}'.format, range(ca['arity'])))
        print('asm proc {{{} {}}}'.format(ca['name'] or '$', args))
        if ca['xcount'] > ca['arity']:
            print(' ', ' '.join(map('X{}'.format, range(ca['arity'], ca['xcount']))))
            print('in')
        for pc, opcode in opcodes.to_opcodes(ca['code'], ca['ks']):
            opcode_str = str(opcode)
            opcode_prefix = '  /* {:4} */    '.format(pc)
            for line in opcode_str.split('\n'):
                print(opcode_prefix, line)
        print('  /* {:4} */\nend\n'.format(len(ca['code'])//2))

        lst = ca['ks']

    for item in lst:
        dump_codearea(item, visited)


@dump_codearea.register(tuple)
@dump_codearea.register(dict)
def _(tup, visited):
    if id(tup) in visited:
        return
    visited.add(id(tup))

    values = tup if not isinstance(tup, dict) else tup.values()
    for item in values:
        dump_codearea(item, visited)


with open(sys.argv[1], 'rb') as f:
    content = ozpickle.load(f)
    dump_codearea(content, set())


