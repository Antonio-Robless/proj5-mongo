"""
Replacement for RUSA ACP brevet time calculator
(see https://rusa.org/octime_acp.html)

"""

import flask
from flask import request
import arrow  # Replacement for datetime, based on moment.js
import acp_times  # Brevet time calculations
import config
from pymongo import MongoClient
from pymongo.errors import PyMongoError

import logging

###
# Globals
###
app = flask.Flask(__name__)
CONFIG = config.configuration()
app.secret_key = CONFIG.SECRET_KEY

client = MongoClient("db", 27017, serverSelectionTimeoutMS=3000)
db = client.brevetsdb
collection = db.controls

###
# Pages
###


@app.route("/")
@app.route("/index")
def index():
    app.logger.debug("Main page entry")
    return flask.render_template('calc.html')


@app.errorhandler(404)
def page_not_found(error):
    app.logger.debug("Page not found")
    flask.session['linkback'] = flask.url_for("index")
    return flask.render_template('404.html'), 404


###############
#
# AJAX request handlers
#   These return JSON, rather than rendering pages.
#
###############
@app.route("/_calc_times")
def _calc_times():
    """
    Calculates open/close times for one control, using rules
    described at https://rusa.org/pages/acp-brevet-control-times-calculator.
    URL arguments:
      km              control distance in kilometers
      brevet_dist_km  nominal brevet distance (200, 300, 400, 600, 1000)
      begin_date      start date, YYYY-MM-DD
      begin_time      start time, HH:mm
    Returns JSON {"result": {"open": iso, "close": iso, "error": msg|null}}
    """
    app.logger.debug("request.args: {}".format(request.args))
    km = request.args.get('km', None, type=float)
    brevet_dist = request.args.get('brevet_dist_km', 200, type=int)
    begin_date = request.args.get('begin_date', '2017-01-01', type=str)
    begin_time = request.args.get('begin_time', '00:00', type=str)

    if km is None:
        return flask.jsonify(result={"open": None, "close": None,
                                     "error": "Distance must be a number"})
    try:
        start = arrow.get("{} {}".format(begin_date, begin_time),
                          "YYYY-MM-DD HH:mm")
    except (arrow.parser.ParserError, ValueError):
        return flask.jsonify(result={"open": None, "close": None,
                                     "error": "Invalid start date/time"})
    if km < 0:
        error = "Distance cannot be negative"
    elif km > brevet_dist * 1.2:
        error = "Control is more than 20% past the {}km brevet".format(
            brevet_dist)
    else:
        error = None
    if error:
        return flask.jsonify(result={"open": None, "close": None,
                                     "error": error})

    try:
        open_time = acp_times.open_time(km, brevet_dist, start.isoformat())
        close_time = acp_times.close_time(km, brevet_dist, start.isoformat())
    except ValueError as err:
        return flask.jsonify(result={"open": None, "close": None,
                                     "error": str(err)})
    note = None
    if km > brevet_dist:
        note = "Past nominal distance; timed as {}km".format(brevet_dist)
    result = {"open": open_time, "close": close_time, "error": None,
              "note": note}
    return flask.jsonify(result=result)


@app.route("/_submit", methods=["POST"])
def _submit():
    data = request.get_json(silent=True)
    app.logger.debug("submit: {}".format(data))
    if not isinstance(data, dict):
        return flask.jsonify(result={"error": "Invalid request"}), 400

    controls = data.get("controls")
    if not isinstance(controls, list) or len(controls) == 0:
        return flask.jsonify(result={
            "error": "No controle times to submit"}), 400

    try:
        brevet_dist = int(data.get("brevet_dist_km"))
    except (TypeError, ValueError):
        brevet_dist = None
    if brevet_dist not in acp_times.FINAL_CLOSE:
        return flask.jsonify(result={
            "error": "Invalid brevet distance"}), 400

    try:
        start = arrow.get("{} {}".format(data.get("begin_date"),
                                         data.get("begin_time")),
                          "YYYY-MM-DD HH:mm")
    except (arrow.parser.ParserError, ValueError):
        return flask.jsonify(result={
            "error": "Invalid start date/time"}), 400

    docs = []
    seen = set()
    for control in controls:
        try:
            km = float(control.get("km"))
        except (AttributeError, TypeError, ValueError):
            return flask.jsonify(result={
                "error": "Distance must be a number"}), 400
        if km < 0:
            return flask.jsonify(result={
                "error": "Distance cannot be negative"}), 400
        if km > brevet_dist * 1.2:
            return flask.jsonify(result={
                "error": "{}km is more than 20% past the {}km brevet".format(
                    km, brevet_dist)}), 400
        if km in seen:
            return flask.jsonify(result={
                "error": "Two controls at {}km".format(km)}), 400
        seen.add(km)
        docs.append({
            "brevet_dist_km": brevet_dist,
            "begin": start.isoformat(),
            "km": km,
            "miles": round(km * 0.621371, 1),
            "location": str(control.get("location") or "").strip(),
            "open": acp_times.open_time(km, brevet_dist, start.isoformat()),
            "close": acp_times.close_time(km, brevet_dist, start.isoformat())
        })
    docs.sort(key=lambda doc: doc["km"])

    try:
        collection.delete_many({})
        collection.insert_many(docs)
    except PyMongoError as err:
        app.logger.debug("Database error: {}".format(err))
        return flask.jsonify(result={
            "error": "Could not reach the database"}), 503
    return flask.jsonify(result={"count": len(docs), "error": None})


@app.route("/display")
def display():
    app.logger.debug("Display page entry")
    try:
        controls = list(collection.find().sort("km"))
    except PyMongoError as err:
        app.logger.debug("Database error: {}".format(err))
        return flask.render_template('display.html', controls=[],
                                     error="Could not reach the database"), 503
    return flask.render_template('display.html', controls=controls,
                                 error=None)


@app.template_filter("pretty_time")
def pretty_time(iso):
    return arrow.get(iso).format("ddd M/D H:mm")


#############

app.debug = CONFIG.DEBUG
if app.debug:
    app.logger.setLevel(logging.DEBUG)

if __name__ == "__main__":
    print("Opening for global access on port {}".format(CONFIG.PORT))
    app.run(port=CONFIG.PORT, host="0.0.0.0")
