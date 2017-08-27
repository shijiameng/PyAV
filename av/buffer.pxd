
cdef class _Buffer(object):

    cdef size_t _buffer_size(self)
    cdef void* _buffer_ptr(self)
    cdef bint _buffer_writable(self)
    cdef _buffer_strides(self)
    cdef _buffer_shape(self)


cdef class Buffer(_Buffer):
    pass
