# Project 5: Brevet time calculator with Ajax and MongoDB

**Author:** Antonio Robles — bryan77robles@gmail.com
**Repo:** <https://github.com/Antonio-Robless/proj5-mongo>

The ACP brevet control times calculator from project 4, extended to save
control times to MongoDB and display them on a separate page. The app and
the database run as two containers with Docker Compose.

## Running

```bash
cd DockerMongo
docker compose up --build
# open http://localhost:5000
```

Stop with `docker compose down`.

## Using the calculator

1. Pick the brevet distance (200, 300, 400, 600 or 1000 km).
2. Set the start date and time.
3. Type each control's distance in miles **or** kilometers. The other unit,
   the open time and the close time fill in automatically (AJAX).
4. Click **Submit** to save the controls to the database. A message under
   the table shows how many were saved, or what went wrong.
5. Click **Display** to open a new page listing the saved controls.

Each Submit replaces what was saved before, so the database always holds
one brevet: the last one submitted. Open and close times are recalculated
on the server from the distances, so what is stored always follows the
rules below.

### Error cases

Submit is rejected, and nothing in the database changes, when:

- there are no controls with times in the table
- a distance is not a number or is negative
- a control is more than 20% past the brevet distance
- two controls have the same distance
- the brevet distance is not 200, 300, 400, 600 or 1000
- the start date or time is invalid
- the database cannot be reached

Display shows "No controle times in the database" when nothing has been
submitted yet, and an error message if the database cannot be reached.

## Control time rules

A control's **open time** is the earliest a rider may arrive (based on the
maximum speed). Its **close time** is the latest (based on the minimum speed).

### Speed table

| Control location (km) | Minimum speed (km/h) | Maximum speed (km/h) |
|-----------------------|----------------------|----------------------|
| 0 – 200               | 15                   | 34                   |
| 200 – 400             | 15                   | 32                   |
| 400 – 600             | 15                   | 30                   |
| 600 – 1000            | 11.428               | 28                   |
| 1000 – 1300           | 13.333               | 26                   |

### Calculation

1. **Split by band.** Speeds apply per band, not per whole distance. For a
   control at 350 km: the first 200 km use the 0–200 speed, the next 150 km
   use the 200–400 speed.
   - Open: 200/34 + 150/32 = 10.570 h → **10h34**
   - Close: 200/15 + 150/15 = 23.333 h → **23h20**
2. **Round** the total to the nearest minute (half a minute rounds up).
3. **Add** the result to the start time.

### Special cases

- **Start control (0 km):** opens at the start, closes 1 hour later.
- **Controls within the first 60 km:** close time = distance / 20 km/h + 1 h.
  This gives early riders enough time. Example: 20 km closes at 2h00, not
  1h20. (This follows the current RUSA calculator. Older calculators used
  15 km/h for these controls too.)
- **Finish control:** closes at a fixed overall limit, not by the speed table:

  | Brevet | 200 km | 300 km | 400 km | 600 km | 1000 km |
  |--------|--------|--------|--------|--------|---------|
  | Limit  | 13h30  | 20h00  | 27h00  | 40h00  | 75h00   |

- **Controls past the brevet distance:** a route may run up to 20% longer than
  its nominal distance. Any control past the nominal distance gets the same
  times as one exactly at it. Example: a 205 km finish on a 200 km brevet
  opens at 5h53 and closes at 13h30. A control more than 20% past is
  rejected.

### Worked examples (start 00:00)

| Brevet | Control | Open  | Close |
|--------|---------|-------|-------|
| 200    | 60      | 1h46  | 4h00  |
| 200    | 175     | 5h09  | 11h40 |
| 200    | 205     | 5h53  | 13h30 |
| 600    | 550     | 17h08 | 36h40 |
| 1000   | 890     | 29h09 | 65h23 |

References: <https://rusa.org/pages/acp-brevet-control-times-calculator>,
<https://rusa.org/pages/rulesForRiders>.

## Developer notes

### Layout

```
DockerMongo/
  flask_brevets.py         Flask app: pages, /_calc_times, /_submit, /display
  acp_times.py             open_time / close_time logic
  templates/calc.html      calculator page, AJAX, Submit/Display buttons
  templates/display.html   saved controls page
  test_acp_times.py        tests for the time calculations
  test_submit_display.py   tests for the Submit and Display buttons
  config.py                reads credentials.ini / command line
  credentials.ini          author, repo, port, secret key
  Dockerfile
  docker-compose.yml       web (Flask) + db (mongo:7)
```

### API

`GET /_calc_times?km=<float>&brevet_dist_km=<int>&begin_date=YYYY-MM-DD&begin_time=HH:mm`
returns `{"result": {"open": iso, "close": iso, "error": null, "note": ...}}`.

`POST /_submit` with JSON

```json
{"brevet_dist_km": 200, "begin_date": "2017-01-01", "begin_time": "00:00",
 "controls": [{"km": 60, "location": "Optional"}, {"km": 205}]}
```

returns `{"result": {"count": 2, "error": null}}`, or status 400/503 with
`{"result": {"error": "..."}}`.

`GET /display` renders the saved controls, sorted by distance.

### Database

Database `brevetsdb`, collection `controls`, one document per control:

```json
{"brevet_dist_km": 200, "begin": "2017-01-01T00:00:00+00:00",
 "km": 60.0, "miles": 37.3, "location": "",
 "open": "2017-01-01T01:46:00+00:00", "close": "2017-01-01T04:00:00+00:00"}
```

To look at it directly:

```bash
docker compose exec db mongosh brevetsdb --eval 'db.controls.find()'
```

### Tests

```bash
cd DockerMongo
pip install -r requirements.txt
nosetests
```

The button tests use `mongomock` in place of a real database, so they run
without Docker.
