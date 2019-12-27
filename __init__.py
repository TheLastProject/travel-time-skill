from mycroft import MycroftSkill, intent_file_handler, util

from urllib.parse import urlencode
from urllib.request import urlopen
import json

import WazeRouteCalculator


class TravelTime(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)

    def _parse_location(self, location_string):
        location_name = self._resolve_alias(location_string)
        if location_name == "home":
            # If "home" is requested and not set, grab Mycroft's location
            location = "{},{}".format(
                self.location["coordinate"]["latitude"],
                self.location["coordinate"]["longitude"]
            )
        elif location_name == "work":
            # If "work" is requested and not set, give up
            location = None
        else:
            # Otherwise, resolve
            location = self._geocode(location_name)

        return location_name, location

    def _resolve_alias(self, location_string):
        if location_string is self.settings and self.settings[location_string]:
            return self.settings[location_string]

        return location_string

    def _geocode(self, location):
        # WazeRouteCalculator is not good at geocoding
        # So we ask OpenStreetMap Nomatim
        query = urlencode({'q': location, 'format': 'json', 'limit': 1})
        url = "https://nominatim.openstreetmap.org/search?{}".format(query)
        with urlopen(url) as data:
            json_data = data.read().decode('utf-8')
            parsed_data = json.loads(json_data)
            try:
                return "{},{}".format(
                    parsed_data[0]["lat"],
                    parsed_data[0]["lon"]
                )
            except (IndexError, KeyError):
                return None

    def _speak_not_found(self, location):
        self.speak_dialog(
            'time.travel.failed_finding_location',
            {'location': location}
        )

    def _speak_result(self, from_, destination, minutes, kilometers, unit):
        # Mycroft expects the time in seconds
        time = util.format.nice_duration(
            minutes * 60,
            resolution=util.format.TimeResolution.MINUTES
        )

        # Waze gives the distance in kilometers, translate if imperial
        if unit == "imperial":
            dialog = "time.travel.imperial"
            distance = kilometers * 0.62137119
        else:
            dialog = "time.travel.metric"
            distance = kilometers

        # Speak result
        self.speak_dialog(
            dialog,
            {
                'time': time,
                'distance': util.format.pronounce_number(distance, places=0),
                'from': from_,
                'destination': destination
            }
        )

    @intent_file_handler('time.travel.intent')
    def handle_time_travel(self, message):
        destination_string = message.data.get('destination')
        # If we don't have a destination, give up
        if not destination_string:
            return None

        # "How long to building in city" -> "building, city"
        specifier = message.data.get('specifier')
        if specifier:
            destination_string = "{}, {}".format(destination_string, specifier)

        # If can't find destination, give up
        destination = self._parse_location(destination_string)
        if destination[1] is None:
            self._speak_not_found(destination[0])
            return None

        # Default to home
        from_string = message.data.get('from')
        if from_string is None:
            from_string = "home"

        # If can't find from, give up
        from_ = self._parse_location(from_string)
        if from_[1] is None:
            self._speak_not_found(from_[0])
            return None

        # Calculate route
        route = WazeRouteCalculator.WazeRouteCalculator(
            from_[1],
            destination[1]
        )
        route_info = route.calc_route_info()

        # Speak result
        self._speak_result(
            from_=from_[0],
            destination=destination[0],
            minutes=route_info[0],
            kilometers=route_info[1],
            unit=self.config_core["system_unit"]
        )


def create_skill():
    return TravelTime()
