"""An in-memory stand-in for the PostGIS database.

Creates an in-memory SQLite engine holding the same tables ``app.py`` reads
(``sc_counties``, ``sc_county_law_info``, ``target_data``) pre-seeded with
small sample data. The real SQL in ``src/queries.py`` runs unchanged against
it, so tests exercise genuine query logic instead of mocking ``read_sql``.

PostGIS is not available on SQLite, so geometries are stored as hex WKB text;
``gpd.read_postgis`` parses those back into shapely geometries.
"""

import sqlalchemy as sa
from shapely.geometry import Polygon
from shapely import wkb

# ---------------------------------------------------------------------------
# Sample data (a handful of counties is plenty for testing)
# ---------------------------------------------------------------------------

# county_name -> population + a simple square "geometry" per county
_COUNTIES = {
    "York": 288_519,
    "Greenville": 554_886,
    "Charleston": 413_888,
}

# (county_name, fips) crosswalk mirroring sc_county_law_info
_LAW_INFO = [
    ("York", "45091"),
    ("Greenville", "45045"),
    ("Charleston", "45019"),
]

# (incident_id, offense_type, location, fips) incident rows for target_data.
# Deliberately unbalanced so ORDER BY / LIMIT behaviour is observable.
_INCIDENTS = [
    # York (45091): Larceny dominates, then Simple Assault, then Burglary
    (1, "Larceny", "Store", "45091"),
    (2, "Larceny", "Residence", "45091"),
    (3, "Larceny", "Parking Lot", "45091"),
    (4, "Simple Assault", "Residence", "45091"),
    (5, "Simple Assault", "Street", "45091"),
    (6, "Burglary", "Residence", "45091"),
    # Greenville (45045): Motor Vehicle Theft leads
    (7, "Motor Vehicle Theft", "Parking Lot", "45045"),
    (8, "Motor Vehicle Theft", "Highway", "45045"),
    (9, "Larceny", "Store", "45045"),
    # Charleston (45019)
    (10, "Robbery", "Street", "45019"),
    (11, "Robbery", "Convenience Store", "45019"),
    (12, "Larceny", "Store", "45019"),
]


def _square_wkb(name):
    """A tiny non-overlapping square polygon per county, as hex WKB."""
    x = 0.0 + 2 * _COUNTIES_INDEX[name]
    poly = Polygon([(x, 0), (x + 1, 0), (x + 1, 1), (x, 1)])
    return wkb.dumps(poly, hex=True)


_COUNTIES_INDEX = {name: i for i, name in enumerate(_COUNTIES)}


class MockDatabase:
    """In-memory SQLite engine shaped like the app's Postgres schema."""

    def __init__(self):
        self.engine = sa.create_engine("sqlite://")
        self._create_tables()
        self._seed()

    def _create_tables(self):
        with self.engine.begin() as conn:
            conn.execute(sa.text(
                "CREATE TABLE sc_counties ("
                "  county_name TEXT PRIMARY KEY,"
                "  pop INTEGER,"
                "  geometry TEXT"  # hex WKB (stand-in for PostGIS geometry)
                ")"))
            conn.execute(sa.text(
                "CREATE TABLE sc_county_law_info ("
                "  county_name TEXT,"
                "  fips TEXT PRIMARY KEY"
                ")"))
            conn.execute(sa.text(
                "CREATE TABLE target_data ("
                "  incident_id INTEGER,"
                "  offense_type TEXT,"
                "  location TEXT,"
                "  fips TEXT"
                ")"))

    def _seed(self):
        with self.engine.begin() as conn:
            for name, pop in _COUNTIES.items():
                conn.execute(
                    sa.text("INSERT INTO sc_counties VALUES (:n, :p, :g)"),
                    {"n": name, "p": pop, "g": _square_wkb(name)},
                )
            for name, fips in _LAW_INFO:
                conn.execute(
                    sa.text("INSERT INTO sc_county_law_info VALUES (:n, :f)"),
                    {"n": name, "f": fips},
                )
            conn.execute(sa.text(
                "INSERT INTO target_data (incident_id, offense_type, location, fips) "
                "VALUES (:i, :o, :l, :f)"), [
                {"i": i, "o": o, "l": l, "f": f} for i, o, l, f in _INCIDENTS
            ])

    def connect(self):
        return self.engine.connect()

    def dispose(self):
        self.engine.dispose()
