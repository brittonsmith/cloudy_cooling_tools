"""
Britton Smith <brittonsmith@gmail.com>

A wrapper for the hdf5 cooling grid tools: convert, graft, and zero.

"""

from grid_tools import *
import sys

def convert(args):
    cloudyGrid_ascii2hdf5(args[0], args[1])

def graft(args):
    graft_grid(args[0], args[1], args[2])

def zero(args):
    input = args.pop(0)
    output = None
    fields = ['MMW']
    while args:
        arg = args.pop(0)
        if arg == '-f':
            fields = []
            while args: fields.append(args.pop(0))
        else:
            output = arg
    zero_dataset(input, output_file=output, data_fields=fields)

actions = {'convert': {'usage': 'convert <path to run file> <output file>',
                       'function': convert},
           'graft': {'usage': 'graft <low T data (w/ e- fraction)> <high T data (w/o e- fraction)> <output file>',
                     'function': graft},
           'zero': {'usage': 'zero <input file> [output file] [-f <fields>]',
                    'function': zero}}

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
