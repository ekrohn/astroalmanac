#!/usr/bin/python3
import argparse
import datetime
import ephem
import math
import sys

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.path import Path

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
parser.add_argument ('--elevation', '--elev', '-L', type=float, default=1700,
                   help='site elevation in meters')
parser.add_argument ('--tzoffset', '--tz', '-Z', type=int, default=-7,
                   help='the offset of the local timezone in hours after UTC')
parser.add_argument ('--start-date', '--start', '-s', type=str, default=None,
                   help='start date for the chart')
parser.add_argument ('--end-date', '--end', '-e', type=str, default=None,
                   help='end date for the chart')
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
obcolor["mercury"]  = '#b04000'
obcolor["venus"]    = '#2000d0'
obcolor["mars"]     = '#f00000'
obcolor["jupiter"]  = '#6000a0'
obcolor["saturn"]   = '#a0a040'
obcolor["uranus"]   = '#0020d0'
obcolor["star"]   = '#808080'

if args.verbose:
    print ("start_date = %s, end_date = %s" % (
        ephem.Date(start_date), ephem.Date(end_date), ))

here.date = start_date
days = range (days_in_chart)
times = {}

def draw_time_lines (start_hour, end_hour, days, axes, times):
    for h in range (start_hour, end_hour+1):
        # Full hour dotted line.
        y = []
        for d in days:
            sun_rise = times["sun"]["rise"][d]
            sun_set  = times["sun"]["set"][d]
            y.append (math.nan if (h > sun_rise or h < sun_set) else h)
        axes.plot (days, y, color='white', marker='.', markerfacecolor='brown', lw=1)
        axes.text (0, h, "%d " % ((h+12)%24,), va="center", ha="right")
        axes.text (days[-1], h, " %d" % ((h+12)%24,), va="center", ha="left")
        # Half hour dotted line.
        y = []
        m = h + 0.5
        for d in days:
            sun_rise = times["sun"]["rise"][d]
            sun_set  = times["sun"]["set"][d]
            y.append (math.nan if (m > sun_rise or m < sun_set) else m)
        axes.plot (days, y, color='white', marker='.', markerfacecolor='brown', lw=1)
    # Solid line for midnight localtime (non-DST).
    axes.plot (days, [12 for d in days], color='black')
    return

def draw_date_lines (start_hour, end_hour, days, axes, times, start_date, where):
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
        axes.plot (x, y, color='white', marker='.', markerfacecolor='brown', lw=1)
        where.date = start_date
        day = ephem.localtime (ephem.Date(here.date + d))
        axes.text (d, sun_set, "%d" % (day.day,), va="top", ha="center")
        if day.day <= 7:
            axes.text (d, sun_set-1/6., day.strftime("%B"), va="top", ha="left")
            axes.text (d, sun_rise+1/6., day.strftime("%B"), va="bottom", ha="left")
        day = ephem.localtime (ephem.Date(here.date + d +end_hour*ephem.hour))
        axes.text (d, sun_rise, "%d" % (day.day,), va="bottom", ha="center")
        #axes.text (days[-1], h, " %d" % ((h+12)%24,), va="center", ha="left")
    # Solid line for midnight localtime (non-DST).
    axes.plot (days, [12 for i in days], color='black')
    return

def hours_after (t2, t1):
    return 24.0 * (t2-t1)

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
    print (name)
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

def label_object (time, label, obcolor):
    '''
    Attempt to label an object's time plot.
    Most objects will have discontiguous segments. Try to place the label
    near the middle of each segment.
    '''
    first_non_nan = None
    for i in days:
        # print ("%3d  %5.3f" % (i, time[i]))
        if math.isnan (time[i]):
            if first_non_nan == None:
                # print ("nan to nan %d" % (i,))
                pass
            else:
                # Compute the label position
                mid = int ((i + first_non_nan) / 2)
                # print ("non-nan to nan, label %s at %d,%5.3f" % (label, mid, time[mid]))
                axes.text (mid, time[mid], label, va="bottom", ha="center", color=obcolor)
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
        # print ("last is non-nan, label %s at %d,%5.3f" % (label, mid, time[mid]))
        axes.text (mid, time[mid], label, va="bottom", ha="center", color=obcolor)
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

rise_set_transit (ephem.Moon(), "moon", here, times, do_transit=False)
rise_set_transit (ephem.Mercury(), "mercury", here, times, do_transit=False)
rise_set_transit (ephem.Venus(), "venus", here, times, do_transit=False)
rise_set_transit (ephem.Mars(), "mars", here, times)
rise_set_transit (ephem.Jupiter(), "jupiter", here, times)
rise_set_transit (ephem.Saturn(), "saturn", here, times)
rise_set_transit (ephem.Uranus(), "uranus", here, times)
rise_set_transit (ephem.star("Sirius"), "sirius", here, times)
rise_set_transit (ephem.star("Regulus"), "regulus", here, times)
#rise_set_transit (ephem.star("Polaris"), "polaris", here, times, do_rise=False, do_set=False)

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

draw_time_lines (start_plot_hour, end_plot_hour, days, axes, times)
draw_date_lines (start_plot_hour, end_plot_hour, days, axes, times, start_date, here)

axes.plot (days, times["sun"]["set"], color=obcolor['sun'])
axes.plot (days, times["sun"]["rise"], color=obcolor['sun'])
axes.text (mid_chart, times["sun"]["set"][mid_chart], "sun set", va="top", ha="left", color=obcolor['sun'])
axes.text (mid_chart, times["sun"]["rise"][mid_chart], "sun rise", va="bottom", ha="left", color=obcolor['sun'])
axes.plot (days, times["civil"]["set"], color=obcolor['civil'])
axes.plot (days, times["civil"]["rise"], color=obcolor['civil'])
axes.plot (days, times["nautical"]["set"], color=obcolor['nautical'])
axes.plot (days, times["nautical"]["rise"], color=obcolor['nautical'])
axes.plot (days, times["astro"]["set"], color=obcolor['astro'])
axes.plot (days, times["astro"]["rise"], color=obcolor['astro'])
axes.text (mid_chart, times["astro"]["set"][mid_chart], "twilight", va="top", ha="right", color=obcolor['astro'])
axes.text (mid_chart, times["astro"]["rise"][mid_chart], "twilight", va="bottom", ha="right", color=obcolor['astro'])

# When sun is down, plot moon rise time or set time with the phase of the
# moon at that moment.
#plot_moon_phases (axes, days, here, times)

#axes.plot (days, times["moon"]["rise"], 'y')
#axes.plot (days, times["moon"]["set"], 'g')

axes.plot (days, times["mercury"]["rise"], color=obcolor['mercury'])
axes.plot (days, times["mercury"]["set"], color=obcolor['mercury'])
label_object (times['mercury']['rise'], 'mercury rise', obcolor['mercury'])
label_object (times['mercury']['set'], 'mercury set', obcolor['mercury'])

axes.plot (days, times["venus"]["rise"], color=obcolor['venus'])
axes.plot (days, times["venus"]["set"], color=obcolor['venus'])
label_object (times['venus']['rise'], 'venus rise', obcolor['venus'])
label_object (times['venus']['set'], 'venus set', obcolor['venus'])

axes.plot (days, times["mars"]["rise"], color=obcolor['mars'])
axes.plot (days, times["mars"]["transit"], color=obcolor['mars'])
axes.plot (days, times["mars"]["set"], color=obcolor['mars'])
label_object (times['mars']['rise'], 'mars rise', obcolor['mars'])
label_object (times['mars']['transit'], 'mars transit', obcolor['mars'])
label_object (times['mars']['set'], 'mars set', obcolor['mars'])

axes.plot (days, times["jupiter"]["rise"], color=obcolor['jupiter'])
axes.plot (days, times["jupiter"]["transit"], color=obcolor['jupiter'])
axes.plot (days, times["jupiter"]["set"], color=obcolor['jupiter'])
label_object (times['jupiter']['rise'], 'jupiter rise', obcolor['jupiter'])
label_object (times['jupiter']['transit'], 'jupiter transit', obcolor['jupiter'])
label_object (times['jupiter']['set'], 'jupiter set', obcolor['jupiter'])

axes.plot (days, times["saturn"]["rise"], color=obcolor['saturn'])
axes.plot (days, times["saturn"]["transit"], color=obcolor['saturn'])
axes.plot (days, times["saturn"]["set"], color=obcolor['saturn'])
label_object (times['saturn']['rise'], 'saturn rise', obcolor['saturn'])
label_object (times['saturn']['transit'], 'saturn transit', obcolor['saturn'])
label_object (times['saturn']['set'], 'saturn set', obcolor['saturn'])

axes.plot (days, times["uranus"]["rise"], color=obcolor['uranus'])
axes.plot (days, times["uranus"]["transit"], color=obcolor['uranus'])
axes.plot (days, times["uranus"]["set"], color=obcolor['uranus'])
label_object (times['uranus']['rise'], 'uranus rise', obcolor['uranus'])
label_object (times['uranus']['transit'], 'uranus transit', obcolor['uranus'])
label_object (times['uranus']['set'], 'uranus set', obcolor['uranus'])

axes.plot (days, times["sirius"]["transit"], color=obcolor['star'])
label_object (times['sirius']['transit'], 'sirius transit', obcolor['star'])

axes.plot (days, times["regulus"]["transit"], color=obcolor['star'])
label_object (times['regulus']['transit'], 'regulus transit', obcolor['star'])

#axes.plot (days, times["polaris"]["antitransit"], 'k')
#axes.plot (days, times["polaris"]["transit"], 'k')

plt.show ()
