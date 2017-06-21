
import re

from mako.template import Template

source = '''

def __mixin__ cached_property_h(name, type='object'):
    cdef ${type} __cached_${name}

def __mixin__ cached_property(x, cast=None):
    <% body = capture(caller.body) %>
    property __uncached_${x}(self):
        % if '__get__' in body:
        @{body}
        % else:
        def __get__(self):
            @{body}
        % endif

    property ${x}:

        def __get__(self):
            if self.__cached_${x} is None:
                value = self.__uncached_${x}
                % if cast:
                value = ${cast}(value)
                % endif
                self.__cached_${x} = value
            return self.__cached_${x}

        % if '__set__' in body:
        def __set__(self, value):
            self.__uncached_${x} = value
            self.__cached_${x} = self.__uncached_${x}
        % endif


def @@notify_prop(public, private):

    property ${public}:
        def __get__(self):
            return self.${private}
        def __set__(self, new):
            old = self.${private}
            @{__body__}
            self.${private} = new


cdef class A(object):

    @@cached_property_h('noget', 'int')

    @@cached_property('noget'):
        return 123

    @@cached_property('hasget', cast='tuple'):
        def __get__(self):
            return 456

    @@cached_property('hasset'):
        def __get__(self):
            return 789
        def __set__(self, value):
            self._hasset = value # broken.

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
        return body

    while source:

        lvl, line = source.pop(0)

        m = re.match(r'([\t ]*)def\s+(?:@@\s*|__mixin__\s+)(.+?):\s*$', line)
        if m:
            body = get_body()
            body = reindent(0)(body)
            body = body.replace('{__body__', '{capture(caller.body)')
            output.append('<%%def name="%s" buffered="True">\n' % m.group(2))
            output.append(body)
            output.append('</%def>\n\n')
            continue

        m = re.match(r'([\t ]*)(?:@@\s*|__mixin__\s+)(.+?)(:?)\s*$', line)
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


