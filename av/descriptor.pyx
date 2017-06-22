mimport av.utils as utils

cimport libav as lib

from .option cimport Option, OptionChoice, wrap_option, wrap_option_choice


cdef Descriptor wrap_avclass(const lib.AVClass *ptr):
    if ptr == NULL:
        return None
    cdef Descriptor obj = @{utils.alloc_private('Descriptor')}
    obj.ptr = ptr
    return obj


cdef class Descriptor(object):

    @@utils.def_private_cinit()

    property name:
        def __get__(self): return self.ptr.class_name if self.ptr.class_name else None

    @@utils.cached_property('options'):
        def __get__(self):

            cdef lib.AVOption *ptr = self.ptr.option
            cdef lib.AVOption *choice_ptr

            options = []

            while ptr != NULL and ptr.name != NULL:
                if ptr.type == lib.AV_OPT_TYPE_CONST:
                    ptr += 1
                    continue
                choices = []
                if ptr.unit != NULL:  # option has choices (matching const options)
                    choice_ptr = self.ptr.option
                    while choice_ptr != NULL and choice_ptr.name != NULL:
                        if choice_ptr.type != lib.AV_OPT_TYPE_CONST or choice_ptr.unit != ptr.unit:
                            choice_ptr += 1
                            continue
                        choices.append(wrap_option_choice(choice_ptr))
                        choice_ptr += 1
                options.append(wrap_option(tuple(choices), ptr))
                ptr += 1

            return tuple(options)

    def __repr__(self):
        return '<av.%s %s at 0x%x>' % (self.__class__.__name__, self.name, id(self))
