#!/usr/bin/python3
import argparse
import datetime
import ephem
import math
import sys
import time

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.path import Path

process_start_time_wall = time.perf_counter()
process_start_time_cpu = time.process_time()

Command = sys.argv[0]
oneday = 1
here = ephem.Observer ()

# Determine which calendar year to use by default.
default_year = ephem.localtime (ephem.now()).year
if ephem.localtime (here.date).month >= 9:
    default_year += 1

parser = argparse.ArgumentParser (description='Generate a graphical astronomical ephemeris')
parser.add_argument ('--latitude', '--lat', '-N', type=str, default='39.75',
                   help='site latitude degrees north')
parser.add_argument ('--longitude', '--lon', '-E', type=str, default='-105',
                   help='site longitude degrees east')
parser.add_argument ('--elevation', '--elev', '-L', type=float, default=1582,
                   help='site elevation in meters')
parser.add_argument ('--tzoffset', '--tz', '-Z', type=int, default=-7,
                   help='the offset of the local timezone in hours after UTC')
parser.add_argument ('--start-date', '--start', '-s', type=str, default=None,
        help='start date for the chart. Date can be any string decoded by ephem.Date, e.g., -s 2018 or -s 2018-01. Default: now.')
parser.add_argument ('--end-date', '--end', '-e', type=str, default=None,
        help='end date for the chart. Default: one year after START_DATE.')
parser.add_argument ('--output-file', '--output', '-o', type=str, default=None,
        help='PDF output file. Default: displays chart in matplotlib\'s viewer.')
parser.add_argument ('--verbose', '-v', action='count',
                   help='verbose')
args = parser.parse_args ()

here.lon, here.lat, here.elev = args.longitude, args.latitude, args.elevation

# Normalize date to noon localtime.
def normalize_to_noon (t, tzoffset):
    '''
    Normalize to noon localtime.
    t as ephem.Date, tzoffset hours after UTC as int.
    '''
    # t.tuple() gives a pure tuple (Y, M, D, H, m, s.ss)
    # print ("t", type(t), t)
    utc_time = t.tuple ()
    localnoon = (utc_time[0], utc_time[1], utc_time[2], 12 - tzoffset, 0, 0)
    return ephem.Date (localnoon)

def determine_start_and_end_dates (args):
    start_time = end_time = ephem.now()
    if args.start_date == None:
        start_time = ephem.now()
    else:
        start_time = ephem.Date(args.start_date)
    start_time = normalize_to_noon (start_time, args.tzoffset)
    if args.end_date == None:
        # Default end_time is one year after start_time.
        utc_time = start_time.tuple ()
        end_time = ephem.Date ((utc_time[0]+1, utc_time[1], utc_time[2], 0, 0, 0))
    else:
        end_time = ephem.Date(args.end_date)
    end_time = normalize_to_noon (end_time, args.tzoffset)
    return (start_time, end_time)

start_date, end_date = determine_start_and_end_dates (args)

print ("start date: %s" % (start_date,))
print ("end date: %s" % (end_date,))

days_in_chart = int (end_date - start_date + 0.5)
mid_chart = int (days_in_chart / 2)  # only used for labelling

if args.verbose:
    print ("start %s, end %s, %s, %s  %3.0fm" % (start_date, end_date,
        args.longitude, args.latitude, args.elevation))

# Color code different objects' text and curve.
obcolor = {}
obcolor["sun"]      = '#b0b000'
obcolor["civil"]    = '#808000'
obcolor["nautical"] = '#404000'
obcolor["astro"]    = '#202000'
obcolor["Mercury"]  = '#b04000'
obcolor["Venus"]    = '#2000d0'
obcolor["Mars"]     = '#f00000'
obcolor["Jupiter"]  = '#6000a0'
obcolor["Saturn"]   = '#a0a040'
obcolor["Uranus"]   = '#20c020'
obcolor["Neptune"]  = '#00a010'
obcolor["star"]     = '#808080'
obcolor["fullgrid"] = '#505050'
obcolor["halfgrid"] = '#808080'
obcolor["default"]  = '#808080'

obfontsize = {}
obfontsize["month"]  = 7
obfontsize["day"]    = 6
obfontsize["hour"]   = 5
obfontsize["object"] = 4
obfontsize["sun"]    = 3
obfontsize["default"] = 4

obwidth = {}
obwidth["default"] = 1
obwidth["sun"]    = 2

if args.verbose:
    print ("start_date = %s, end_date = %s" % (
        ephem.Date(start_date), ephem.Date(end_date), ))

here.date = start_date
days = range (days_in_chart)
times = {}

def text_rotation (day, time, previous_day, previous_time):
    '''Day is the x-axis, time is the y-axis.
    Figure out how to rotate text to match the slope of the curve.
    Return rotation in degrees. '''
    if previous_day == None or previous_time == None:
        return 0
    if day == None or time == None:
        return 0
    slope = (time - previous_time) / (day - previous_day)
    # The slope here is odd - one hour in the y-axis is about the same size on
    # the plot as 17 days on the x-axis. So scale the slope accordingly.
    # On a one year plot *17 works well.
    # On a 6 month plot *8 works well.
    # On a 3 month plot *4 works well.
    # On a 1 month plot *1.5 works well.
    slope *= days_in_chart * 17.0 / 365.0
    degree = math.degrees (math.atan (slope))
    # print ("text rotation %3.2f deg, (%3.2f - %3.2f) / (%3.2f - %3.2f)" % ( degree, time, previous_time, day, previous_day))
    return degree

def draw_time_lines (start_hour, end_hour, days, axes, times):
    for h in range (start_hour, end_hour+1):
        # Full hour dotted line. One dot per day.
        y = []
        for d in days:
            sun_rise = times["sun"]["rise"][d]
            sun_set  = times["sun"]["set"][d]
            y.append (math.nan if (h > sun_rise or h < sun_set) else h)
        axes.plot (days, y,
                color=obcolor['fullgrid'], linewidth=0.0,
                marker='+', markerfacecolor=obcolor['fullgrid'], markersize=0.1)
        # Label the hours
        axes.text (0, h, "%02d" % ((h+12)%24,),
                va="center", ha="right", rotation=90, fontsize=obfontsize['day'])
        axes.text (days[-1]+1, h, "%02d" % ((h+12)%24,),
                va="center", ha="left", rotation=90, fontsize=obfontsize['day'])
        # Half hour dotted line. One dot per day.
        y = []
        m = h + 0.5
        for d in days:
            sun_rise = times["sun"]["rise"][d]
            sun_set  = times["sun"]["set"][d]
            y.append (math.nan if (m > sun_rise or m < sun_set) else m)
        axes.plot (days, y,
                color=obcolor['fullgrid'], linewidth=0.0,
                marker='+', markerfacecolor=obcolor['fullgrid'], markersize=0.1)
    # Solid line for midnight localtime (non-DST).
    axes.plot (days, [12 for d in days], color='black', linewidth=0.5)
    return

def draw_date_lines (start_hour, end_hour, days, axes, times, start_date, where):
    previous_d = None
    previous_sun_rise = None
    previous_sun_set = None
    # Dots every 7 days
    for d in days:
        if (d % 7 != 0):
            continue
        sun_rise = times["sun"]["rise"][d]
        sun_set  = times["sun"]["set"][d]
        x = [d for i in range (12 * (end_hour-start_hour))]
        y = []
        # Fill in 5 minute intervals. 12 of those per hour.
        for t in range (start_hour*12, end_hour*12):
            h = t / 12. # back to hours
            y.append (math.nan if (h >= sun_rise or h <= sun_set) else h)
        axes.plot (x, y,
                color=obcolor['fullgrid'], linewidth=0.01,
                marker='+', markerfacecolor='red', markersize=0.1)
        where.date = start_date
        day = ephem.localtime (ephem.Date(here.date + d))
        # Label bottom sunset curve with day of month.
        axes.text (d, sun_set, "%d " % (day.day,),
                va="top", ha="center", rotation=90,
                fontsize=obfontsize['day'])
        if day.day >= 12 and day.day <= 18:
            # Label sunset and sunrise curves with month names.
            axes.text (d, sun_set-3/6., day.strftime("%B"),
                    va="top", ha="center",
                    rotation=text_rotation(d,sun_set, previous_d, previous_sun_set),
                    fontsize=obfontsize['month'])
            axes.text (d, sun_rise+3/6., day.strftime("%B"),
                    va="bottom", ha="center",
                    rotation=text_rotation(d,sun_rise, previous_d, previous_sun_rise),
                    fontsize=obfontsize['month'])
        day = ephem.localtime (ephem.Date(here.date + d +end_hour*ephem.hour))
        # Label top sunrise curve with day of month.
        axes.text (d, sun_rise, " %d" % (day.day,),
                va="bottom", ha="center", rotation=90,
                fontsize=obfontsize['day'])
        #axes.text (days[-1], h, " %d" % ((h+12)%24,), va="center", ha="left")
        previous_d = d
        previous_sun_rise = sun_rise
        previous_sun_set = sun_set
    return

def hours_after (t2, t1):
    return 24.0 * (t2-t1)

def show_elapsed_time():
    print ("elapsed %3.2f total, %3.2f cpu" % (
        (time.perf_counter() - process_start_time_wall),
        (time.process_time() - process_start_time_cpu),
        ))

def rise_set_transit (object, name, where, times, horizon = '0',
        do_rise = True, do_set = True, do_transit = True,
        do_anti_transit = False, debug = False):
    '''Compute, and save in times dictionary, the rising, setting, and transit 
    times of object.
    horizon defaults to zero (note that it is a string), but can be changed for
    computing civil, nautical, and astronomical twilight times.
    debug lists the rise, set, and transit times.
    do_transit flags whether to compute the transit time.
    do_anti_transit flags whether to comput the anti-transit time.'''
    if not name in times:
        times[name] = {}
    if do_set    : times[name]["set"] = []
    if do_rise   : times[name]["rise"] = []
    if do_transit: times[name]["transit"] = []
    if do_anti_transit: times[name]["antitransit"] = []
    where.date = start_date
    where.horizon = horizon
    if debug:
        show = "%-3s" % ("day", )
        if do_set: show += "  %7s" % ("set",)
        if do_rise: show += "  %7s" % ("rise",)
        if do_transit: show += "  %7s" % ("transit",)
        if do_anti_transit: show += "  %7s" % ("antitransit",)
        print (show)
    for i in days:
        if name != "sun":
            sun_rise = times["sun"]["rise"][i]
            sun_set  = times["sun"]["set"][i]
        if name == "moon" and debug:
            print ("%s %s" % (where.next_rising(object), where.next_setting(object)))
        if do_set:
            h = (hours_after (where.next_setting(object), where.date))
            if h > 24 :
                h = math.nan
            # If object sets while sun is up, do not plot it.
            if name != "sun" and (h > sun_rise or h < sun_set):
                h = math.nan
            times[name]["set"].append (h)
        if do_rise:
            h = (hours_after (where.next_rising(object), where.date))
            if h > 24 :
                h = math.nan
            # If object rises while sun is up, do not plot it.
            if name != "sun" and (h > sun_rise or h < sun_set):
                h = math.nan
            times[name]["rise"].append (h)
        if do_transit:
            h = (hours_after (where.next_transit(object), where.date))
            if h > 24 :
                h = math.nan
            # If object transits while sun is up, do not plot it.
            if name != "sun" and (h > sun_rise or h < sun_set):
                h = math.nan
            times[name]["transit"].append (h)
        if do_anti_transit:
            h = (hours_after (where.next_antitransit(object), where.date))
            if h > 24 :
                h = math.nan
            # If object anti-transits while sun is up, do not plot it.
            if name != "sun" and (h > sun_rise or h < sun_set):
                h = math.nan
            times[name]["antitransit"].append (h)
        if debug:
            show = "%-3d" % (i, )
            if do_set: show += "  %7.4f" % (times[name]["set"][i],)
            if do_rise: show += "  %7.4f" % (times[name]["rise"][i],)
            if do_transit: show += "  %7.4f" % (times[name]["transit"][i],)
            if do_anti_transit: show += "  %7.4f" % (times[name]["antitransit"][i],)
            print (show)
        where.date = where.date + oneday
    print (name, end=' ')
    show_elapsed_time()

def choose_arg (kwname, kwargs, objname, globalargs):
    if kwname in kwargs:
        value = kwargs[kwname]
    elif objname in globalargs:
        value = globalargs[objname]
    else:
        value = globalargs["default"]
    return value

def rotated_label (label, x1, y1, x0, y0, va, color):
    # print (label)
    rotation = text_rotation (x1,y1, x0,y0)
    # Matplotlib has odd ideas about where to place rotated text
    # with respect to the curve when va="bottom" and ha="center".
    # So use va="center" and tweak x and y to put the label where 
    # we want it.
    radians = math.radians (rotation)
    if va == "top":
        align_delta_multiplier = -1
    else:   # bottom va
        align_delta_multiplier = 1
    x = x1 - math.sin (radians) * 3 * align_delta_multiplier # x units in days
    y = y1 + math.cos (radians) * 0.1 * align_delta_multiplier # y units in hours
    axes.text (x, y, label,
            va="center", ha="center",
            color=color,
            rotation=rotation,
            fontsize=obfontsize['object'])
    return

def plot_object_event (times, obj, event, **kwargs):
    '''
    Plot a curve for an object event (e.g., Mercury rise).
    Also label the object event's time plot.
    Most event plots will have discontiguous segments. Try to place the label
    near the middle of each segment.
    '''
    color = choose_arg ("color", kwargs, obj, obcolor)
    linewidth = choose_arg ("linewidth", kwargs, obj, obwidth)
    # print (obj, event, color, linewidth)
    axes.plot (days, times[obj][event],
            color=color, linewidth=linewidth)
    if "label" in kwargs and kwargs["label"] == None:
        return # no label wanted
    # Now figure out where to put the label(s).
    if not "va" in kwargs:
        kwargs["va"] = "center"
    if not "label" in kwargs:
        kwargs["label"] = "%s %s" % (obj, event)
    first_non_nan = None
    time = times[obj][event]
    for i in days:
        # print ("%3d  %5.3f" % (i, time[i]))
        if math.isnan (time[i]):
            if first_non_nan == None:
                # print ("nan to nan %d" % (i,))
                pass
            else:
                # Compute the label position
                mid = int ((i + first_non_nan) / 2)
                # print ("non-nan to nan, label %s at %d,%5.3f" % (kwargs['label'], mid, time[mid]))
                # TODO: the mid-1 might not be valid
                rotated_label (kwargs['label'],
                        mid, time[mid], mid-1, time[mid-1],
                        kwargs['va'], color)
                first_non_nan = None
        else: # non-nan
            if first_non_nan == None:
                first_non_nan = i
                # print ("nan to non-nan %d" % (i,))
            else:
                # print ("non-nan to non-nan %d %d %5.3f" % (i, first_non_nan, time[i]))
                pass
        pass
    if first_non_nan == None:
        # Ignore
        pass
    else:
        # Compute the label position
        mid = int ((days[-1] + first_non_nan) / 2)
        # print ("last is non-nan, label %s at %d,%5.3f" % (kwargs['label'], mid, time[mid]))
        rotated_label (kwargs['label'],
                mid, time[mid], mid-1, time[mid-1],
                kwargs['va'], color)
    return

def plot_moon_phases (axes, days, where, times):
    '''
    Place a marker of moon's phase at the point of moon rise or moon set,
    whichever happens after sunset on a day and before sunrise.
    '''
    where.date = start_date
    for i in days:
        sun_rise = times["sun"]["rise"][i]
        sun_set  = times["sun"]["set"][i]
        moon_rise = times["moon"]["rise"][i]
        moon_set  = times["moon"]["set"][i]
        prev_new_moon = ephem.previous_new_moon (where.date + sun_set/24)
        next_new_moon = ephem.next_new_moon (where.date + sun_set/24)
        lunation = next_new_moon - prev_new_moon
        moon_time = math.nan
        if math.isnan (moon_rise):
            if math.isnan (moon_set):
                continue
            else:
                moon_time = moon_set
        else:
            moon_time = moon_rise
        age = where.date + moon_time/24 - prev_new_moon
        if args.verbose:
            print ("%3d %5.2f %5.2f %5.2f %5.2f %4.1f" % (i, sun_set, sun_rise, moon_rise, moon_set, age))
        draw_moon_phase (i, moon_time, age, lunation)
        where.date = where.date + oneday
    return

# Add (p1x,p1y) and (p2x,p2y)
def add_coord (p1, p2):
    return ((p1[0] + p2[0], p1[1] + p2[1]))

def draw_moon_phase (x, y, age, lunation):
    '''
    Draw a diagram of the moon's phase centered on (x,y).
    The diagram should not be overly large.
    Make the diagram double diameter around new, full, and quarter.
    '''
    # http://www.charlespetzold.com/blog/2012/12/Bezier-Circles-and-Bezier-Ellipses.html
    # describes how to get bezier curves to describe circular arcs.
    # We need the control point length L to be
    # L = 4 * tan (a/4) / 3 * r
    # For half circle, that simplifies to
    # L = 4/3 * r
    # For half ellipse, we multiply L by the semi-minor axis rather than the semi-major axis.
    # We draw one half circle for the illuminated moon limb.
    # We draw one half ellipse for the terminator.
    # As a special case, for new moon, draw a full empty circle.
    # The moon's terminator is always a circle, however, viewed from the
    # earth it will be a circle viewed usually off perpendicular.
    # That gives us an ellipse. At new moon and full moon (0π and 1π) the
    # terminators are half circles, one unlit and the other fully lit.
    # At first quarter and last quarter (0.5π and 1.5π), the terminator reduces 
    # to a straight line (circle seen edge on).
    # So use cosine to generate the semi-minor axis of the terminator ellipse.
    fraction = age / lunation
    cos = math.cos (fraction * 2 * math.pi)
    control_L = 4. / 3 * 0.5 * 0.20
    moon_upper_limb = (x-1.0, y)
    moon_lower_limb = (x+1.0, y)
    bezier_verts = []
    bezier_codes = []
    limb_direction = 1 if age <= lunation/2 else -1
    moon_color = 'yellow'
    if (fraction < 0.03 or fraction > 0.97):
        moon_color = 'white'
        # This is a hack. I want an empty full circle around new moon, not a 
        # half circle.
        cos = -cos
    # Upper limb (left on our chart)
    bezier_verts.append (moon_upper_limb)
    bezier_codes.append (Path.MOVETO)
    # First control point
    bezier_verts.append (add_coord (moon_upper_limb, (0, control_L * limb_direction)))
    bezier_codes.append (Path.CURVE4)
    # Second control point
    bezier_verts.append (add_coord (moon_lower_limb, (0, control_L * limb_direction)))
    bezier_codes.append (Path.CURVE4)
    # Lower limb (right on our chart)
    bezier_verts.append (moon_lower_limb)
    bezier_codes.append (Path.CURVE4)
    # Now turn around and draw the terminator.
    # First control point
    bezier_verts.append (add_coord (moon_lower_limb, (0, control_L * cos * limb_direction)))
    bezier_codes.append (Path.CURVE4)
    # Second control point
    bezier_verts.append (add_coord (moon_upper_limb, (0, control_L * cos * limb_direction)))
    bezier_codes.append (Path.CURVE4)
    # Lower limb (right on our chart)
    bezier_verts.append (moon_upper_limb)
    bezier_codes.append (Path.CURVE4)
    # Close the curve
    bezier_verts.append (moon_upper_limb)
    bezier_codes.append (Path.CLOSEPOLY)
    moon = Path (bezier_verts, bezier_codes)
    moon_patch = matplotlib.patches.PathPatch (moon, facecolor=moon_color, lw=1)
    axes.text (x, y, "%.0f" % (age,), va="center", ha="center")
    axes.add_patch (moon_patch)
    return

# Record the times for lots of interesting events.
# Do the sun first since other objects' display depends on the sun being below
# horizon.
rise_set_transit (ephem.Sun(), "sun", here, times, do_transit=False)
rise_set_transit (ephem.Sun(), "civil", here, times, horizon = '-6', do_transit=False)
rise_set_transit (ephem.Sun(), "nautical", here, times, horizon = '-12', do_transit=False)
rise_set_transit (ephem.Sun(), "astro", here, times, horizon = '-18', do_transit=False)

# These times should depend on extrema of sunrise and sunset times.
# Start plot y axis this many hours after noon localtime (no DST adjustment)
start_plot_hour = math.floor (min(times["sun"]["set"]))
# End plot y axis this many hours after noon localtime (no DST adjustment)
end_plot_hour = math.ceil (max(times["sun"]["rise"]))
print ("start_plot_hour = %s, end_plot_hour = %s" % (start_plot_hour, end_plot_hour))

fig = plt.figure()
axes = fig.add_axes([0.0, 0.0, 1.0, 1.0]) # left, bottom, width, height  range 0-1
axes.set_xlabel("Date")
axes.set_ylabel("hours after noon")

# Normally we'd want xlim from 0-days_in_chart and ylim from start_plot_hour-
# end_plot_hour. But we want some extra to fit labels.
extra_border_fraction = 0.05
extra_border_x = days_in_chart * extra_border_fraction
extra_border_y = (end_plot_hour - start_plot_hour) * extra_border_fraction
axes.set_xlim([0-extra_border_x,days_in_chart+extra_border_x])
axes.set_ylim([start_plot_hour-extra_border_y,end_plot_hour+extra_border_y])

# Put the date range on the chart.
date_label_x = mid_chart if float(args.latitude) > 0 else 0
axes.text (date_label_x, start_plot_hour-extra_border_y,
        "%s - %s UTC%+d" % (
            ephem.localtime (start_date).strftime ("%F"),
            ephem.localtime (end_date).strftime ("%F"),
            args.tzoffset),
        va="bottom", ha="center")

draw_date_lines (start_plot_hour, end_plot_hour, days, axes, times, start_date, here)
draw_time_lines (start_plot_hour, end_plot_hour, days, axes, times)

rise_set_transit (ephem.Moon(), "moon", here, times, do_transit=False)
rise_set_transit (ephem.Mercury(), "Mercury", here, times, do_transit=False)
rise_set_transit (ephem.Venus(), "Venus", here, times, do_transit=False)
rise_set_transit (ephem.Mars(), "Mars", here, times)
rise_set_transit (ephem.Jupiter(), "Jupiter", here, times)
rise_set_transit (ephem.Saturn(), "Saturn", here, times)
rise_set_transit (ephem.Uranus(), "Uranus", here, times)
rise_set_transit (ephem.Neptune(), "Neptune", here, times)

rise_set_transit (ephem.star("Antares"), "Antares", here, times)
rise_set_transit (ephem.star("Betelgeuse"), "Betelgeuse", here, times)
rise_set_transit (ephem.star("Pollux"), "Pollux", here, times)
rise_set_transit (ephem.star("Regulus"), "Regulus", here, times)
rise_set_transit (ephem.star("Sirius"), "Sirius", here, times)
#rise_set_transit (ephem.star("Polaris"), "polaris", here, times, do_rise=False, do_set=False)
 
plot_object_event (times, "sun", "set", va="top")
plot_object_event (times, "sun", "rise", va="bottom")
plot_object_event (times, "civil", "set", label=None)
plot_object_event (times, "civil", "rise", label=None)
plot_object_event (times, "nautical", "set", label=None)
plot_object_event (times, "nautical", "rise", label=None)
plot_object_event (times, "astro", "set", label="evening twilight", va="top")
plot_object_event (times, "astro", "rise", label="morning twilight", va="bottom")

# When sun is down, plot moon rise time or set time with the phase of the
# moon at that moment.
#plot_moon_phases (axes, days, here, times)

#axes.plot (days, times["moon"]["rise"], 'y')
#axes.plot (days, times["moon"]["set"], 'g')

plot_object_event (times, "Betelgeuse", "transit")
plot_object_event (times, "Pollux", "transit")
plot_object_event (times, "Regulus", "transit")
plot_object_event (times, "Sirius", "rise")
plot_object_event (times, "Sirius", "transit")

plot_object_event (times, "Neptune", "rise")
plot_object_event (times, "Neptune", "transit")
plot_object_event (times, "Neptune", "set")

plot_object_event (times, "Uranus", "rise")
plot_object_event (times, "Uranus", "transit")
plot_object_event (times, "Uranus", "set")

plot_object_event (times, "Mercury", "rise", va="top")
plot_object_event (times, "Mercury", "set")

plot_object_event (times, "Venus", "rise", va="top")
plot_object_event (times, "Venus", "set")

plot_object_event (times, "Mars", "rise")
plot_object_event (times, "Mars", "transit")
plot_object_event (times, "Mars", "set")

plot_object_event (times, "Jupiter", "rise")
plot_object_event (times, "Jupiter", "transit")
plot_object_event (times, "Jupiter", "set")

plot_object_event (times, "Saturn", "rise")
plot_object_event (times, "Saturn", "transit")
plot_object_event (times, "Saturn", "set")

#axes.plot (days, times["polaris"]["antitransit"], 'k')
#axes.plot (days, times["polaris"]["transit"], 'k')

if args.output_file != None:
    fig.savefig (args.output_file)
else:
    plt.show ()

