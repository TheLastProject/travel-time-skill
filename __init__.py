from mycroft import MycroftSkill, intent_file_handler, util

from urllib.parse import urlencode
from urllib.request import urlopen
import json
import traceback

import WazeRouteCalculator


class TravelTime(MycroftSkill):
    def __init__(self):
        MycroftSkill.__init__(self)
        self.home_words = self.translate_list("home")
        self.work_words = self.translate_list("work")

    def _parse_location(self, location_string):
        location_name = self._resolve_alias(location_string)
        if location_name in self.home_words:
            # If "home" is requested and not set, grab Mycroft's location
            location = "{},{}".format(
                self.location["coordinate"]["latitude"],
                self.location["coordinate"]["longitude"]
            )
        elif location_name in self.work_words:
            # If "work" is requested and not set, give up
            location = None
        else:
            # Otherwise, resolve
            location = self._geocode(location_name)

        return location_name, location

    def _resolve_alias(self, location_string):
        if location_string in self.home_words:
            lookup = "home"
        elif location_string in self.work_words:
            lookup = "work"
        else:
            lookup = location_string

        if lookup in self.settings and self.settings[lookup]:
            return self.settings[lookup]

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

    def _speak_failed_calculating_route(self, from_, destination):
        self.speak_dialog(
            'time.travel.failed_calculating_route',
            {
                'from': from_,
                'destination': destination
            }
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

        # If can't find destination, give up
        destination = self._parse_location(destination_string)
        if destination[1] is None:
            self._speak_not_found(destination[0])
            return None

        # Default to home
        from_string = message.data.get('from')
        if from_string is None:
            from_string = self.home_words[0]

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
        try:
            route_info = route.calc_route_info()
        except WazeRouteCalculator.WRCError as e:
            self._speak_failed_calculating_route(from_[0], destination[0])
            traceback.print_exc()
            return None

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
