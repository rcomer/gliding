#!/usr/bin/env python
"""Command line interface to plot multiple traces with glidertrace.py"""

import argparse
import os
import glob

import matplotlib.pyplot as plt
import numpy as np
import cartopy.crs as ccrs

import glidertrace

# Get command line arguments
parser = argparse.ArgumentParser(description='Plot all traces in a directory')
parser.add_argument('directory',
                    help='A directory containing one or more IGC logger files')
parser.add_argument('title', help='A title for the map')
parser.add_argument('--imagefile', '-f', default=None,
                    help=('File to write A4 landscape map into.  If not set, '
                          'opens Matplotlib display.'))
parser.add_argument('--turnpointlist', '-t', nargs='+',
                    help='List of BGA trigraphs for annotation')
parser.add_argument('--zoom', '-z', type=int, default=10,
                    help=('Map detail level.  Use 10 for large tasks, 12 for '
                          'local tasks'))

args = parser.parse_args()
lgdir = args.directory+'/'
recordfile = lgdir+'records.txt'

files = glob.glob(lgdir+'*.igc') + glob.glob(lgdir+'*.IGC')

# Get logger header records
if os.path.isfile(recordfile):
    records = glidertrace.read_header_records(recordfile)
    files_new = list(set(files) -
                     set([record.get('logger_file') for record in records]))
    if len(files_new) > 0:
        glidertrace.write_header_records(files_new, recordfile, append=True)
        editor = os.getenv('EDITOR', 'gedit')
        x = os.spawnlp(os.P_WAIT, editor, editor, recordfile)
        records = glidertrace.read_header_records(recordfile)
else:
    glidertrace.write_header_records(files, recordfile)
    editor = os.getenv('EDITOR', 'gedit')
    x = os.spawnlp(os.P_WAIT, editor, editor, recordfile)
    records = glidertrace.read_header_records(recordfile)

files = [record.get('logger_file') for record in records]
labels = ['{} {}'.format(record.get('pilot'), record.get('compno')) for
          record in records]
labels, files = zip(*sorted(zip(labels, files)))  # alphabetize


# Choose colours
if len(labels) > 3:
    colors = []
    cmap = plt.get_cmap('gist_rainbow_r')
    for i, pilot in enumerate(labels):
        colors.append(cmap(float(i) / (len(labels) - 1)))
else:
    colors = ['magenta', 'blue', 'red']


# Read traces from files
flights = []
for lgfile in files:
    flight = glidertrace.GliderFlight(lgfile, skip_declaration=True)
    flights.append(flight)

# Plot traces
ax1 = glidertrace.plotmap(flights, zoom=args.zoom, tracecolors=colors,
                          aspectratio=11.7/8.3)

# Plot turnpoints if given
if args.turnpointlist:
    dummy = glidertrace.Task(args.turnpointlist)
    source_crs = ccrs.PlateCarree()
    target_crs = ax1.projection
    for name, coord in dummy.latlon.items():
        ax1.annotate(
            name,
            xy=target_crs.transform_point(coord[0], coord[1], source_crs),
            bbox=dict(boxstyle="round", fc="w"), fontsize='small')

# Add title and legend
ax1.set_title(args.title, fontsize='large')
if len(labels) >= 12:
    ncol = 3
else:
    ncol = 2
leg = ax1.legend(labels, ncol=ncol, loc=4)
for legobj in leg.legendHandles:
    legobj.set_linewidth(2.0)

if args.imagefile is not None:
    fig = plt.gcf()
    fig.tight_layout()
    fig.set_size_inches((11.7, 8.3))
    plt.savefig(args.imagefile)
else:
    plt.show()
