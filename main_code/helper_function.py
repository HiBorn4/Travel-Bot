import json 
import re 
from datetime import datetime, timedelta

def purpose_validation(travel_json, TRAVEL_PURPOSES):
    travel_purpose = travel_json['purpose']
    if travel_purpose in TRAVEL_PURPOSES:
        return True
    else:
        return False

def get_valid_city_codes(travel_json, city_map):
    origin = travel_json.get("origin_city")
    destination = travel_json.get("destination_city")

    if origin in city_map and destination in city_map:
        result_dict = {'origin_city':origin,
                       'origin_city_code':city_map[origin],
                       'destination_city':destination,
                       'destination_city_code':city_map[destination]}
        return result_dict
    return False

def extract_employee_id(response_text):
    match = re.search(r"\{[\s\S]*\}", response_text)
    if match:
        json_str = match.group(0)
        try:
            parsed_json = json.loads(json_str)
            before_json = response_text.replace(json_str, "").strip()
            return parsed_json, before_json
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse JSON: {e}")
            return None, response_text
    else:
        return None, response_text

def extract_travel_json(input_string: str):
    input_string = input_string.replace("<TRAVEL_DATA_COLLECTED>", "").strip()
    json_pattern = re.compile(r'\{.*?\}', re.DOTALL)
    match = json_pattern.search(input_string)
    
    if match:
        json_str = match.group()
        try:
            json_data = json.loads(json_str)
            
            # Convert date fields to YYYYMMDD format
            for date_key in ["start_date", "end_date"]:
                if date_key in json_data:
                    try:
                        json_data[date_key] = datetime.strptime(json_data[date_key], "%Y%m%d").strftime("%Y%m%d")
                    except ValueError:
                        print(f"Warning: Invalid date format for {date_key}")
            
            # Convert time fields to HHMMSS format
            for time_key in ["start_time", "end_time"]:
                if time_key in json_data:
                    try:
                        json_data[time_key] = datetime.strptime(json_data[time_key], "%H:%M").strftime("%H%M%S")
                    except ValueError:
                        print(f"Warning: Invalid time format for {time_key}")
            
            # Extract remaining text after JSON
            bot_response = input_string.replace(json_str, "").strip()
            return json_data, bot_response
        except json.JSONDecodeError:
            print("Error: Extracted JSON is invalid")
            return None, None
    
    print("No valid JSON found in input string")
    return None, None


def get_date_range_around_today():
    today = datetime.today()
    start_date = (today - timedelta(days=90)).strftime("%Y%m%d")
    end_date = (today + timedelta(days=90)).strftime("%Y%m%d")
    return start_date, end_date

def extract_trip_details_json(response: str):
    if response.startswith("<TRIP_DETAILS>"):
        try:
            json_part = response.replace("<TRIP_DETAILS>", "").strip()
            trip_json = json.loads(json_part)

            # If both start_date and end_date are empty, assign default range
            if trip_json.get("start_date", "") == "" and trip_json.get("end_date", "") == "":
                start_date, end_date = get_date_range_around_today()
                trip_json["start_date"] = start_date
                trip_json["end_date"] = end_date

            return trip_json

        except json.JSONDecodeError as e:
            print(f"❌ JSON decoding failed: {e}")
            return None
    else:
        print("❌ Input does not start with <TRIP_DETAILS>")
        return None

def format_date(date_str):
    try:
        return datetime.strptime(date_str, "%Y%m%d").strftime("%Y-%m-%d")
    except ValueError:
        return date_str
    
def beautify_trip_list(trip_list):
    if not trip_list:
        return "No trips found."

    response_lines = ["📋 Here are your trip details:\n"]

    for i, trip in enumerate(trip_list, start=1):
        trip_no = trip.get("trip_number", "N/A")
        start_date = format_date(trip.get("start_date", ""))
        end_date = format_date(trip.get("end_date", ""))
        status = trip.get("approval_status", "N/A")

        response_lines.append(
            f"{i}. Trip No: {trip_no}\n"
            f"   - Start Date: {start_date}\n"
            f"   - End Date: {end_date}\n"
            f"   - Status: {status}\n"
        )

    return "\n".join(response_lines)



def extract_trip_cancel_json(response: str):
    if response.startswith("<TRIP_CANCEL>"):
        try:
            json_part = response.replace("<TRIP_CANCEL>", "").strip()
            extracted_json = json.loads(json_part)
            return True, extracted_json
        except json.JSONDecodeError as e:
            output = f"❌ JSON decoding failed: {e}"
            print(output)
            return False, output
    else:
        output = "❌ Input does not start with <TRIP_CANCEL>"
        print(output)
        return None, output