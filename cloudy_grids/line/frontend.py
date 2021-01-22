"""
Britton Smith <brittonsmith@gmail.com>

A wrapper for the hdf5 cooling grid tools: convert, graft, and zero.

"""

from grid_tools import *
import sys

def convert(args):
    cloudyGrid_ascii2hdf5(args[0], args[1])

actions = {'convert': {'usage': 'convert <path to run file> <output file>',
                       'function': convert}}

if len(sys.argv) < 2:
    print "Usage:"
    for act in actions.values():
        print "\tpython frontend.py " + act['usage']
    exit(0)
action = sys.argv[1]
if action in actions:
    actions[action]['function'](sys.argv[2:])
else:
    print "Usage:"
    for act in actions.values():
        print "\tpython frontend.py " + act['usage']
