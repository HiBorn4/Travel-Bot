# generate_es_final_payload.py

from datetime import datetime, timezone
from travel_modes import TRAVEL_MODES

# DEFAULTS = {
#     "PERNR": "25017514",
#     "REINR": "0000000000",
#     "MOBILE": "9759206343",
#     "PAYMODE": "Bank Transfer To A/C -4248735076",
#     "PERSK": "A3",
#     "PERSA": "CCRP",
#     "ADDADV": "0.00",
#     "TRAVADV": "0.00",
#     "PERCENT": "100.00",
#     "EMAIL": "25017514@MAHINDRA.COM",
#     "FNAME": "Bhavya",
#     "LNAME": "Joshi",
#     "MNAME": "",
#     "TITLE": "Mr",
#     "SEX": "Male",
#     "DOB": "19900101",
#     "COUNTRY_BEG": "IN",
#     "COUNTRY_END": "IN"
# }

def to_epoch_date(date_str):
    dt = datetime.strptime(date_str, "%Y%m%d").replace(tzinfo=timezone.utc)
    return f"/Date({int(dt.timestamp()) * 1000})/"

def create_segment(input_json, city_code, employee_details, itinerary_no, round_trip=False, reverse=False):
    travel_mode = input_json["travel_mode"]
    mode_config = TRAVEL_MODES.get(travel_mode, TRAVEL_MODES["Bus"])
    requires_ticket = mode_config["defaults"].get("requires_ticket_method", True)

    origin = city_code["destination_city"] if reverse else city_code["origin_city"]
    destination = city_code["origin_city"] if reverse else city_code["destination_city"]
    origin_code = city_code["destination_city_code"] if reverse else city_code["origin_city_code"]
    dest_code = city_code["origin_city_code"] if reverse else city_code["destination_city_code"]

    travel_class_input = input_json.get("travel_class_text", "AC")
    travel_class_mapping = mode_config.get("travel_class", {})

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

    start_date = input_json["start_date"]
    end_date = input_json["end_date"]
    start_time = input_json["start_time"].replace(":", "") + "00"
    end_time = input_json["end_time"].replace(":", "") + "00"

    if round_trip:
        if itinerary_no == 1:
            date_beg = to_epoch_date(start_date)
            date_end = to_epoch_date(end_date)
            time_beg = start_time
            time_end = end_time
        else:
            date_beg = to_epoch_date(end_date)
            date_end = to_epoch_date(end_date)
            time_beg = end_time
            time_end = "000000"
    else:
        date_beg = to_epoch_date(start_date)
        date_end = to_epoch_date(end_date)
        time_beg = start_time
        time_end = end_time

    segment = {
        "CITY_CLASS": "",
        "COUNTRY_BEG": "IN",
        "COUNTRY_END": "IN",
        "DATE_BEG": date_beg,
        "DATE_END": date_end,
        "DEL_BUTTON_READ_ONLY": "",
        "DEST_CODE": dest_code,
        "EDIT_BUTTON_READ_ONLY": "",
        "ITENARY": str(itinerary_no),
        "LOCATION_BEG": origin,
        "LOCATION_END": destination,
        "MRC_1_2_WAY_FLAG": "",
        "ORIGIN_CODE": origin_code,
        "PERNR": employee_details["PERNR"],
        "PREFERRED_FLIGHT": "",
        "TIME_BEG": time_beg,
        "TIME_END": time_end,
        "TRAVEL_CLASS": travel_class_code,
        "TRAVEL_CLASS_TEXT": travel_class_text,
        "TRAVEL_MODE": mode_config["code"],
        "TRAVEL_MODE_CODE": mode_config["code"],
        "TICK_METH_TXT": booking_method_text if requires_ticket else "",
        "TICKET_METHOD": booking_method_code if requires_ticket else ""
    }

    return segment

def convert_to_es_final(input_json, city_code, employee_details):
    print('INSIDE CREATING ES FINAL')
    round_trip = input_json.get("journey_type", "One Way").lower() == "round trip"

    segments = [create_segment(input_json, city_code, employee_details, itinerary_no=1, round_trip=round_trip)]
    if round_trip:
        segments.append(create_segment(input_json, city_code,employee_details, itinerary_no=2, round_trip=round_trip, reverse=True))

    print('IN ES_FINAL BEFORE RETURN')
    return {
        "ACTION": "",
        "ADDADV": employee_details.get("ADDADV", "0.00"),
        "AGE": employee_details.get("AGE", ""),
        "ATTACHMANDT": "",
        "ATTACHVISIBLE": "",
        "COMMENT": input_json.get("comment", ""),
        "CREAT_DATE": "",
        "DATE_BEG": input_json["start_date"],
        "DATE_END": input_json["end_date"],
        "DOB": employee_details.get("DOB", ""),
        "EMAIL": employee_details.get("EMAIL", ""),
        "FNAME": employee_details.get("FNAME", ""),
        "ISSFUSERID": "",
        "LNAME": employee_details.get("LNAME", ""),
        "LOC_START": city_code["origin_city"],
        "LOCATION_END": city_code["destination_city"],
        "MNAME": employee_details.get("MNAME", ""),
        "MOBILE": employee_details.get("MOBILE", ""),
        "MODE": "",
        "NAV_FIN_BOOK": [],
        "NAV_FIN_COMING": [],
        "NAV_FIN_COST": [{
            "AUFNR": "",
            "KOSTL": input_json["cost_center"],
            "PERCENT": employee_details.get("PERCENT", "100.00"),
            "POSNR": input_json.get("project_wbs", ""),
            "POSNR2W": ""
        }],
        "NAV_FIN_EMPFLIGHTS": [],
        "NAV_FIN_FILES": [],
        "NAV_FIN_GOING": [],
        "NAV_FIN_J12WAY": [],
        "NAV_FIN_ONEWAY": [],
        "NAV_FIN_REPRICE": [],
        "NAV_FIN_SEGMENT": [],
        "NAV_FIN_TO_IT": segments,
        "NO_VALIDATIONS": "X",
        "OLOC_START": "",
        "OLOCATION_END": "",
        "OTHERREASON": "",
        "PAYMODE": employee_details.get("PAYMODE", ""),
        "PERNR": employee_details.get("PERNR", ""),
        "PERSA": employee_details.get("PERSA", ""),
        "PERSK": employee_details.get("PERSK", ""),
        "REASON": input_json["travel_purpose"],
        "REINR": "0000000000",
        "SEARCHMANDT": "X",
        "SEARCHMODE": "",
        "SEARCHVISIBLE": "X",
        "SEX": employee_details.get("SEX", ""),
        "TIME_BEG": input_json["start_time"].replace(":", "") + "00",
        "TIME_END": input_json["end_time"].replace(":", "") + "00",
        "TITLE": employee_details.get("TITLE", ""),
        "TRAVADV": employee_details.get("TRAVADV", "0.00"),
        "TRIPDEL": "",
        "TRIPEDIT": "",
        "WAERS": "",
        "WBSMAND": ""
    }
