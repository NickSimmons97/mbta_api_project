#!/usr/bin/python3
import requests
import pytz
import sys
import io
import unittest
from unittest.mock import patch
from datetime import datetime

# ------------- Author: Nick Simmons ----------------------------------------


# ------------- PUBLIC CONSTANTS --------------------------------------------
MBTA_API = "https://api-v3.mbta.com/"
HEAVY_RAIL = 1
LIGHT_RAIL = 0
# ---------------------------------------------------------------------------


# ------------- GENERAL FUNCTIONS -------------------------------------------
def get_mbta_api_data_as_json(path, param):
    request = requests.get(MBTA_API + path, params=param)
    if request.status_code == 200:
        return request.json()['data']
    return None


def get_current_est_datetime():
    return datetime.now(pytz.timezone('US/Eastern'))


def get_input_from_user(type_of_selection, selection_length):
    try:
        selection_id = int(input("+ please select {} by entering ID number:".format(type_of_selection)))
        if selection_id < selection_length:
            return selection_id
        else:
            print("ERROR: your entered value must be between [{}, {}]\n".format(0, selection_length-1))
    except:
        print("ERROR: your entered value must be a number\n")
    return None


def get_light_and_heavy_rail_routes_json():
    routes_json = get_mbta_api_data_as_json("routes", {'filter[type]': '{},{}'.format(HEAVY_RAIL, LIGHT_RAIL)})
    return routes_json


def get_stops_json_for_route(route):
    stops_json = get_mbta_api_data_as_json("stops", {'filter[route]': '{}'.format(route.api_id)})
    return stops_json


def get_departures_for_stop_and_route(stop_object, route_object):
    departures_json = get_mbta_api_data_as_json("predictions", {'filter[stop]': '{}'.format(stop_object.get_api_id()),
                                                                'filter[route]': '{}'.format(route_object.get_api_id())})
    return departures_json


def select_route(routes_json):
    idx = 0
    choice = None
    print("\n")
    for route in routes_json:
        print("ID(" + str(idx) + ") " + route['attributes']['long_name'])
        print("-----------------------------")
        idx += 1
    while choice is None:
        choice = get_input_from_user("route", idx)
    return Route().populate_from_json(routes_json[choice])


def select_stop(stops_json):
    idx = 0
    choice = None
    print("\n")
    for stop in stops_json:
        print("ID(" + str(idx) + ") " + stop['attributes']['name'])
        print("-----------------------------")
        idx += 1
    while choice is None:
        choice = get_input_from_user("stop", idx)
    return Stop().populate_from_json(stops_json[choice])


def select_direction(route_object, stop_object):
    choice = None
    while choice is None:
        route_object.print_direction_options()
        choice = get_input_from_user("direction", len(route_object.direction_names))
    if not is_valid_destination(route_object.get_direction_destinations()[choice],
                                stop_object.get_name()):
        print("\nERROR: You are already at the end of the track.")
        print("+ Please try again and select the OTHER direction")
        return select_direction(route_object, stop_object)
    else:
        return choice


def is_valid_destination(direction_destination, stop_name):
    return stop_name not in direction_destination


def select_next_departure_time(direction_code, departures_json):
    for departure in departures_json:
        if departure['attributes']['direction_id'] == direction_code:
            if departure['attributes']['departure_time']:
                next_departure_time = datetime.strptime(departure['attributes']['departure_time'], '%Y-%m-%dT%H:%M:%S%z')
                if get_current_est_datetime() < next_departure_time:
                    return next_departure_time
    return None

# ---------------------------------------------------------------------------


# --------------- MODEL CLASSES ---------------------------------------------
class Route:
    def __init__(self):
        self.long_name = None
        self.api_id = None
        self.direction_destinations = None
        self.direction_names = None

    def set_long_name(self, long_name):
        self.long_name = long_name

    def get_long_name(self):
        return self.long_name

    def set_api_id(self, api_id):
        self.api_id = api_id

    def get_api_id(self):
        return self.api_id

    def set_direction_destinations(self, direction_destinations):
        self.direction_destinations = direction_destinations

    def get_direction_destinations(self):
        return self.direction_destinations

    def set_direction_names(self, direction_names):
        self.direction_names = direction_names

    def get_direction_names(self):
        return self.direction_names

    def print_direction(self, direction_code):
        print(self.direction_names[direction_code] + " to " + self.direction_destinations[direction_code])

    def print_direction_options(self):
        print("\nThe following are your direction options:")
        for code in range(len(self.direction_names)):
            print("ID("+str(code) + ") ", end="")
            self.print_direction(code)

    def populate_from_json(self, route_json):
        self.set_long_name(route_json['attributes']['long_name'])
        self.set_api_id(route_json['id'])
        self.set_direction_destinations(route_json['attributes']['direction_destinations'])
        self.set_direction_names(route_json['attributes']['direction_names'])
        return self


class Stop:
    def __init__(self):
        self.name = None
        self.api_id = None

    def set_name(self, name):
        self.name = name

    def get_name(self):
        return self.name

    def set_api_id(self, api_id):
        self.api_id = api_id

    def get_api_id(self):
        return self.api_id

    def populate_from_json(self, stop_json):
        self.set_name(stop_json['attributes']['name'])
        self.set_api_id(stop_json['id'])
        return self


class UserDesire:
    def __init__(self):
        self.route = None
        self.stop = None
        self.direction_code = None

    def set_route(self, route):
        self.route = route

    def get_route(self):
        return self.route

    def set_stop(self, stop):
        self.stop = stop

    def get_stop(self):
        return self.stop

    def set_direction_code(self, direction_code):
        self.direction_code = direction_code

    def get_direction_code(self):
        return self.direction_code
# ---------------------------------------------------------------------------


# ------------- CONTROLLER CLASS --------------------------------------------
class Controller:
    def __init__(self):
        self.user_desire = UserDesire()
        self.next_departure = None

    def set_next_departure(self, next_departure):
        self.next_departure = next_departure

    def print_next_departure(self):
        if self.next_departure:
            print("Will be departing at: ", end="")
            print(self.next_departure.strftime('%I:%M:%S%p on %Y/%m/%d'))
        else:
            print("Does not exist.")
            print("There is no scheduled train for the trip listed above.")

    def print_time_until_next_departure(self):
        est_current_datetime = get_current_est_datetime()
        time_delta = self.next_departure - est_current_datetime
        time_delta_minutes = time_delta.seconds // 60
        min_label = "minute" if time_delta_minutes == 1 else "minutes"
        time_delta_remaining_seconds = time_delta.seconds % 60
        second_label = "second" if time_delta_remaining_seconds == 1 else "seconds"
        print("You have: {} {} and {} {} to spare".format(str(time_delta_minutes), min_label,
                                                          str(time_delta_remaining_seconds), second_label))

    def print_summary(self):
        print("\n-------------------------------")
        print("The next ", end="")
        print(self.user_desire.get_route().get_long_name()+" train")
        print("At stop: "+self.user_desire.get_stop().get_name())
        print("Going in the direction: ", end="")
        self.user_desire.get_route().print_direction(self.user_desire.get_direction_code())
        self.print_next_departure()
        if self.next_departure:
            self.print_time_until_next_departure()
        print("-------------------------------")

    def run(self):
        self.user_desire.set_route(select_route(get_light_and_heavy_rail_routes_json()))
        self.user_desire.set_stop(select_stop(get_stops_json_for_route(self.user_desire.get_route())))
        self.user_desire.set_direction_code(select_direction(self.user_desire.get_route(), self.user_desire.get_stop()))
        self.set_next_departure(select_next_departure_time(self.user_desire.get_direction_code(),
                                                           get_departures_for_stop_and_route(self.user_desire.get_stop(),
                                                                                             self.user_desire.get_route())))
        self.print_summary()
# ---------------------------------------------------------------------------

# ------------ Automated Tests ----------------------------------------------
class TestMbtaChallenge(unittest.TestCase):

    def test_is_valid_destination_diff_names(self):
        self.assertTrue(is_valid_destination("Cleveland Circle", "Copley"))

    def test_is_valid_destination_same_names(self):
        self.assertFalse(is_valid_destination("North Station", "North Station"))

    def test_is_valid_destination_name_within_name(self):
        self.assertFalse(is_valid_destination("Ashmont/Braintree", "Braintree"))

    def test_get_mbta_api_data_as_json_valid_arguments(self):
        route_json = requests.get("https://api-v3.mbta.com/routes?filter[type]=0,1").json()['data']
        self.assertEqual(get_mbta_api_data_as_json("routes", {'filter[type]': '{},{}'.format(HEAVY_RAIL, LIGHT_RAIL)}),
                         route_json)

    def test_get_mbta_api_data_as_json_invalid_arguments(self):
        self.assertIsNone(get_mbta_api_data_as_json("this_is_invalid", {'no_params': 'fake_news'}))

    def test_get_light_and_heavy_rail_routes_with_equal_get_request(self):
        route_json = requests.get("https://api-v3.mbta.com/routes?filter[type]=0,1").json()['data']
        self.assertEqual(route_json, get_light_and_heavy_rail_routes_json())

    def test_get_stops_json_for_route_with_equal_get_request(self):
        route = Route()
        route.populate_from_json({"attributes":
                                      {"long_name": "Mattapan Trolley",
                                       "direction_destinations": ["Mattapan", "Ashmont"],
                                       "direction_names": ["Outbound", "Inbound"]
                                       },
                                  "id": "Mattapan"})
        stop_json = requests.get("https://api-v3.mbta.com/stops?filter[route]=Mattapan").json()['data']
        self.assertEqual(stop_json, get_stops_json_for_route(route))

    def test_get_input_from_user_valid_input(self):
        with patch('builtins.input', return_value='6') as mock_input:
            output = get_input_from_user("route", 7)
            mock_input.assert_called_once()
            self.assertEqual(output, 6)

    def test_get_input_from_user_invalid_input_not_number(self):
        sys.stdout = io.StringIO()  # suppressing function's print statements
        with patch('builtins.input', return_value='hey this is not valid') as mock_input:
            output = get_input_from_user("stop", 20)
            mock_input.assert_called_once()
            self.assertIsNone(output)
        sys.stdout = sys.__stdout__  # releasing suppression of print statements

    def test_get_input_from_user_invalid_input_number_out_of_range(self):
        sys.stdout = io.StringIO()  # suppressing function's print statements
        with patch('builtins.input', return_value='100') as mock_input:
            output = get_input_from_user("route", 21)
            mock_input.assert_called_once()
            self.assertIsNone(output)
        sys.stdout = sys.__stdout__  # releasing suppression of print statements

    def test_select_route(self):
        route = Route()
        route.populate_from_json({"attributes":
                                      {"long_name": "Mattapan Trolley",
                                       "direction_destinations": ["Mattapan", "Ashmont"],
                                       "direction_names": ["Outbound", "Inbound"]
                                       },
                                  "id": "Mattapan"})
        sys.stdout = io.StringIO()  # suppressing function's print statements
        with patch('builtins.input', return_value='1') as mock_input:
            output = select_route(get_light_and_heavy_rail_routes_json())
            mock_input.assert_called_once()
            self.assertEqual([output.get_long_name(), output.get_api_id(),
                              output.get_direction_destinations(), output.get_direction_names()],
                             [route.get_long_name(), route.get_api_id(),
                              route.get_direction_destinations(), route.get_direction_names()])
        sys.stdout = sys.__stdout__  # releasing suppression of print statements

    def test_select_stop(self):
        stop = Stop()
        stop.populate_from_json({"attributes": {"name": "Milton"},
                                 "id": "place-miltt"})
        mattapan_stop_json = requests.get("https://api-v3.mbta.com/stops?filter[route]=Mattapan").json()['data']
        sys.stdout = io.StringIO()  # suppressing function's print statements
        with patch('builtins.input', return_value='3') as mock_input:
            output = select_stop(mattapan_stop_json)
            mock_input.assert_called_once()
            self.assertEqual([output.get_api_id(), output.get_name()],
                             [stop.get_api_id(), stop.get_name()])
        sys.stdout = sys.__stdout__  # releasing suppression of print statements

    def test_select_direction(self):
        route = Route()
        route.populate_from_json({"attributes":
                                      {"long_name": "Mattapan Trolley",
                                       "direction_destinations": ["Mattapan", "Ashmont"],
                                       "direction_names": ["Outbound", "Inbound"]
                                       },
                                  "id": "Mattapan"})
        stop = Stop()
        stop.populate_from_json({"attributes": {"name": "Milton"},
                                 "id": "place-miltt"})
        sys.stdout = io.StringIO()  # suppressing function's print statements
        with patch('builtins.input', return_value='1') as mock_input:
            output = select_direction(route, stop)
            mock_input.assert_called_once()
            self.assertEqual(output, 1)
        sys.stdout = sys.__stdout__  # releasing suppression of print statements

# ---------------------------------------------------------------------------


# -------------- Running Portal ---------------------------------------------

if __name__ == '__main__':
    selection = input("Please enter 'test' to run tests, or any key to run the program: ")
    if selection == 'test':
        unittest.main()
    else:
        Controller().run()

# ---------------------------------------------------------------------------
