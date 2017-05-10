
import re

from mako.template import Template

source = '''

def __mixin__ cached_prop(x):

    cdef _calc_${x}(self):
        @{__body__}

    cdef _cached_${x}

    property ${x}:
        def __get__(self):
            if self._cached_${x} is None:
                self._cached_${x} = self._calc_${x}()
            return self._cached_${x}


def __mixin__ notify_prop(public, private):

    property ${public}:
        def __get__(self):
            return self.${private}
        def __set__(self, new):
            old = self.${private}
            @{__body__}
            self.${private} = new


cdef class A(object):

    __mixin__ cached_prop('name'):
        return 123

    __mixin__ notify_prop('format', '_format'):
        self._rebuild_format()

    def _rebuild_format(self, attr, old, new):
        pass

'''


def preprocess(source):

    source = source.splitlines()

    source = [(len(line) - len(line.lstrip()), line) for line in source]


    output = []

    def get_body():
        body = []
        while source and ((not source[0][1].strip()) or (source[0][0] > lvl and source[0][1].strip())):
            body.append(source.pop(0)[1])
        body = '\n'.join(body)
        #body = reindent(0)(body)
        return body

    while source:

        lvl, line = source.pop(0)

        m = re.match(r'([\t ]*)def __mixin__ (.+?):\s*$', line)
        if m:
            body = get_body()
            body = reindent(0)(body)
            body = body.replace('{__body__', '{capture(caller.body)')
            output.append('<%%def name="%s" buffered="True">\n' % m.group(2))
            output.append(body)
            output.append('</%def>\n\n')
            continue

        m = re.match(r'([\t ]*)__mixin__ (.+?)(:?)\s*$', line)
        if m:
            indent, expr, has_body = m.groups()
            indent = len(indent.replace('\t', 8 * 'x'))
            output.append('<%%block filter="reindent(%d)"><%%call expr="%s">\n' % (indent, expr))
            if has_body:
                body = get_body()
                body = reindent(0)(body)
                output.append(body)
            output.append('</%call></%block>\n\n')
            continue

        output.append(line + '\n')

    source = ''.join(output)

    source = re.sub(
        r'([\t ]*)@{(.+?)}',
        lambda m: '${%s|reindent(%d)}' % (m.group(2), len(m.group(1).replace('\t', '        '))),
        source,
    )

    # print 'SOURCE'
    # print source
    # print '---'

    return source

def reindent(n):
    indent = ' ' * n
    def _reindent(source):
        lines = source.splitlines()
        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            return ''
        strip = len(lines[0]) - len(lines[0].lstrip())
        lines = [indent + l[strip:] for l in lines]
        return '\n'.join(lines)
    return _reindent


template = Template(source,
    imports=['from __main__ import reindent'],
    preprocessor=preprocess,
)

print template.render()


