from av.audio.format cimport get_audio_format
from av.audio.layout cimport get_audio_layout
from av.audio.plane cimport AudioPlane
from av.deprecation import renamed_attr
from av.utils cimport err_check


cdef object _cinit_bypass_sentinel

cdef AudioFrame alloc_audio_frame():
    """Get a mostly uninitialized AudioFrame.

    You MUST call AudioFrame._init(...) or AudioFrame._init_user_attributes()
    before exposing to the user.

    """
    return AudioFrame.__new__(AudioFrame, _cinit_bypass_sentinel)


cdef class AudioFrame(Frame):

    """A frame of audio."""

    def __cinit__(self, format='s16', layout='stereo', samples=0, align=True):
        if format is _cinit_bypass_sentinel:
            return

        cdef AudioFormat cy_format = AudioFormat(format)
        cdef AudioLayout cy_layout = AudioLayout(layout)
        self._init(cy_format.sample_fmt, cy_layout.layout, samples, align)

    cdef _init(self, lib.AVSampleFormat format, uint64_t layout, unsigned int nb_samples, bint align):

        self.align = align
        self.ptr.nb_samples = nb_samples
        self.ptr.format = <int>format
        self.ptr.channel_layout = layout

        # HACK: It really sucks to do this twice.
        self._init_user_attributes()

        cdef size_t buffer_size
        if self.layout.channels and nb_samples:

            # Cleanup the old buffer.
            lib.av_freep(&self._buffer)

            # Get a new one.
            self._buffer_size = err_check(lib.av_samples_get_buffer_size(
                NULL,
                len(self.layout.channels),
                nb_samples,
                format,
                align
            ))
            self._buffer = <uint8_t *>lib.av_malloc(self._buffer_size)
            if not self._buffer:
                raise MemoryError("cannot allocate AudioFrame buffer")

            # Connect the data pointers to the buffer.
            err_check(lib.avcodec_fill_audio_frame(
                self.ptr,
                len(self.layout.channels),
                <lib.AVSampleFormat>self.ptr.format,
                self._buffer,
                self._buffer_size,
                self.align
            ))

            self._init_planes(AudioPlane)

    def __dealloc__(self):
        lib.av_freep(&self._buffer)

    cdef _recalc_linesize(self):
        lib.av_samples_get_buffer_size(
            self.ptr.linesize,
            len(self.layout.channels),
            self.ptr.nb_samples,
            <lib.AVSampleFormat>self.ptr.format,
            self.align
        )
        # We need to reset the buffer_size on the AudioPlane/s. This is
        # an easy, if inefficient way.
        self._init_planes(AudioPlane)

    cdef _init_user_attributes(self):
        self.layout = get_audio_layout(0, self.ptr.channel_layout)
        self.format = get_audio_format(<lib.AVSampleFormat>self.ptr.format)
        self.nb_channels = lib.av_get_channel_layout_nb_channels(self.ptr.channel_layout)
        self.nb_planes = self.nb_channels if lib.av_sample_fmt_is_planar(<lib.AVSampleFormat>self.ptr.format) else 1
        self._init_planes(AudioPlane)

    def __repr__(self):
        return '<av.%s %d, pts=%s, %d samples at %dHz, %s, %s at 0x%x>' % (
            self.__class__.__name__,
            self.index,
            self.pts,
            self.samples,
            self.rate,
            self.layout.name,
            self.format.name,
            id(self),
        )

    property samples:
        """
        Number of audio samples (per channel).

        :type: int
        """
        def __get__(self):
            return self.ptr.nb_samples

    property sample_rate:
        """
        Sample rate of the audio data, in samples per second.

        :type: int
        """
        def __get__(self):
            return self.ptr.sample_rate
        def __set__(self, value):
            self.ptr.sample_rate = value

    property rate:
        """Another name for :attr:`sample_rate`."""
        def __get__(self):
            return self.ptr.sample_rate
        def __set__(self, value):
            self.ptr.sample_rate = value

    def to_ndarray(self, **kwargs):
        """
        Get a numpy array of this frame.
        """

        import numpy as np

        # map avcodec type to numpy type
        try:
            dtype = np.dtype({
                's16p':'<i2',
                'fltp':'<f4',
            }[self.format.name])
        except:
            raise AssertionError("Don't know how to convert data type.", self.format.name)

        # convert and return data
        return np.vstack(map(lambda x: np.frombuffer(x, dtype), self.planes))

    to_nd_array = renamed_attr('to_ndarray')
