#!/usr/bin/env python3

import re
try:
    from functools import singledispatch
except ImportError:
    from singledispatch import singledispatch

KEYWORDS = frozenset(['andthen', 'at', 'attr', 'case', 'catch', 'choice',
                      'class', 'cond', 'declare', 'define', 'dis', 'div',
                      'else', 'elsecase', 'elseif', 'end', 'export', 'fail',
                      'false', 'feat', 'finally', 'from', 'fun', 'functor',
                      'if', 'import', 'in', 'local', 'lock', 'meth', 'mod',
                      'not', 'of', 'or', 'orelse', 'prepare', 'proc', 'prop',
                      'raise', 'require', 'self', 'skip', 'then', 'thread',
                      'true', 'try', 'unit', 'for'])

def ozify_tuple(label, contents, **kwargs):
    if label == '#' and len(contents) >= 2:
        contents_strings = []
        for item in contents:
            item_string = ozify(item, **kwargs)
            if isinstance(item, list):
                item_string = '(' + item_string + ')'
            contents_strings.append(item_string)
        return '#'.join(contents_strings)
    else:
        return '{}({})'.format(ozify(label, **kwargs),
                               ' '.join(ozify(c, **kwargs) for c in contents))

def ozify_record(label, contents, **kwargs):
    entries = ['{}:{}'.format(ozify(k, **kwargs), ozify(v, **kwargs)) for k, v in contents]
    return '{}({})'.format(label, ' '.join(entries))

def ozify_abstraction(uuid, contents, **kwargs):
    if not kwargs.get('is_verbose_abstraction', False):
        return contents['codearea'][2]['name']
    else:
        return '<Abstraction {}/[{}]>'.format(ozify(contents['codearea'], **kwargs),
                                              ' '.join(ozify(c, **kwargs) for c in contents['gs']))

@singledispatch
def ozify(r, **kwargs):
    return str(r)

@ozify.register(bool)
def _(r, **kwargs):
    return 'true' if r else 'false'

@ozify.register(int)
@ozify.register(float)
def _(r, **kwargs):
    return str(r).replace('-', '~')

@ozify.register(str)
def _(r, **kwargs):
    if not re.match('^[a-z][a-z0-9A-Z_]*$', r) or r in KEYWORDS:
        return "'" + re.sub(r"(['\\])", r"\\\1", r) + "'"
    else:
        return r

@ozify.register(list)
def _(r, **kwargs):
    visited = kwargs.get('visited', set())
    if id(r) in visited:
        return '...'
    visited.add(id(r))
    kwargs['visited'] = visited

    return {
        'unit': lambda: 'unit',
        'cons': lambda x, y: '{}|{}'.format(ozify(x, **kwargs), ozify(y, **kwargs)),
        'tuple': lambda l, c: ozify_tuple(l, c, **kwargs),
        'record': lambda l, c: ozify_record(l, c, **kwargs),
        'builtin': lambda m, b: '{}.{}'.format(m, ozify(b, **kwargs)),
        'patmatwildcard': lambda: '_',
        'patmatcapture': lambda c: '?X{}'.format(c),
        'reg': lambda rc, n: '{}{}'.format(rc, n),
        'abstraction': lambda uuid, c: ozify_abstraction(uuid, c, **kwargs),
        'codearea': lambda uuid, d: "<CodeArea '{}'/{}>".format(d['name'], d['arity']),
        'uniquename': lambda c: '<UniqueName {}>'.format(c),
    }[r[0]](*r[1:])

