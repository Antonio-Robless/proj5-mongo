"""
Nose tests for acp_times.py

Expected values are the worked examples on
https://rusa.org/pages/acp-brevet-control-times-calculator
cross-checked against https://rusa.org/octime_acp.html.

Run from the brevets directory with:  nosetests
"""
import arrow
import nose
from nose.tools import assert_raises

from acp_times import open_time, close_time

START = arrow.get("2017-01-01T00:00:00+00:00")
START_ISO = START.isoformat()


def after(hours, minutes):
    """ISO string for START shifted by hours:minutes."""
    return START.shift(hours=hours, minutes=minutes).isoformat()


def check(km, brevet, open_hm, close_hm):
    assert open_time(km, brevet, START_ISO) == after(*open_hm), \
        "open {}km/{}km".format(km, brevet)
    assert close_time(km, brevet, START_ISO) == after(*close_hm), \
        "close {}km/{}km".format(km, brevet)


def test_start_control():
    """Control at 0 km opens at start, closes one hour later."""
    check(0, 200, (0, 0), (1, 0))


def test_first_segment_200():
    """RUSA example 1: 200 km brevet, controls inside 0-200 km band."""
    check(60, 200, (1, 46), (4, 0))
    check(120, 200, (3, 32), (8, 0))
    check(175, 200, (5, 9), (11, 40))


def test_early_control_rule():
    """Controls within 60 km close at 20 km/h + 1 h, not 15 km/h."""
    check(20, 200, (0, 35), (2, 0))
    check(50, 300, (1, 28), (3, 30))


def test_final_control_fixed_close():
    """Finish closes at the fixed limit, not distance / 15 km/h."""
    check(200, 200, (5, 53), (13, 30))
    check(300, 300, (9, 0), (20, 0))
    check(400, 400, (12, 8), (27, 0))
    check(600, 600, (18, 48), (40, 0))
    check(1000, 1000, (33, 5), (75, 0))


def test_control_past_nominal_distance():
    """Controls up to 20% past the nominal distance are timed
    as if they were exactly at the nominal distance."""
    check(205, 200, (5, 53), (13, 30))
    check(240, 200, (5, 53), (13, 30))
    check(609, 600, (18, 48), (40, 0))


def test_multiple_segments_600():
    """RUSA example 2: 600 km brevet, speeds change at 200 and 400 km."""
    check(350, 600, (10, 34), (23, 20))
    check(550, 600, (17, 8), (36, 40))


def test_multiple_segments_1000():
    """RUSA example 3: 890 km on a 1000 km brevet uses the
    11.428 km/h minimum speed in the 600-1000 km band."""
    check(890, 1000, (29, 9), (65, 23))


def test_preserves_timezone():
    """Results stay in the brevet start's time zone."""
    start = "2017-01-01T07:00:00-08:00"
    assert open_time(100, 200, start) == "2017-01-01T09:56:00-08:00"
    assert close_time(100, 200, start) == "2017-01-01T13:40:00-08:00"


def test_invalid_input():
    assert_raises(ValueError, open_time, -5, 200, START_ISO)
    assert_raises(ValueError, close_time, 100, 250, START_ISO)


if __name__ == "__main__":
    nose.main()
