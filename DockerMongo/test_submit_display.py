import sys

import arrow
import mongomock

sys.argv = [sys.argv[0]]
import flask_brevets
import acp_times

START = "2017-01-01"
START_ISO = arrow.get("2017-01-01 00:00", "YYYY-MM-DD HH:mm").isoformat()


def setup():
    flask_brevets.collection = mongomock.MongoClient().db.controls
    flask_brevets.app.testing = True


def submit(controls, brevet=200):
    client = flask_brevets.app.test_client()
    return client.post("/_submit", json={
        "brevet_dist_km": brevet,
        "begin_date": START,
        "begin_time": "00:00",
        "controls": controls
    })


def display():
    client = flask_brevets.app.test_client()
    return client.get("/display")


def test_submit_stores_controls():
    setup()
    resp = submit([{"km": 175, "location": "Halfway"}, {"km": 60}])
    assert resp.status_code == 200
    assert resp.get_json()["result"]["count"] == 2
    docs = list(flask_brevets.collection.find().sort("km"))
    assert [doc["km"] for doc in docs] == [60, 175]
    assert docs[1]["location"] == "Halfway"
    assert docs[1]["open"] == acp_times.open_time(175, 200, START_ISO)
    assert docs[1]["close"] == acp_times.close_time(175, 200, START_ISO)


def test_submit_empty():
    setup()
    resp = submit([])
    assert resp.status_code == 400
    assert resp.get_json()["result"]["error"] == "No controle times to submit"
    assert flask_brevets.collection.count_documents({}) == 0


def test_submit_bad_distance():
    setup()
    assert submit([{"km": -5}]).status_code == 400
    assert submit([{"km": 300}]).status_code == 400
    assert submit([{"km": "abc"}]).status_code == 400
    assert submit([{"km": 50}, {"km": 50}]).status_code == 400
    assert flask_brevets.collection.count_documents({}) == 0


def test_submit_bad_brevet():
    setup()
    assert submit([{"km": 50}], brevet=250).status_code == 400


def test_submit_replaces_previous():
    setup()
    submit([{"km": 100}, {"km": 150}])
    submit([{"km": 200}])
    docs = list(flask_brevets.collection.find())
    assert [doc["km"] for doc in docs] == [200]


def test_display_empty():
    setup()
    resp = display()
    assert resp.status_code == 200
    assert b"No controle times in the database" in resp.data


def test_display_after_submit():
    setup()
    submit([{"km": 205, "location": "Finish"}])
    resp = display()
    assert resp.status_code == 200
    page = resp.data.decode()
    assert "205.0" in page
    assert "Finish" in page
    assert "Sun 1/1 5:53" in page
    assert "Sun 1/1 13:30" in page
