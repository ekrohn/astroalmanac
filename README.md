# astroalmanac
astroalmanac produces a graphical astronomical almanac/ephemeris
for a given location.
The almanac includes times of: sun rise, set, and twilight;
visible planet rise, set, and transit;
and transit for certain bright stars.
No moon rise and set with phase (yet).

The start and end dates for the chart are not constrained to a full year.
However, charts of less than 3 months are not as interesting and charts
of more than one year look too cramped.
For easier printing, create one chart for the first half of the year and a
second chart for the last half of the year.

There is no adjustment for Daylight Savings Time.
I find it easiest to pick the UTC offset that is used most of the year in
my location.

The overall layout looks much like the very useful Stargazer's Almanac produced
annually by Sky & Telescope, however, astroalmanac is more low budget.
The background is white, which is easier on ink/toner.
The text labels are placed by machine rather than by intelligent human, so they
are not always placed legibly.

If you want a program that produces a graphic more like the Sky & Telescope
chart, look at one of the PySkyAlmanac forks on github.com.

# Dependencies
- python3
- pyephem
- matplotlib

# Bugs

- Throws an ephem.AlwaysUpError for locations more than about 48 degrees from
  the equator.
  This happens in the astronomical twilight calculation (sun 18 degrees below
  the horizon).

