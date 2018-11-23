"""Classes and functions for plotting glider traces."""

import datetime
import math
import os.path
from itertools import islice

import shapely.geometry as sgeom
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.gridspec as gridspec
import matplotlib.patches as mpatches
import cartopy.crs as ccrs
from cartopy.io.img_tiles import MapboxTiles, OSM, GoogleTiles

from mapbox import mapboxkey

TURNPOINT_FILE = 'bga_tp_2015.txt'
METRETOFOOT = 3.28
SOURCE_CRS = ccrs.PlateCarree()
GEOM_CRS = ccrs.OSGB()

HEADER_KEYS = ['pilot', 'type', 'reg', 'compno', 'date']
HEADER_FLAGS = ['HFPLT', 'HFGTY', 'HFGID', 'HFCID',  'HFDTE']


class Trace(object):
    '''
    Class to hold glider trace (B record) info.  Attribute of GliderTrace.
    Initialised empty and then populated as file is read.
    '''
    def __init__(self):
        self.times = []
        self.alt = []
        self.gpsalt = []
        self.latlon = sgeom.LineString()

    def addtomap(self, ax, color='black'):
        lon, lat = zip(*self.latlon.coords)
        plt.plot(lon, lat, transform=SOURCE_CRS, color=color)

    def os_points(self):
        """
        Get eastings and northings as numpy arrays.
        """
        lon, lat = np.array(self.latlon).T
        return GEOM_CRS.transform_points(SOURCE_CRS, lon, lat)[:, :-1]

    def distance(self):
        """
        Return the actual distance flown in km.
        """
        os_shape = sgeom.LineString(self.os_points())
        return os_shape.length / 1000.0

    def check_points(self):
        eastings, northings = self.os_points().T
        distances = np.sqrt((eastings[1:] - eastings[:-1]) ** 2 +
                            (northings[1:] - northings[:-1]) ** 2)
        if distances.max() > 2000:
            raise UserWarning("Probable data error.  Over 2km in one step.")


class Task(object):
    '''
    Class to hold task's turnpoint trigraphs and lat/lon info.  Will also
    contain FAI sector or barrel shapes for each turnpoint when I get around to
    coding them.
    '''
    def __init__(self, turnpoint_list=[], latlon_list=None, barrels=False):
        self.names = turnpoint_list
        self.latlon = {}

        if len(self.names):
            if latlon_list:
                if len(self.names) != len(latlon_list):
                    raise UserWarning('Turnpoint name and location lists '
                                      'inconsistent lengths')
                else:
                    for (name, coord) in zip(turnpoint_list, latlon_list):
                        self.latlon.update({name: coord})
            else:
                # Coordinates not supplied.  Read from BGA turnpoint file
                self.latlon = locate_turnpoints(self.names)

        self.geoms = []
        # List of barrel or FAI sector shapely polygons.  NOT multipolygon as
        # need order.

        if barrels:
            for name in self.names:
                lon, lat = self.latlon[name]
                self.geoms.append(sgeom.Point(GEOM_CRS.transform_point(
                    lon, lat, SOURCE_CRS)).buffer(500))
        else:
            pass

    def addtomap(self, ax, color=None):
        if len(self.names):
            if len(self.geoms):
                ax.add_geometries(self.geoms, GEOM_CRS, facecolor='w',
                                  alpha=0.5)
                for lon, lat in self.latlon.values():
                    circle = mpatches.Circle(
                        GEOM_CRS.transform_point(lon, lat, SOURCE_CRS), 50,
                        edgecolor='MidnightBlue', facecolor='none',
                        transform=GEOM_CRS)
                    ax.add_patch(circle)

            task_lon, task_lat = zip(*[self.latlon.get(tp) for
                                     tp in self.names])
            ax.plot(task_lon, task_lat, transform=SOURCE_CRS, color=color)
            for name, coord in self.latlon.iteritems():
                ax.annotate(
                    name,
                    xy=ax.projection.transform_point(coord[0], coord[1],
                                                     SOURCE_CRS),
                    textcoords='offset points', xytext=(5, 5),
                    bbox=dict(boxstyle="round", fc="w", alpha=0.7))


def header_dict(line):
    '''Convert a header line from an IGC logger file into a dictionary entry'''
    headkey_dict = dict(zip(HEADER_FLAGS, HEADER_KEYS))
    headkey = headkey_dict.get(line[0:5])
    if not headkey:
        return {}
    elif headkey == 'date':
        year = 2000 + int(line[9:11])
        if year > datetime.date.today().year:
            year = year-100
        month = int(line[7:9])
        day = int(line[5:7])
        return {headkey: datetime.date(year, month, day)}
    else:
        tup = line.split(':')
        if len(tup) != 2:
            raise UserWarning("Invalid key=value data: %s" % line)
        headval = tup[1].strip()
        if len(headval) > 0:
            return {headkey: headval}
        else:
            return{}


def read_headers(ifp):
    '''
    Read header fields from an open IGC logger file, and store information in a
    dictionary
    '''
    headers = {}
    while True:
        line = ifp.readline()
        if line.startswith('H'):
            headers.update(header_dict(line))
            head_last = ifp.tell()
        elif len(headers) == 0:
            pass
        else:
            ifp.seek(head_last)
            if headers.get('reg'):
                headers.setdefault('compno', headers['reg'][-3:])
            return headers


def write_header_records(logger_filelist, record_file, append=False):
    '''
    Read the headers from a list of IGC files and write them into a text file
    in csv format.
    '''
    if os.path.isfile(record_file) and not append:
        while True:
            decide = raw_input(record_file+' exists.  Overwrite? (y/n)')
            if decide == 'n':
                return
            elif decide == 'y':
                break

    if append:
        f = open(record_file, 'a')
    else:
        f = open(record_file, 'w')
    for logfile in logger_filelist:
        headers = read_headers(open(logfile))
        if headers.get('pilot'):
            pilot_str = headers['pilot'].replace('.', ' ').replace('_', ' ')
            headers['pilot'] = pilot_str
            if headers['pilot'].isupper() or headers['pilot'].islower():
                headers['pilot'] = headers['pilot'].title()
        record = [logfile]
        for head in HEADER_KEYS:
            record.append(str(headers.get(head, '')))
        f.write(', '.join(record)+'\n')
    f.close()


def read_header_records(record_file):
    '''Read header records from csv file and store in list of dictionaries'''
    record_header_keys = ['logger_file']+HEADER_KEYS
    records = []
    with open(record_file) as ifp:
        for line in ifp:
            records.append(dict(zip(record_header_keys, line.split(', '))))
    return records


class GliderFlight(object):
    '''
    Class to hold information about a glider flight: a trace, a (possibly
    empty) task, and pilot/glider/date info in the header.  Initialised with an
    IGC logger file.
    '''
    def __init__(self, filename, barrels=False, skip_declaration=False):
        self.trace = Trace()
        lat = []
        lon = []
        tp_names = []
        tp_lat = []
        tp_lon = []
        declared = False

        def fixtofloat(fixstring):
            if fixstring[-1] in ['N', 'E']:
                return float(fixstring[0:-6])+float(fixstring[-6:-1])/60000.
            elif fixstring[-1] in ['S', 'W']:
                return -(float(fixstring[0:-6])+float(fixstring[-6:-1])/60000.)
            else:
                raise UserWarning("Invalid latlon format")

        with open(filename) as ifp:
            self.headers = read_headers(ifp)
            for line in ifp:
                if line.startswith('B'):
                    self.trace.times.append(datetime.time(
                        int(line[1:3]), int(line[3:5]), int(line[5:7])))
                    lat.append(fixtofloat(line[7:15]))
                    lon.append(fixtofloat(line[15:24]))
                    self.trace.alt.append(float(line[25:30])*METRETOFOOT)
                    self.trace.gpsalt.append(float(line[30:35])*METRETOFOOT)
                elif line.startswith('C') and skip_declaration is False:
                    if not declared:
                        declared = True
                        # First C line is declaration date. Skip.
                    else:
                        tp_lat.append(fixtofloat(line[1:9]))
                        tp_lon.append(fixtofloat(line[9:18]))
                        tp_names.append(line[18:-2])

        self.trace.latlon = sgeom.LineString(zip(lon, lat))
        if declared:
            self.task = Task(tp_names[1:-1], zip(tp_lon[1:-1], tp_lat[1:-1]))
        else:
            self.task = Task()


def locate_turnpoints(turnpoint_list):
    '''
    Takes a list of BGA turnpoint trigraphs and returns a dictionary
    with the longitude and latitude of each turnpoint in list
    '''
    latlon = {}
    ntp = len(set(turnpoint_list))
    with open(TURNPOINT_FILE) as ifp:
        while True:
            record = list(islice(ifp, 13))
            if not record:
                break
            if record[1].strip() in turnpoint_list:
                lat = float(record[9][0:2]) + float(record[9][3:9])/60.
                if record[9][21] == 'S':
                    lat = -lat
                lon = float(record[9][11:14]) + float(record[9][15:21])/60.
                if record[9][21] == 'W':
                    lon = -lon
                latlon.update({record[1].strip(): (lon, lat)})
                if len(latlon) == ntp:
                    break
    return latlon


def plotmap(flights, zoom=10, tracecolors=['black'], taskcolors=['Crimson'],
            aspectratio=None, terrain=False):
    '''
    Plot one or more GliderFlight instances on a map.

    Arguments:
    * flights: A (list of) GliderFlight instance(s)
    * zoom: detail level of map image.  10 is recommended for large tasks, 12
        for local (within gliding range of airfield) tasks
    * tracecolors: A (list of) colour(s) for the trace lines
    * taskcolors: A (list of) colour(s) for the task lines
    * aspectratio: float specifying aspect ration of map as width/height
    * terrain: boolean.  False to plot OpenStreetMap map, True to plot Google
      terrain
    '''

    if type(flights) is not list:
        flights = [flights]

    if type(taskcolors) is not list:
        taskcolors = [taskcolors]
    while len(taskcolors) < len(flights):
        taskcolors += taskcolors

    if type(tracecolors) is not list:
        tracecolors = [tracecolors]
    while len(tracecolors) < len(flights):
        tracecolors += tracecolors

    if terrain:
        tiler = GoogleTiles(style='terrain')
    else:
        tiler = MapboxTiles(mapboxkey, 'mapbox.pirates')

    target_crs = tiler.crs
    ax = plt.axes(projection=target_crs)

    for flight, color1, color2 in zip(flights, taskcolors, tracecolors):
        if type(flight) is str:
            flight = GliderFlight(flight)
        if color1:
            flight.task.addtomap(ax, color1)
        flight.trace.addtomap(ax, color2)

    (minx, maxx, miny, maxy) = ax.get_extent(target_crs)

    # Add buffer space.
    buffer_size = 0.05
    minx = minx - (maxx - minx) * buffer_size
    maxx = maxx + (maxx - minx) * buffer_size
    miny = miny - (maxy - miny) * buffer_size
    maxy = maxy + (maxy - miny) * buffer_size

    if aspectratio:

        oldratio = (maxx-minx)/(maxy-miny)
        if oldratio < aspectratio:
            newmaxx = (aspectratio * (maxy-miny) + maxx + minx) / 2.0
            newminx = (maxx + minx - aspectratio * (maxy - miny)) / 2.0
            newmaxy = maxy
            newminy = miny
        else:
            newmaxy = ((maxx-minx)/aspectratio + maxy + miny) / 2.0
            newminy = (maxy + miny - (maxx - minx) / aspectratio) / 2.0
            newmaxx = maxx
            newminx = minx
        ax.set_extent([newminx, newmaxx, newminy, newmaxy], crs=target_crs)

    ax.add_image(tiler, zoom, alpha=0.8, interpolation='spline36')
    print ax.get_images()

    if isinstance(tiler, MapboxTiles):
        ax.annotate('$\copyright$ Mapbox, $\copyright$ OpenStreetMap',
                    xy=(2, 2), xycoords='axes points', fontsize='small')

    return ax


def plotaltitude(flights, ax, colors=['black']):
    '''
    Plot a graph of altitude against time from one or more GliderFlight
    instances.
    '''
    if type(flights) is not list:
        flights = [flights]

    if type(colors) is not list:
        colors = [colors]
    while len(colors) < len(flights):
        colors += colors

    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    for flight, color in zip(flights, colors):
        x = [datetime.datetime.combine(flight.headers.get('date'), t) for t in
             flight.trace.times]
        if max(flight.trace.alt):
            print 'plotting real'
            ax.plot(x, flight.trace.alt, color=color)
        else:
            print 'plotting gps'
            ax.plot(x, flight.trace.gpsalt, color=color)
    ax.grid(True)
    ax.set_ylabel('Altitude (feet)')
    ax.set_xlabel('Time (GMT)')


def plotflight(filename, pilotname=None, gliderid=None, tp_list=None,
               barrels=False, altitude=True, **kwargs):
    '''
    Plot a glider flight on a map

    Arguments:
    * filename: string pointing to an IGC logger file
    * pilotname: pilot's name for plot title
    * gliderid: glider registration or competition number for plot title
    * tp_list: list of BGA trigraph strings to define a task
    * barrels: bolean indicating True for half km barrel turnpoints, False for
      FAI sectors
    * altitude: if True, plot a graph of altitude vs time below the map

    * any kwargs for plotmap
    '''
    flight = GliderFlight(filename)
    if not pilotname:
        pilotname = flight.headers.get('pilot')
    if not gliderid:
        gliderid = flight.headers.get('compno')
    if not gliderid:
        gliderid = flight.headers.get('reg')

    if tp_list is not None:
        flight.task = Task(tp_list, barrels=barrels)

    print flight.task.geoms

    fig = plt.figure()
    ax1 = plotmap(flight, **kwargs)
    ax1.set_title(pilotname+' '+gliderid+' '+str(flight.headers.get('date')))

    if altitude:
        (minx, maxx, miny, maxy) = ax1.get_extent()
        if (maxx-minx) >= (maxy-miny):
            gs = gridspec.GridSpec(3, 1)
        else:
            gs = gridspec.GridSpec(1, 3)
        ax1.set_position(gs[0:2].get_position(fig))
        ax1.set_subplotspec(gs[0:2])
        ax2 = plt.subplot(gs[2])
        plotaltitude(flight, ax2)

    fig.tight_layout()

    plt.show()

if __name__ == '__main__':
    # Test with sample flight
    plotflight('ruth_silver_height_flight.IGC', 'Ruth Comer', 'KHA',
               ['NHL', 'CUL', 'HHL', 'CLS', 'NHL'], barrels=True, zoom=12)
