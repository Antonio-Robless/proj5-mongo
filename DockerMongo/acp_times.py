"""
Open and close time calculations
for ACP-sanctioned brevets
following rules described at https://rusa.org/pages/acp-brevet-control-times-calculator
and https://rusa.org/pages/rulesForRiders
"""
import math

import arrow

#  Note for CIS 322 Fall 2016:
#  You MUST provide the following two functions
#  with these signatures, so that I can write
#  automated tests for grading.  You must keep
#  these signatures even if you don't use all the
#  same arguments.  Arguments are explained in the
#  javadoc comments.
#

SPEED_TABLE = [
    (0, 200, 15, 34),
    (200, 400, 15, 32),
    (400, 600, 15, 30),
    (600, 1000, 11.428, 28),
    (1000, 1300, 13.333, 26),
]

FINAL_CLOSE = {
    200: (13, 30),
    300: (20, 0),
    400: (27, 0),
    600: (40, 0),
    1000: (75, 0),
}

EARLY_LIMIT_KM = 60
EARLY_SPEED = 20


def _round_minutes(hours):
    """Convert fractional hours to whole minutes, rounding half up."""
    return int(math.floor(hours * 60 + 0.5))


def _elapsed_hours(control_dist_km, speed_index):
    """Sum time over each speed segment the control distance covers.
    speed_index 0 uses minimum speed (closing), 1 maximum speed (opening)."""
    hours = 0.0
    for start, end, *speeds in SPEED_TABLE:
        if control_dist_km <= start:
            break
        segment = min(control_dist_km, end) - start
        hours += segment / speeds[speed_index]
    return hours


def _effective_distance(control_dist_km, brevet_dist_km):
    """Controls past the nominal distance are timed as if at the
    nominal distance (ACP allows the route to be up to 20% longer)."""
    if control_dist_km < 0:
        raise ValueError("Control distance cannot be negative")
    if brevet_dist_km not in FINAL_CLOSE:
        raise ValueError("Brevet distance must be one of {}".format(
            sorted(FINAL_CLOSE)))
    return min(control_dist_km, brevet_dist_km)


def open_time(control_dist_km, brevet_dist_km, brevet_start_time):
    """
    Args:
       control_dist_km:  number, the control distance in kilometers
       brevet_dist_km: number, the nominal distance of the brevet
           in kilometers, which must be one of 200, 300, 400, 600,
           or 1000 (the only official ACP brevet distances)
       brevet_start_time:  An ISO 8601 format date-time string indicating
           the official start time of the brevet
    Returns:
       An ISO 8601 format date string indicating the control open time.
       This will be in the same time zone as the brevet start time.
    """
    dist = _effective_distance(control_dist_km, brevet_dist_km)
    minutes = _round_minutes(_elapsed_hours(dist, 1))
    return arrow.get(brevet_start_time).shift(minutes=minutes).isoformat()


def close_time(control_dist_km, brevet_dist_km, brevet_start_time):
    """
    Args:
       control_dist_km:  number, the control distance in kilometers
          brevet_dist_km: number, the nominal distance of the brevet
          in kilometers, which must be one of 200, 300, 400, 600, or 1000
          (the only official ACP brevet distances)
       brevet_start_time:  An ISO 8601 format date-time string indicating
           the official start time of the brevet
    Returns:
       An ISO 8601 format date string indicating the control close time.
       This will be in the same time zone as the brevet start time.
    """
    dist = _effective_distance(control_dist_km, brevet_dist_km)
    if dist >= brevet_dist_km:
        hours, mins = FINAL_CLOSE[brevet_dist_km]
        minutes = hours * 60 + mins
    elif dist <= EARLY_LIMIT_KM:
        minutes = _round_minutes(dist / EARLY_SPEED + 1)
    else:
        minutes = _round_minutes(_elapsed_hours(dist, 0))
    return arrow.get(brevet_start_time).shift(minutes=minutes).isoformat()
