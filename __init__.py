from mycroft import MycroftSkill, intent_file_handler

from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json

import WazeRouteCalculator

class TravelTime(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def _geocode(self, location):
        # WazeRouteCalculator is not good at geocoding
        # So we ask OpenStreetMap Nomatim
        url = "https://nominatim.openstreetmap.org/search?{}".format(urlencode({'q': location, 'format': 'json', 'limit': 1}))
        with urlopen(url) as data:
            json_data = data.read().decode('utf-8')
            parsed_data = json.loads(json_data)
            try:
                return "{},{}".format(parsed_data[0]["lat"], parsed_data[0]["lon"])
            except (IndexError, KeyError):
                return None


    @intent_file_handler('time.travel.intent')
    def handle_time_travel(self, message):
        destination_string = message.data.get('destination')
        if not destination_string:
            return None

        specifier = message.data.get('specifier')
        if specifier:
            destination_string = "{}, {}".format(destination_string, specifier)

        # WazeRouteCalculator is not good at reverse geocoding
        # So we ask OpenStreetMap Nomatim first
        destination = self._geocode(destination_string)
        if not destination:
            self.speak_dialog('time.travel.failed_finding_location', {'location': destination_string})
            return None

        from_string = message.data.get('from')
        if from_string:
            from_ = self._geocode(from_string)
            if not from_:
                self.speak_dialog('time.travel.failed_finding_location', {'location': destination_string})
                return None
        else:
            from_string = self.location_pretty
            current_location = self.location["coordinate"]
            from_ = "{},{}".format(current_location["latitude"], current_location["longitude"])

        route = WazeRouteCalculator.WazeRouteCalculator(from_, destination)
        route_info = route.calc_route_info()

        self.speak_dialog('time.travel', {'time': "{:.0f}".format(route_info[0]), 'distance': "{:.0f}".format(route_info[1]), 'from': from_string, 'destination': destination_string})


def create_skill():
    return TravelTime()

