#!/usr/bin/env python
"""Plot flights from Competition Enterprise 2017"""

from glidertrace import *
import os
import glob
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
import numpy as np
import cartopy.crs as ccrs
import time

SOURCE_CRS = ccrs.PlateCarree()
OS_CRS = ccrs.OSGB()
    
DSGC_OS = OS_CRS.transform_point(-3.27, 50.85, SOURCE_CRS)


def plotonmap(lgdir, title, imagefile, turnpointlist=None, plot_extras=None, labels_use=None, zoom=9):
    recordfile = lgdir+'/records.txt'

    files = glob.glob(lgdir+'/*.igc') + glob.glob(lgdir+'/*.IGC')

    # Get logger header records
    if os.path.isfile(recordfile):
        records = read_header_records(recordfile)
        files_new = list(set(files) - set([record.get('logger_file') for record in records]))
        if len(files_new) > 0:
            write_header_records(files_new, recordfile, append=True)
            editor = os.getenv('EDITOR','gedit')
            x = os.spawnlp(os.P_WAIT,editor,editor,recordfile)
            records = read_header_records(recordfile)
    else:
        write_header_records(files, recordfile)
        editor = os.getenv('EDITOR','gedit')
        x = os.spawnlp(os.P_WAIT,editor,editor,recordfile)
        records = read_header_records(recordfile)
        
    files = [record.get('logger_file') for record in records]
    comp_nos = [record.get('compno') for record in records]
    file_dict = dict(zip(comp_nos, files))
    
    labelled_files = [file_dict.pop(label.split(' ')[-1]) for label in labels_use]
    print 'found {} exceptional files'.format(len(labelled_files))
    files = file_dict.values()
        
    # Choose colours for exceptional flights
    colors = []
    cmap = plt.get_cmap('gist_rainbow')
    for i, pilot in enumerate(labels_use):
        colors.append(cmap(float(i)/(len(labels_use)-1)))
    
    # Choose colours for other flights
    fixed_colors = ['DarkRed'] * len(files)
            

    # Read traces from files
    flights = []
    for lgfile in labelled_files + files:
        flight = GliderFlight(lgfile, skip_declaration=True)
        flights.append(flight)
        
    # Plot traces
    ax1 = plotmap(flights[::-1], zoom=zoom, tracecolors=fixed_colors+colors[::-1], aspectratio=11.7/8.3)

    # Plot turnpoints if given
    if turnpointlist is not None:
        dummy = Task(turnpointlist)
        source_crs = ccrs.PlateCarree()
        target_crs = ax1.projection
        for name, coord in dummy.latlon.iteritems():
            ax1.annotate(name, xy=target_crs.transform_point(coord[0], coord[1], source_crs), 
                         bbox=dict(boxstyle="round", fc="w"), fontsize='small')
    
    # Any extra stuff
    if plot_extras is not None:
        plot_extras()

    # Add title and legend       
    ax1.set_title(title, fontsize='large')
    
    lines = [mlines.Line2D([], [], color=color, label=label) for (color, label) in zip(colors, labels_use)]
    leg = ax1.legend(handles=lines, loc=4, fontsize='small')
    for legobj in leg.legendHandles:
        legobj.set_linewidth(2.0)

    # Save to file
    fig=plt.gcf()
    fig.tight_layout()
    fig.set_size_inches((11.7, 8.3))
    plt.savefig(imagefile + '.pdf')
    plt.savefig(imagefile + '.png')
    
    plt.close()


def plot_range_rings():
    ax = plt.gca()
    color='Gray'
    for distance in range(10, 181, 10):
        ax.add_patch(mpatches.Circle(DSGC_OS, distance * 1000, edgecolor=color, facecolor='none', transform=OS_CRS))
        ax.annotate('%skm' % distance, 
                    xy=ax.projection.transform_point(DSGC_OS[0]+distance*820 + 1500, DSGC_OS[1]+distance*570, OS_CRS), 
                    color=color,
                    fontsize='small',
                    ha='left', va='top')
        
        
def plot_compass():
    ax = plt.gca()
    dsgc = ax.projection.transform_point(-3.27, 50.85, SOURCE_CRS)
    color = 'Gray'
    ax.axhline(dsgc[1], color=color)
    ax.axvline(dsgc[0], color=color)


title_dict = {1: 'Northward Challenge',
              2: 'Visit our Friends',
              3: 'Around the Compass',
              4: 'Westward Ho!',             
              5: 'Running Round in Circles',
              6: 'Anyone for Tennis?',
              7: 'Around and About'}
                  

turnpoint_dict = {1: ['CLS', 'WEG', 'TAU', 'WLS', 'FRO', 'DEV', 'AST', 'ADF',
                      'BID'],
                  4: ['TRW', 'BOM', 'LAU', 'HOL', 'EAG', 'BAM', 'WEG', 'TAU',
                      'BWE', 'GLA', 'FRO', 'CPW', 'TET', 'CME', 'TEW', 'GTW',
                      'TES', 'WHI'],
                  5: None,
                  7: ['CER', 'BEA', 'AXM', 'HHL', 'CUL', 'MUD', 'EGG', 'BPL',
                      'MLN', 'DKY', 'DUL', 'BAM']}

plot_extra_dict = {3: plot_compass,
                   5: plot_range_rings}


exceptional_flights = {1: ['Justin Wills 1', 'Mike Armstrong JVA', 'Trevor Stuart 621', 'Matt Williamson 611',
                           'Nick Gaunt A98', 'Ron Johns 711', 'Phil & Diana King DD2'],
                       2: ['Jon Wand T1', 'Trevor Stuart 621', 'Justin Wills 1', 'Team Eagle BBB',
                           'Bob Bromwich 94', 'Jordan Richards L18', 'Ron Johns 711', ],
                       3: ['Trevor Stuart 621', 'Mike Armstrong JVA', 'Liam Vile DG1', 'Nick Gaunt A98',
                           'Nick Harrison JDD', 'Justin Wills 1', 'Ron Johns 711', 'Simon Minson SM'],
                       4: ['Rod Witter LEC', 'Jon Wand T1', 'Trevor Stuart 621', 'Justin Wills 1',
                           'Jordan Richards L18', 'Mike Armstrong JVA'],
                       5: ['Justin Wills 1', 'Bob Bromwich 94', 'Trevor Stuart 621', 'Geddes Chalmers Z5',
                           'Mike Armstrong JVA', 'Andrew Cluskey J5T'],
                       6: ['Trevor Stuart 621', 'Justin Wills 1', 'Bob Bromwich 94', 'Mike Armstrong JVA',
                           'Jordan Richards L18', 'Team Eagle BBB', 'Pete Bennett DRE'],
                       7: ['Mike Armstrong JVA', 'Alan Price AP', 'Rod Witter LEC', 'Ron Johns 711',
                           'Phil & Diana King DD2', 'Jon Wand T1']}


if __name__ == '__main__':
    for day in range(1, 8):  
        if day == 7:
            zoom = 11
        if day in [3, 4, 6, 7]:
            zoom = 10
        else:
            zoom = 9
        
        if day == 1:
            plotonmap(os.path.join('enterprise', 'day{}'.format(day)), 
                    'Day {}: {}'.format(day, title_dict.get(day, '')),
                    os.path.join('enterprise_maps/stamen', 'day{}'.format(day)),
                    turnpointlist=turnpoint_dict.get(day),
                    plot_extras=plot_extra_dict.get(day),
                    labels_use=exceptional_flights.get(day),
                    zoom=zoom)
            
