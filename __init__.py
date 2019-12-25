from mycroft import MycroftSkill, intent_file_handler

from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json

import WazeRouteCalculator

class TravelTime(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    @intent_file_handler('time.travel.intent')
    def handle_time_travel(self, message):
        destination_string = message.data.get('destination')
        if not destination_string:
            return None

        # WazeRouteCalculator is not good at reverse geocoding
        # So we ask OpenStreetMap Nomatim first
        url = "https://nominatim.openstreetmap.org/search?{}".format(urlencode({'q': destination_string, 'format': 'json', 'limit': 1}))
        with urlopen(url) as data:
            json_data = data.read().decode('utf-8')
            parsed_data = json.loads(json_data)[0]
            destination = "{},{}".format(parsed_data["lat"], parsed_data["lon"])

        from_string = message.data.get('from')
        if not from_string:
            from_string = self.location_pretty
            current_location = self.location["coordinate"]
            from_ = "{},{}".format(current_location["latitude"], current_location["longitude"])

        route = WazeRouteCalculator.WazeRouteCalculator(from_, destination)
        route_info = route.calc_route_info()

        self.speak_dialog('time.travel', {'time': "{:.0f}".format(route_info[0]), 'distance': "{:.0f}".format(route_info[1]), 'from': from_string, 'destination': destination_string})


def create_skill():
    return TravelTime()

