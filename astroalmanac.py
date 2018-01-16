import argparse
import datetime
import ephem
import math
import sys

import matplotlib
import matplotlib.pyplot as plt

Command = sys.argv[0]
oneday = 1
tformat = "%Y-%m-%d %H:%M:%S"
here = ephem.Observer ()

# Determine which calendar year to use.
year = ephem.localtime (ephem.now()).year
if ephem.localtime (here.date).month >= 9:
    year += 1

parser = argparse.ArgumentParser (description='Generate a one-year graphical Astronomical ephemeris')
parser.add_argument ('--latitude', '--lat', type=str, default='39.75',
                   help='site latitude degrees north')
parser.add_argument ('--longitude', '--lon', type=str, default='-105',
                   help='site longitude degrees east')
parser.add_argument ('--elevation', '--elev', type=float, default=1700,
                   help='site elevation in meters')
parser.add_argument ('--tzoffset', '--tz', type=int, default=-7,
                   help='the offset of the local timezone in hours after UTC')
parser.add_argument ('--year', '-y', type=int, default=year,
                   help='the calendar year')
parser.add_argument ('--verbose', '-v', action='count',
                   help='verbose')
args = parser.parse_args ()

days_in_year = 366
mid_year = 183  # only used for labelling
here.lon, here.lat, here.elev = args.longitude, args.latitude, args.elevation

start_date = (args.year, 1, 1, 12-args.tzoffset, 0, 0)
# TODO These times should depend somehow on latitude.
start_plot_hour = 4  # start plot this many hours after noon localtime (no DST)
end_plot_hour = 20   # end plot this many hours after noon localtime (no DST)

if args.verbose:
    print ("year %d, %s,%s  %3.0fm" % (args.year,
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

# Crude unicode glyphs for moon phases:
moon_new          = "\u1F311"
moon_wax_crescent = "\u1F312"
moon_first_quarter= "\u1F313"
moon_wax_gibbous  = "\u1F314"
moon_full         = "\u1F315"
moon_wane_gibbous = "\u1F316"
moon_last_quarter = "\u1F317"
moon_wane_crescent= "\u1F318"

# TODO adjust UTC for localtime offset; we want our almanac to report in
# localtime for everything.
# here.date.tuple() gives a pure tuple (Y, M, D, H, m, s.ss)
# ephem.localtime (here.date) gives a datetime.datetime (Y, M, D, H, m, s, d)
here_utctime = here.date.tuple()
here_localtime = ephem.localtime (here.date)
# Find difference between UTC and localtime, then adjust UTC.
delta_hours = here_utctime[3] - here_localtime.hour
# TODO Fix assumption of timezone offset being full hours.
# TODO In USA, daylight savings time runs much more than half the year.
# Maybe all times should be in DST.
if delta_hours < 12:
    start_date = (args.year, 1, 1, 12+delta_hours, 0, 0)
    end_date = (args.year+1, 1, 1, 12+delta_hours, 0, 0)
else:
    start_date = (args.year, 1, 1, 12, 0, 0)
    end_date = (args.year+1, 1, 1, 12, 0, 0)

here.date = start_date
days = range (days_in_year)
times = {}

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

# 
def label_object (time, label, obcolor):
    '''Attempt to label an object's time plot.
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
                print ("non-nan to nan, label %s at %d,%5.3f" % (label, mid, time[mid]))
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
        print ("last is non-nan, label %s at %d,%5.3f" % (label, mid, time[mid]))
        axes.text (mid, time[mid], label, va="bottom", ha="center", color=obcolor)
    return

# Do Sun first since other objects' display depends on the sun being below
# horizon.
rise_set_transit (ephem.Sun(), "sun", here, times, do_transit=False)
rise_set_transit (ephem.Sun(), "civil", here, times, horizon = '-6', do_transit=False)
rise_set_transit (ephem.Sun(), "nautical", here, times, horizon = '-12', do_transit=False)
rise_set_transit (ephem.Sun(), "astro", here, times, horizon = '-18', do_transit=False)

rise_set_transit (ephem.Moon(), "moon", here, times, do_transit=False)
rise_set_transit (ephem.Mercury(), "mercury", here, times, do_transit=False)
rise_set_transit (ephem.Venus(), "venus", here, times, do_transit=False)
rise_set_transit (ephem.Mars(), "mars", here, times)
rise_set_transit (ephem.Jupiter(), "jupiter", here, times, debug = False)
rise_set_transit (ephem.Saturn(), "saturn", here, times)
rise_set_transit (ephem.Uranus(), "uranus", here, times)
rise_set_transit (ephem.star("Sirius"), "sirius", here, times)
rise_set_transit (ephem.star("Regulus"), "regulus", here, times)
#rise_set_transit (ephem.star("Polaris"), "polaris", here, times, do_rise=False, do_set=False)

fig = plt.figure()
axes = fig.add_axes([0.0, 0.0, 1.0, 1.0]) # left, bottom, width, height  range 0-1
axes.set_xlabel("Day of Year (%d)" % (args.year,))
axes.set_ylabel("hours after noon")
axes.set_xlim([0,days_in_year])
axes.set_ylim([start_plot_hour,end_plot_hour])

axes.plot (days, times["sun"]["set"], color=obcolor['sun'])
axes.plot (days, times["sun"]["rise"], color=obcolor['sun'])
axes.text (mid_year, times["sun"]["set"][mid_year], "sun set", va="top", ha="right", color=obcolor['sun'])
axes.text (mid_year, times["sun"]["rise"][mid_year], "sun rise", va="bottom", ha="right", color=obcolor['sun'])
axes.plot (days, times["civil"]["set"], color=obcolor['civil'])
axes.plot (days, times["civil"]["rise"], color=obcolor['civil'])
axes.plot (days, times["nautical"]["set"], color=obcolor['nautical'])
axes.plot (days, times["nautical"]["rise"], color=obcolor['nautical'])
axes.plot (days, times["astro"]["set"], color=obcolor['astro'])
axes.plot (days, times["astro"]["rise"], color=obcolor['astro'])
axes.text (mid_year, times["astro"]["set"][mid_year], "twilight", va="top", ha="right", color=obcolor['astro'])
axes.text (mid_year, times["astro"]["rise"][mid_year], "twilight", va="bottom", ha="right", color=obcolor['astro'])
if float(args.latitude) > 0:
    axes.text (mid_year, start_plot_hour, str(year), va="bottom")
else:
    axes.text (0, start_plot_hour, str(year), va="bottom", ha="right")

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
