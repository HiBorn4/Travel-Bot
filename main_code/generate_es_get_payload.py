# generate_es_get_payload.py

from datetime import datetime
from travel_modes import TRAVEL_MODES

# DEFAULTS = {
#     "REINR": "0000000000",
#     "COUNTRY_BEG": "IN",
#     "COUNTRY_END": "IN"
# }

def format_datetime_iso(date_str):
    return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%dT00:00:00")

def create_segment(input_json, city_code, employee_details, itinerary_no, reverse=False):
    travel_mode = input_json["travel_mode"]
    mode_config = TRAVEL_MODES.get(travel_mode, TRAVEL_MODES["Bus"])
    requires_ticket = mode_config.get("defaults", {}).get("requires_ticket_method", True)

    origin = city_code["destination_city"] if reverse else city_code["origin_city"]
    destination = city_code["origin_city"] if reverse else city_code["destination_city"]
    origin_code = city_code["destination_city_code"] if reverse else city_code["origin_city_code"]
    dest_code = city_code["origin_city_code"] if reverse else city_code["destination_city_code"]

    date_beg = input_json["end_date"] if reverse else input_json["start_date"]
    date_end = input_json["end_date"] if reverse else input_json["start_date"]
    time_beg = input_json["end_time"] if reverse else input_json["start_time"]
    time_end = "00:00" if reverse else input_json["end_time"]

    travel_class_input = input_json.get("travel_class_text", "AC")
    travel_class_mapping = mode_config.get("travel_class", {})

    # Resolve class code and text
    if travel_mode == "Own Car":
        travel_class_text = "Any Class"
        travel_class_code = "*"
    else:
        travel_class_code = travel_class_mapping.get(travel_class_input)
        if travel_class_code:
            travel_class_text = travel_class_input
        else:
            travel_class_text = next((k for k, v in travel_class_mapping.items() if v == travel_class_input), "")
            travel_class_code = travel_class_input if travel_class_text else ""

    booking_method_text = input_json.get("booking_method", "Company Booked")
    booking_method_code = mode_config["booking_method"].get(booking_method_text, "3")

    segment = {
        "PERNR": employee_details["PERNR"],
        "DATE_BEG": format_datetime_iso(date_beg),
        "TIME_BEG": time_beg.replace(":", "") + "00",
        "DATE_END": format_datetime_iso(date_end),
        "TIME_END": time_end.replace(":", "") + "00",
        "LOCATION_BEG": origin,
        "COUNTRY_BEG": "IN",
        "ORIGIN_CODE": origin_code,
        "LOCATION_END": destination,
        "COUNTRY_END": "IN",
        "DEST_CODE": dest_code,
        "TRAVEL_MODE": mode_config["code"],
        "TRAVEL_MODE_CODE": mode_config["code"],
        "TRAVEL_CLASS": travel_class_code,
        "TRAVEL_CLASS_TEXT": travel_class_text,
        "PREFERRED_FLIGHT": "",
        "MRC_1_2_WAY_FLAG": "",
        "ITENARY": str(itinerary_no)
    }

    if requires_ticket:
        segment["TICKET_METHOD"] = booking_method_code
        segment["TICK_METH_TXT"] = booking_method_text

    return segment

def convert_to_es_get(input_json, city_code, employee_details):
    print('INSIDE CREATING ES GET')
    print('input_json')
    print(input_json)
    print('----------------')
    print('city_code')
    print(city_code)
    print('----------------')
    print('employee_details')
    print(employee_details)
    print('----------------')
    round_trip = input_json.get("journey_type", "One Way").lower() == "round trip"

    segments = [create_segment(input_json, city_code, employee_details, itinerary_no=1)]
    if round_trip:
        segments.append(create_segment(input_json, city_code, employee_details, itinerary_no=2, reverse=True))

    print('IN ES_GET BEFORE RETURN')
    
    return {
        "ACTION": "",
        "ADDADV": employee_details.get("ADDADV", "0.00"),
        "DATE_BEG": input_json["start_date"],
        "DATE_END": input_json["end_date"],
        "FLAG": "",
        "LOC_START": city_code["origin_city"],
        "LOCATION_END": city_code["destination_city"],
        "LOCSTART": "",
        "MOBILE": employee_details.get("MOBILE", ""),
        "NAV_APPROVERS": [],
        "NAV_GETSEARCH": [],
        "NAV_J12WAY": [],
        "NAV_PREFERRED_FLIGHT": [],
        "NAV_REPRICE": [],
        "NAV_TRAVELDET": segments,
        "OLOC_START": "",
        "OLOCATION_END": "",
        "OTHERREASON": "",
        "PAYMODE": employee_details.get("PAYMODE", ""),
        "PERNR":employee_details["PERNR"],
        "PERSA": employee_details.get("PERSA", ""),
        "PERSK": employee_details.get("PERSK", ""),
        "REASON": input_json["travel_purpose"],
        "REINR": "0000000000",
        "SEARCHMANDT": "X",
        "SEARCHVISIBLE": "X",
        "TIME_BEG": input_json["start_time"],
        "TIME_END": input_json["end_time"],
        "TRAVADV": employee_details.get("TRAVADV", "0.00")
    }
