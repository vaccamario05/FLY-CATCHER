import logging
from urllib.request import urlopen
from urllib.error import URLError
import json
from time import sleep

logger = logging.getLogger(__name__)

DUMP1090DATAURL = "http://localhost:8080/data/aircraft.json"


class FlightData():
    def __init__(self, data_url=DUMP1090DATAURL, flight_log_number=0):
        self.data_url = data_url
        self._last_json = None
        self.json_data = None
        self.aircraft = []
        self.refresh()

    def refresh(self):
        try:
            req = urlopen(self.data_url)
            raw = req.read()
            self.json_data = json.loads(raw.decode('utf-8'))
            self._last_json = self.json_data
            self.aircraft = AirCraftData.parse_flightdata_json(self.json_data)
        except URLError as e:
            logger.warning("dump1090 unreachable: %s — using last known data", e)
            if self._last_json is not None:
                self.aircraft = AirCraftData.parse_flightdata_json(self._last_json)
        except (json.JSONDecodeError, KeyError) as e:
            logger.error("Malformed response from dump1090: %s", e)

    def _refresh(self):
        with open("data/aircraft.json") as data_file:
            self.json_data = json.load(data_file)
        self.aircraft = AirCraftData.parse_flightdata_json(self.json_data)


class AirCraftData():
    def __init__(self,
                 dhex,
                 squawk,
                 flight,
                 lat,
                 lon,
                 seen_pos,
                 altitude,
                 vert_rate,
                 track,
                 rssi,
                 speed,
                 messages,
                 seen,
                 mlat):

        self.hex = dhex
        self.squawk = squawk
        self.flight = flight
        self.lat = lat
        self.lon = lon
        self.seen_pos = seen_pos
        self.altitude = altitude
        self.vert_rate = vert_rate
        self.track = track
        self.rssi = rssi
        self.speed = speed
        self.messages = messages
        self.seen = seen
        self.mlat = mlat

    @staticmethod
    def parse_flightdata_json(json_data):
        aircraft_list = []
        for aircraft in json_data.get('aircraft', []):
            try:
                aircraftdata = AirCraftData(
                    aircraft.get("hex", None),
                    aircraft.get("squawk", None),
                    aircraft.get("flight", None),
                    aircraft.get("lat", None),
                    aircraft.get("lon", None),
                    aircraft.get("seen_pos", None),
                    aircraft.get("altitude", None),
                    aircraft.get("vert_rate", None),
                    aircraft.get("track", None),
                    aircraft.get("rssi", None),
                    aircraft.get("speed", None),
                    aircraft.get("messages", None),
                    aircraft.get("seen", None),
                    aircraft.get("mlat", None))
                aircraft_list.append(aircraftdata)
            except Exception as e:
                logger.warning("Skipping malformed aircraft record: %s", e)
        return aircraft_list

    def __hash__(self):
        return hash(self.hex)

    def __eq__(self, other):
        if other is None:
            return False
        return self.hex == other.hex


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    myflights = FlightData()
    while True:
        for aircraft in myflights.aircraft:
            print(aircraft.hex, aircraft.flight, aircraft.lat, aircraft.lon)
        sleep(1)
        myflights.refresh()
