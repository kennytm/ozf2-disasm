#!/usr/bin/env python3

import uuid
import re
try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

TYPE_IDS = [
    'int', #1
    'float', #2
    'bool', #3
    'unit', #4
    'atom', #5
    'cons', #6
    'tuple', #7
    'arity', #8
    'record', #9
    'builtin', #10
    'codearea', #11
    'patmatwildcard', #12
    'patmatcapture', #13
    'patmatconjunction', #14
    'patmatopenrecord', #15
    'abstraction', #16
    'chunk', #17
    'uniquename', #18
    'name', #19
    'namedname', #20
    'unicodeString', #21
]

class Cell:
    def __init__(self, index):
        self.index = index

    def __repr__(self):
        return 'Cell({})'.format(self.index)

@singledispatch
def resolve(node, nodes_list, resolved_objects):
    return node

@resolve.register(Cell)
def _(cell, nodes_list, resolved_objects):
    retval = resolve(nodes_list[cell.index], nodes_list, resolved_objects)
    nodes_list[cell.index] = retval
    return retval

def normalize_record(lst):
    if lst[0].endswith('/prenormalized'):
        lst[0] = lst[0][:-14]
        lst[2] = list(zip(lst[1][2], lst[2]))
        lst[1] = lst[1][1]
    elif lst[0] == '*':
        lst[:] = lst[1:]


@resolve.register(list)
def _(lst, nodes_list, resolved_objects):
    if id(lst) in resolved_objects:
        return lst
    resolved_objects.add(id(lst))

    for i, item in enumerate(lst):
        lst[i] = resolve(item, nodes_list, resolved_objects)

    normalize_record(lst)
    return lst

@resolve.register(dict)
def _(dct, nodes_list, resolved_objects):
    if id(dct) in resolved_objects:
        return dct
    resolved_objects.add(id(dct))

    for key in dct:
        dct[key] = resolve(dct[key], nodes_list, resolved_objects)

    return dct


class Unpickler:
    def __init__(self, fileobj):
        self.fileobj = fileobj

    def read(self, n):
        return self.fileobj.read(n)

    def read_int(self):
        return int.from_bytes(self.read(4), 'big')

    def read_str(self):
        length = self.read_int()
        return self.read(length).decode()

    def read_ref(self):
        index = self.read_int() - 1
        return Cell(index)

    def read_ref_list(self):
        count = self.read_int()
        retval = ['*']
        for _ in range(count):
            retval.append(self.read_ref())
        return retval

    def read_uuid(self):
        return uuid.UUID(bytes=self.read(16))

    def read_oz_int(self):
        return int(self.read_str().replace('~', '-'))

    def read_oz_float(self):
        return float(self.read_str().replace('~', '-'))

    def read_oz_bool(self):
        return bool(self.read(1))

    def read_oz_unit(self):
        return ['unit']

    def read_oz_atom(self):
        return self.read_str()

    def read_oz_cons(self):
        head = self.read_ref()
        tail = self.read_ref()
        return ['cons', head, tail]

    def read_oz_tuple(self):
        label = self.read_ref()
        contents = self.read_ref_list()
        return ['tuple', label, contents]

    def read_oz_arity(self):
        as_tuple = self.read_oz_tuple()
        return ['arity', as_tuple[1], as_tuple[2]]

    def read_oz_record(self):
        arity = self.read_ref()
        contents = self.read_ref_list()
        return ['record/prenormalized', arity, contents]

    def read_oz_builtin(self):
        module = self.read_str()
        builtin = self.read_str()
        return ['builtin', module, builtin]

    def read_oz_codearea(self):
        uuid = self.read_uuid()
        code_size = self.read_int()
        code = self.read(code_size*2)
        arity = self.read_int()
        xcount = self.read_int()
        name = self.read_str()
        debug_data = self.read_ref()
        ks = self.read_ref_list()
        return ['codearea', uuid, {
            'code': code,
            'arity': arity,
            'xcount': xcount,
            'name': name,
            'debug_data': debug_data,
            'ks': ks,
        }]

    def read_oz_patmatwildcard(self):
        return ['patmatwildcard']

    def read_oz_patmatcapture(self):
        return ['patmatcapture', self.read_int()]

    def read_oz_patmatconjunction(self):
        return ['patmatconjunction', self.read_ref_list()]

    def read_oz_patmatopenrecord(self):
        as_record = self.read_oz_record()
        return ['patmatopenrecord/prenormalized', as_record[1], as_record[2]]

    def read_oz_abstraction(self):
        uuid = self.read_uuid()
        codearea = self.read_ref()
        gs = self.read_ref_list()
        return ['abstraction', uuid, {
            'codearea': codearea,
            'gs': gs
        }]

    def read_oz_chunk(self):
        return ['chunk', self.read_ref()]

    def read_oz_uniquename(self):
        return ['uniquename', self.read_str()]

    def read_oz_name(self):
        return ['name', self.read_uuid()]

    def read_oz_namedname(self):
        uuid = self.read_uuid()
        name = self.read_str()
        return ['namedname', uuid, name]

    def read_oz_unicodeString(self):
        return ['unicodeString', self.read_str()]

    def unpickle(self):
        nodes_count = self.read_int()
        unresolved_nodes = set(range(nodes_count))
        nodes = [Cell(i) for i in range(nodes_count)]
        result_index = self.read_int() - 1
        while True:
            index = self.read_int() - 1
            if index < 0:
                break
            type_id = self.read(1)[0] - 1
            nodes[index] = getattr(self, 'read_oz_' + TYPE_IDS[type_id])()

        return resolve(nodes[result_index], nodes, set())


def load(fileobj):
    return Unpickler(fileobj).unpickle()


if __name__ == '__main__':
    import pprint
    import sys
    with open(sys.argv[1], 'rb') as f:
        pprint.pprint(load(f))




