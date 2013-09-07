#!/usr/bin/env python3

import ozpickle
import opcodes
import sys
import argparse
import collections
try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

CodeAreaDumpState = collections.namedtuple('CodeAreaDumpState',
                                           ['visited', 'filter'])

def visit_object(obj, state):
    if id(obj) in state.visited:
        return True
    else:
        state.visited.add(id(obj))
        return False


def disassemble(unpickled_obj, ns):
    state = CodeAreaDumpState(set(), ns.filter)
    dump_codearea(unpickled_obj, state)

@singledispatch
def dump_codearea(k, state):
    pass

@dump_codearea.register(list)
def _(lst, state):
    if visit_object(lst, state):
        return

    if lst and lst[0] == 'codearea':
        ca = lst[2]
        name = ca['name']
        if state.filter is None or name == state.filter:
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
        dump_codearea(item, state)


@dump_codearea.register(tuple)
@dump_codearea.register(dict)
def _(tup, state):
    if visit_object(tup, state):
        return

    values = tup if not isinstance(tup, dict) else tup.values()
    for item in values:
        dump_codearea(item, state)


def main(args=None):
    parser = argparse.ArgumentParser(description='Disassemble *.ozf files')
    parser.add_argument('-f', '--filter', help='Keep only procedures with this name')
    parser.add_argument('ozf', type=argparse.FileType('rb'), help='The file to disassemble')
    ns = parser.parse_args(args)

    content = ozpickle.load(ns.ozf)
    disassemble(content, ns)

if __name__ == '__main__':
    main()
