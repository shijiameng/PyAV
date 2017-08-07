import av
import PIL

from tests.common import fate_suite

png = fate_suite('png1/55c99e750a5fd6_50314226.png')
print png

c = av.open(png)
frames = list(c.decode(video=0))
frame = frames[0]

p = frame.planes[0]
print 'line_size:', p.line_size

a = frame.to_ndarray()

print 'shape:', a.shape
print 'strides:', a.strides

# >>> frames = (p.decode_one() for p in av.open("/tmp/%03d.png").demux(video=(0,)))
# >>> ndarrays = (f.to_nd_array() for f in frames if f is not None)
# >>> np.all(np.array(PIL.Image.open("/tmp/000.png")) == next(ndarrays))
