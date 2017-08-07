import numpy as np

class Test(object):

    def __array__(self):
        print 'array!'
        return np.array([1, 2, 3])


x = np.array(Test())
print repr(x)


