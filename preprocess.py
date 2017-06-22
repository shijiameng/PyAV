from __future__ import print_function

import os
import re

try:
    from mako.template import Template
    from mako.lookup import TemplateLookup
    from mako import exceptions
    can_preprocess = True
except ImportError:
    can_preprocess = False


def reindent(n, rstrip=True):
    indent = ' ' * n
    def _reindent(source):

        lines = source.splitlines()

        while lines and not lines[0].strip():
            lines.pop(0)
        if not lines:
            return ''

        strip = len(lines[0]) - len(lines[0].lstrip())
        lines = [indent + l[strip:] for l in lines]
        out = '\n'.join(lines)

        if rstrip:
            out = out.rstrip()

        return out

    return _reindent


def resolve_mimport(module):
    module, ext = os.path.splitext(module)
    if ext not in ('.pxd', '.pyx', '.mako'):
        module = module + ext
        ext = '.pyx'
    path = '/' + module.replace('.', os.path.sep) + ext
    return path


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

        # Comments.
        m = re.match(r'(.+?)(#.*)$', line)
        if m:
            line, comment = m.groups()
        else:
            comment = ''

        # Mako namespaces v1.
        m = re.match(r'mimport\s+([\w\.]+)\s+as\s+(\w+)\s*$', line)
        if m:
            module, name = m.groups()
            path = resolve_mimport(module)
            output.append('<%namespace file="{}" name="{}" />\n'.format(path, name))
            continue

        # Mako namespaces v2.
        m = re.match(r'from\s+([\w\.]+)\s+mimport\s+([\w\s,]+)\s*$', line)
        if m:
            module, import_ = m.groups()
            path = resolve_mimport(module)
            output.append('<%namespace file="{}" import="{}" />\n'.format(path, import_))
            continue

        # Mixin definitions.
        m = re.match(r'([\t ]*)def\s+(?:@@\s*|__mixin__\s+)(.+?):\s*$', line)
        if m:
            body = get_body()
            body = reindent(0, False)(body)
            if '__body__' in body:
                body = '<% __body__ = capture(caller.body) %>\n' + body
            #body = body.replace('{__body__', '{capture(caller.body)')
            output.append('<%%def name="%s" buffered="True">\n' % m.group(2))
            output.append(body)
            output.append('</%def>\n\n')
            continue

        # Mixin use.
        m = re.match(r'([\t ]*)(?:@@\s*|__mixin__\s+)(.+?)(:?)\s*$', line)
        if m:
            indent, expr, has_body = m.groups()
            indent = len(indent.replace('\t', 8 * 'x'))
            output.append('<%%block filter="reindent(%d)"><%%call expr="%s">\n' % (indent, expr))
            if has_body:
                body = get_body()
                body = reindent(0, False)(body)
                output.append(body)
            output.append('</%call></%block>\n\n')
            continue

        output.append(line + comment + '\n')

    source = ''.join(output)

    # Interpret @{...} as a reindented ${...}
    source = re.sub(
        r'([\t ]*)@{(.+?)}',
        lambda m: '${%s|reindent(%d)}' % (m.group(2), len(m.group(1).replace('\t', '        '))),
        source,
    )

    # Very badly fix some escaping.
    source = re.sub(r'return ([\'"])<%', r'return \1<\1 \1%', source)

    return source



template_kwargs = dict(
    preprocessor=preprocess,
    imports=['from %s import reindent' % __name__],
    module_directory=os.path.abspath(os.path.join(__file__, '..', 'build', 'mako')),
)

lookup = TemplateLookup(
    directories=[os.path.dirname(__file__)],
    **template_kwargs
)

def render(path):
    template = lookup.get_template(path)
    return _render(template)

def render_source(source):
    template = Template(source, lookup=lookup, **template_kwargs)
    return _render(template)

def _render(template):

    prologue = []
    epilogue = []

    try:
        main_block = template.render(__prologue__=prologue, __epilogue__=epilogue)
    except Exception:
        print(exceptions.text_error_template().render())
        raise

    output = []
    if prologue:
        output.append('# === PROLOGUE ===')
        output.append('\n'.join(prologue).strip())
    output.append('# === MAIN ===')
    output.append(main_block.strip())
    if epilogue:
        output.append('# === EPILOGUE ===')
        output.append('\n'.join(epilogue).strip())

    return '\n\n'.join(output)


if __name__ == '__main__':

    print(render_source('''

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



def __mixin__ init_guard():

    <%
        if '__did_cimport_cinit_sentinel' not in globals():
            __did_cimport_cinit_sentinel = True
            __prologue__.append('from av.utils cimport cinit_sentinel')
    %>

    def __cinit__(self, sentinel, *args, **kwargs):
        if sentinel is not cinit_sentinel:
            raise RuntimeError('Cannot construct ' + self.__class__.__name__)

cdef class A(object):

    @@init_guard()

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


'''))

