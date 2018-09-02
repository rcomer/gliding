#!/usr/bin/env python

# Command line interface for plotflight in glidertrace.py

from glidertrace import plotflight
import argparse

parser = argparse.ArgumentParser(description='Plot a glider trace')
parser.add_argument('filename', help='An IGC logger file')
parser.add_argument('--pilot', '-p', nargs='+', help='Name of pilot')
parser.add_argument('--glider', '-g', help=('Glider registration or '
                                            'competition number'))
parser.add_argument('--zoom', '-z', type=int, default=10,
                    help=('Map detail level.  Use 10 for large tasks, 12 for '
                          'local tasks'))
parser.add_argument('--task', '-t', nargs='+', help='List of BGA trigraphs')
parser.add_argument('--notask', '-n', action='store_true',
                    help='Do not plot a task')
parser.add_argument('--maponly', action='store_true',
                    help='Do not plot altitude graph')

args = parser.parse_args()

if args.pilot:
    pilot = ' '.join(args.pilot)
else:
    pilot = None

if args.notask:
    task = []
else:
    task = args.task

plotflight(args.filename, pilot, args.glider, task, zoom=args.zoom,
           altitude=not args.maponly)
