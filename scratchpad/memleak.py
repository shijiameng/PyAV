import resource
import argparse
import os
import csv
import sys
import time
import gc
import psutil

# gc.set_debug(gc.DEBUG_LEAK)


import av.frame

proc = psutil.Process(os.getpid())
writer = csv.writer(sys.stdout)
writer.writerow(('rss', 'rss_delta', 'frames'))

last_rss = None
def check():
    global last_rss
    rss = proc.memory_info().rss
    if last_rss:
        diff = rss - last_rss
        writer.writerow((rss, diff, av.frame.frame_count))
        if diff:
            print >> sys.stderr, '+%7d -%7d = %d' % (diff if diff > 0 else 0, abs(diff) if diff < 0 else 0, rss)
    last_rss = rss

parser = argparse.ArgumentParser()
parser.add_argument('input')
args = parser.parse_args()


check()

container = av.open(args.input)
for i, packet in enumerate(container.demux()):
    #if not i % 10000:
    #    gc.collect()
    #print '\t\t\t', packet
    check()
    for frame in packet.decode():
        #print '\t\t\t', frame
        check()
        #del frame
    #del packet
    #time.sleep(0.1)
