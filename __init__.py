from mycroft import MycroftSkill, intent_file_handler, util

from urllib.parse import urlencode
from urllib.request import urlopen, Request
import json

import WazeRouteCalculator

class TravelTime(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def _parse_location(self, location_string):
        if location_string == "home":
            if "home" in self.settings and self.settings["home"]:
                location_name = self.settings["home"]
                location = self._geocode(location_name)
            else:
                location_name = self.location_pretty
                current_location = self.location["coordinate"]
                location = "{},{}".format(self.location["coordinate"]["latitude"], self.location["coordinate"]["longitude"])

            return location_name, location

        location_name = location_string
        if location_string in self.settings and self.settings[location_string]:
            location_name = self.settings[location_string]

        location = self._geocode(location_name)

        return location_name, location

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

        destination = self._parse_location(destination_string)
        if not destination[1]:
            self.speak_dialog('time.travel.failed_finding_location', {'location': destination[0]})
            return None

        from_string = message.data.get('from')
        if from_string:
            from_ = self._parse_location(from_string)
        else:
            from_ = self._parse_location("home")

        if not from_[1]:
            self.speak_dialog('time.travel.failed_finding_location', {'location': from_[0]})
            return None

        route = WazeRouteCalculator.WazeRouteCalculator(from_[1], destination[1])
        route_info = route.calc_route_info()

        # Store if we need metric or imperial version of dialog
        dialog = "time.travel.metric"

        # Mycroft expects the time in seconds
        time = util.format.nice_duration(route_info[0] * 60, resolution=util.format.TimeResolution.MINUTES)

        # Convert to Imperial system if necessary
        distance = route_info[1]
        if self.config_core["system_unit"] == "imperial":
            dialog = "time.travel.imperial"
            distance = distance * 0.62137119

        self.speak_dialog(dialog, {'time': time, 'distance': util.format.pronounce_number(distance, places=0), 'from': from_[0], 'destination': destination[0]})


def create_skill():
    return TravelTime()

