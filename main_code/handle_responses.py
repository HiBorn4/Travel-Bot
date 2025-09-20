import json

from generate_es_get_payload import convert_to_es_get
from generate_es_final_payload import convert_to_es_final
from myrequests import check_user_eligibility, check_trip_validity, post_es_get, post_es_final, get_user_header_details, get_trip_details, cancel_trip
from helper_function import extract_travel_json, get_valid_city_codes, extract_employee_id, extract_trip_details_json, beautify_trip_list, extract_trip_cancel_json
from load_valid_cities_and_purposes import get_valid_cities, get_valid_purposes


# Load allowed values
CITY_MAP = get_valid_cities("citynames.xlsx")
TRAVEL_PURPOSES = get_valid_purposes("Travel-Purpose.xlsx")
city_pairs = "\n".join([f"{city} → {code}" for city, code in CITY_MAP.items()])
purposes_list = ", ".join(TRAVEL_PURPOSES)

def handle_new_travel_request(response):
    global employee_details, pernr
    employee_details = None
    pernr = None
    employee_json, remaining_text = extract_employee_id(response)

    if employee_json is None:
        print("❌ Cannot extract employee ID")
        return None, pernr, employee_details

    pernr = int(employee_json['employee ID'])
    print('📡 Getting Employee Details')
    header_check, employee_details = get_user_header_details(pernr)

    if not header_check:
        print('❌ Not able to receive employee details')
        return None, pernr, employee_details

    print("✅ User Validity Check API Called")
    valid_user, remark = check_user_eligibility(pernr)
    if not valid_user:
        print("❌", remark)
        return None, pernr, employee_details

    response = remaining_text.replace("<NEW_TRAVEL_REQUEST>", "").strip()
    # print(response)
    return response, pernr, employee_details


def handle_travel_data_collected(response, pernr):
    global city_code
    city_code = None
    travel_json, response = extract_travel_json(response)

    if not isinstance(travel_json, dict):
        response = "Sorry, I couldn't extract your travel details. Could you please re-enter the start and end dates and times?"
        return response, city_code

    if travel_json.get("travel_purpose") not in TRAVEL_PURPOSES:
        allowed = ", ".join(TRAVEL_PURPOSES[:5])
        response = f''''{travel_json.get('travel_purpose')}' is not a valid travel purpose.\n Please choose a valid purpose such as: {allowed}.\n 
                        What is the purpose of your trip?"
                    '''

        return response, city_code

    city_code = get_valid_city_codes(travel_json, CITY_MAP)
    
    if not city_code:
        allowed = ", ".join(list(CITY_MAP.keys())[:5])
        response = f'''One or both cities are not valid.\n, Valid cities include: {allowed}.\n Please re-enter your origin and destination cities.
                   '''
        return response, city_code

    trip_valid_check, remark = check_trip_validity(
        pernr,
        travel_json['start_date'],
        travel_json['end_date'],
        travel_json['start_time'],
        travel_json['end_time']
    )
    if not trip_valid_check:
        response = "❌ Trip validation failed:", remark
        return response, city_code

    return response, city_code


def handle_json_ready(response, city_code, employee_details):
    # print("📦 Generating payloads using city code:", city_code)
    json_text = response[len("JSON_READY:"):].strip()
    simple_json = json.loads(json_text)
    # print("\nGenerated Travel Request JSON:")
    print(json.dumps(simple_json, indent=4))

    confirm = input("\nDo you want to submit this request? (yes/no): ").strip().lower()
    if confirm in ["yes", "y"]:
        print('INSIDE CONFIRMATION')
        es_get_payload = convert_to_es_get(simple_json, city_code, employee_details)
        es_final_payload = convert_to_es_final(simple_json, city_code, employee_details)

        with open("es_get.json", "w") as f:
            json.dump(es_get_payload, f, indent=4)
        print("es_get save")

        with open("es_final.json", "w") as f:
            json.dump(es_final_payload, f, indent=4)
        print("es_get save")
        
        print('✅ Payloads saved to es_get.json and es_final.json')
        print("🚀 Calling ES_GET and ES_FINAL APIs...")
        post_es_get()
        post_es_final()
        print("✅ Travel request successfully submitted.")
        


def handle_trip_details(response):
    global trip_json
    trip_json = extract_trip_details_json(response)
    if trip_json is None:
        print("There is an issue in extracting trip details.")
        return None

    trip_detail_check, trips = get_trip_details(trip_json)
    if not trip_detail_check:
        print('Unable to extract trip details from API')
        return None
    elif all(not v for v in trips[0].values()):
        print('There are no trips created for the given dates')
        return None
    else:
        response = beautify_trip_list(trips)
        # print(response)
        return response


def handle_trip_cancel(response):
    json_check, trip_cancel_json = extract_trip_cancel_json(response)
    if not json_check:
        print('Unable to extract trip cancel json')
        return None

    trip_cancel_status, cancel_trip_output = cancel_trip(trip_cancel_json)
    if not trip_cancel_status:
        print(cancel_trip_output)
        return None

    response = cancel_trip_output['MESSAGE']
    # print(response)
    return response


def handle_default_response(response):
    # print(response)
    return response
