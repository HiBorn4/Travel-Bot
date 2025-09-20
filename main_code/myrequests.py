import requests
from requests.auth import HTTPBasicAuth
import json 
import base64

# Authentication credentials
username = "25017514"
password = "Bhavyajoshi@2025"


    
def get_user_header_details(pernr):
    
    headers = {
    'Accept': 'application/json',
    # 'X-Requested-With': 'X',
    'Authorization': 'Basic MjUwMTc1MTQ6Qmhhdnlham9zaGlAMjAyNQ==',
    # 'Cookie': 'MYSAPSSO2=AjQxMDMBABgyADUAMAAxADcANQAxADQAIAAgACAAIAACAAY1ADAAMAADABBSAFEAMgAgACAAIAAgACAABAAYMgAwADIANQAwADkAMAAzADAAOQAwADIABQAEAAAACAYAAlgACQACRQD%2fAVYwggFSBgkqhkiG9w0BBwKgggFDMIIBPwIBATELMAkGBSsOAwIaBQAwCwYJKoZIhvcNAQcBMYIBHjCCARoCAQEwcDBkMQswCQYDVQQGEwJERTEcMBoGA1UEChMTU0FQIFRydXN0IENvbW11bml0eTETMBEGA1UECxMKU0FQIFdlYiBBUzEUMBIGA1UECxMLSTAwMjAxNzkyOTMxDDAKBgNVBAMTA1JRMgIICiAhESUJFAEwCQYFKw4DAhoFAKBdMBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTI1MDkwMzA5MDIyOFowIwYJKoZIhvcNAQkEMRYEFPC4JGHwlPNMyhOfSmKoZrf359HPMAkGByqGSM44BAMELjAsAhQJP976NJDU6s6UgQFvXJnZXNz2%2fAIUI4SK6ZpFgAAMMA643hc5tdnrXe4%3d; SAP_SESSIONID_RQ2_500=Z3JoSB5kLMGgOlxzn55jQbd9Nb2IpBHwm8lZQonZyag%3d; sap-usercontext=sap-client=500'
    }
    
    # Encode the username and password
    auth_string = f"{username}:{password}"
    encoded_auth = base64.b64encode(auth_string.encode("utf-8")).decode("utf-8")
    
    base_url = "https://emssq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV/ES_HEADER"
    # POST API URL with query parameters and expansions
    url = f"{base_url}(UNAME='{pernr}',REINR='',MODE='',PERNR='{pernr}')?sap-client=500&async=true&$expand=NAV_MODE%2CNAV_CITYCLASS%2CNAV_CITYLIST%2CNAV_TICKMETHOD%2CNAV_PURPOSE%2CNAV_COSTASSIGN%2CNAV_KOSTL%2CNAV_CITY%2CNAV_TRAVELCLASS%2CNAV_EMPFLIGHTS%2CNAV_TRAVELDET"

    print("📡 Calling ES_HEADER POST API...")
    # print("ES HEADER URL:")
    # print(url)
    payload = {}
    try:
        # response = requests.post(url, headers=headers, auth=HTTPBasicAuth(username, password))
        response = requests.request("GET", url, headers=headers, data=payload)
        if response.status_code == 200:
            data = response.json().get("d", {})

            extracted_info = {
                "PERNR": data.get("PERNR", ""),
                "MOBILE": data.get("MOBILE", ""),
                "PAYMODE": data.get("PAYMODE", ""),
                "DOB": data.get("DOB", ""),
                "SEX": data.get("SEX", ""),
                "AGE": data.get("AGE", ""),
                "EMAIL": data.get("EMAIL", ""),
                "FNAME": data.get("FNAME", ""),
                "LNAME": data.get("LNAME", ""),
                "MNAME": data.get("MNAME", ""),
                "TITLE": data.get("TITLE", ""),
                "PERSK": data.get("PERSK", ""),
                "PERSA": data.get("PERSA", "")
            }

            print("✅ Extracted user details successfully.")
            return True, extracted_info

        elif response.status_code == 404:
            print("❌ ES_HEADER API returned 404 - user not found.")
            return False, {"error": "User not found (404)"}

        else:
            print(f"❌ Unexpected status code: {response.status_code}")
            return False, {"error": f"Unexpected status code: {response.status_code}"}

    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return False, {"error": str(e)}




def check_user_eligibility(pernr):
    headers = {
    "Accept": "application/json",
    "X-Requested-With": "X"
    }    
    # pernr = int(pernr)
    base_url = "https://emssq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV/ES_MODE_ELIG_OR_NOT"
    
    # Format the URL with the personnel number
    url = f"{base_url}(PERNR='{pernr}')"
    
    try:
        # Make the GET request with basic authentication
        # print('USER VALIDITY API CALLED')
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
        remark = None
        # Check the response status code
        if response.status_code == 200:
            print('** ES_MODE_ELIG_OR_NOT - User is Valid **')
            return True, remark
        elif response.status_code == 404:
            remark = 'response status code is 404'
            print('**ES_MODE_ELIG_OR_NOT - User is NOT Valid **')
            return False, remark
        else:
            remark = f"Error: Received unexpected status code {response.status_code}"
            return False, remark
    except requests.exceptions.RequestException as e:
        remark = f"An error occurred: {e}"
        return False, remark




def check_trip_validity(pernr, dept_date, arr_date, dept_time, arr_time, action="", tripno="0000000000"):
    headers = {
    "Accept": "application/json",
    "X-Requested-With": "X"
    }
    # Base URL of the API
    base_url = "https://emssq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV/ES_TRIPVALD"
    
    # Format the URL with the provided parameters
    url = f"{base_url}(PERNR='{pernr}',DEPT_DATE='{dept_date}',ARR_DATE='{arr_date}',DEPT_TIME='{dept_time}',ARR_TIME='{arr_time}',ACTION='{action}',TRIPNO='{tripno}')?"
    print('TRIP VALID URL')
    print(url)
    try:
        # Make the GET request with basic authentication
        # print("TRIP VALIDATION API CALLED")
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))
        if response.status_code == 200:
            data = response.json()
            status = data.get("d", {}).get("STATUS", "")
            remarks = data.get("d", {}).get("REMARKS", "")
            if status == "S" and remarks == "No trip available for given period":
                print(f"trip remark : Valid Trip")
                return True, remarks
            elif status == "E" and "already exists" in remarks:
                print(f"trip remark : Invalid Trip : {remarks}")
                return False, remarks
            else:
                print('log - UNKNOWN STATUS')
                return False, f"UNKNOWN STATUS: {status}, REMARKS: {remarks}"  # Handle unexpected statuses or remarks
        elif response.status_code == 404:
            print('log - status code 404')
            return False, f'response status code is 404'
        else:
            print(f'Error: Received unexpected status code {response.status_code}')
            return False, f"Error: Received unexpected status code {response.status_code}"
    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")
        return False, f"An error occurred: {e}"
    
'''
IN-VALID TRIP RESPONSE
"STATUS": "E",
"REMARKS": "Trip 2200118348 from Date 26-03-2025 07:00:00 to Date 26-03-2025 19:00:00 already exists"

VALID-TRIP RESPONSE
"STATUS": "S",
"REMARKS": "No trip available for given period"

'''


def post_es_get():
    api_url = "https://emssq.mahindra.com/domestictravel/ES_GET"
    
    headers = {
    'Accept': 'application/json',
    'X-Requested-With': 'X',
    'Authorization': 'Basic MjUwMTc1MTQ6Qmhhdnlham9zaGlAMjAyNQ==',
    # 'Cookie': 'MYSAPSSO2=AjQxMDMBABgyADUAMAAxADcANQAxADQAIAAgACAAIAACAAY1ADAAMAADABBSAFEAMgAgACAAIAAgACAABAAYMgAwADIANQAwADkAMAAzADAAOQAwADIABQAEAAAACAYAAlgACQACRQD%2fAVYwggFSBgkqhkiG9w0BBwKgggFDMIIBPwIBATELMAkGBSsOAwIaBQAwCwYJKoZIhvcNAQcBMYIBHjCCARoCAQEwcDBkMQswCQYDVQQGEwJERTEcMBoGA1UEChMTU0FQIFRydXN0IENvbW11bml0eTETMBEGA1UECxMKU0FQIFdlYiBBUzEUMBIGA1UECxMLSTAwMjAxNzkyOTMxDDAKBgNVBAMTA1JRMgIICiAhESUJFAEwCQYFKw4DAhoFAKBdMBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTI1MDkwMzA5MDIyOFowIwYJKoZIhvcNAQkEMRYEFPC4JGHwlPNMyhOfSmKoZrf359HPMAkGByqGSM44BAMELjAsAhQJP976NJDU6s6UgQFvXJnZXNz2%2fAIUI4SK6ZpFgAAMMA643hc5tdnrXe4%3d; SAP_SESSIONID_RQ2_500=Z3JoSB5kLMGgOlxzn55jQbd9Nb2IpBHwm8lZQonZyag%3d; sap-usercontext=sap-client=500'
    }
    
    # headers = {
    # 'Accept': 'application/json',
    # # 'X-Requested-With': 'X',
    # 'Authorization': 'Basic MjUwMTc1MTQ6Qmhhdnlham9zaGlAMjAyNQ==',
    # # 'Cookie': 'MYSAPSSO2=AjQxMDMBABgyADUAMAAxADcANQAxADQAIAAgACAAIAACAAY1ADAAMAADABBSAFEAMgAgACAAIAAgACAABAAYMgAwADIANQAwADkAMAAzADAAOQAwADIABQAEAAAACAYAAlgACQACRQD%2fAVYwggFSBgkqhkiG9w0BBwKgggFDMIIBPwIBATELMAkGBSsOAwIaBQAwCwYJKoZIhvcNAQcBMYIBHjCCARoCAQEwcDBkMQswCQYDVQQGEwJERTEcMBoGA1UEChMTU0FQIFRydXN0IENvbW11bml0eTETMBEGA1UECxMKU0FQIFdlYiBBUzEUMBIGA1UECxMLSTAwMjAxNzkyOTMxDDAKBgNVBAMTA1JRMgIICiAhESUJFAEwCQYFKw4DAhoFAKBdMBgGCSqGSIb3DQEJAzELBgkqhkiG9w0BBwEwHAYJKoZIhvcNAQkFMQ8XDTI1MDkwMzA5MDIyOFowIwYJKoZIhvcNAQkEMRYEFPC4JGHwlPNMyhOfSmKoZrf359HPMAkGByqGSM44BAMELjAsAhQJP976NJDU6s6UgQFvXJnZXNz2%2fAIUI4SK6ZpFgAAMMA643hc5tdnrXe4%3d; SAP_SESSIONID_RQ2_500=Z3JoSB5kLMGgOlxzn55jQbd9Nb2IpBHwm8lZQonZyag%3d; sap-usercontext=sap-client=500'
    # }
    
    
    json_file_path = "es_get.json"
    # Load the JSON payload from the file
    with open(json_file_path, 'r') as json_file:
        payload = json.load(json_file)
    
        
    try:    
        # Send the POST request with basic authentication and JSON payload
        response = requests.post(api_url, auth=HTTPBasicAuth(username, password), json=payload, headers=headers)
        
        # Check the response status code
        if response.status_code == 201:
            return True
        else:
            reason = f"FAILURE: Received status code {response.status_code}"
            return False
    except FileNotFoundError:
        reason = "FAILURE: JSON file not found"
        return False
    except json.JSONDecodeError:
        reason = "FAILURE: Error decoding JSON file"
        return False
    except requests.exceptions.RequestException as e:
        reason = f"FAILURE: An error occurred while making the request: {e}"
        return False
    


def post_es_final():
    api_url = "https://emssq.mahindra.com/domestictravel/ES_FINAL"
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Requested-With": "X",
        'Authorization': 'Basic MjUwMTc1MTQ6Qmhhdnlham9zaGlAMjAyNQ==',
    }
    json_file_path = "es_final.json"
    # Load the JSON payload from the file
    with open(json_file_path, 'r') as json_file:
        payload = json.load(json_file)
    print("es_final save")
    try:
        # Send the POST request with basic authentication and JSON payload
        response = requests.post(api_url, auth=HTTPBasicAuth(username, password), json=payload, headers=headers)
        
        # Check the response status code
        if response.status_code == 201:
            return True
        else:
            reason = f"FAILURE: Received status code {response.status_code}"
            return False
    except FileNotFoundError:
        reason = "FAILURE: JSON file not found"
        return False
    except json.JSONDecodeError:
        reason = "FAILURE: Error decoding JSON file"
        return False
    except requests.exceptions.RequestException as e:
        response = f"FAILURE: An error occurred while making the request: {e}"
        return False
    

def get_trip_details(pernr, start_date='', end_date='', trip_number='', filter_status=''):
    base_url = "https://emmsq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV"
    
    # Construct the dynamic API endpoint
    endpoint = (
        f"/ES_TRIP_GET_LIST_OF_EMPSet("
        f"USER_ID='{pernr}',"
        f"EMP_ID='',"
        f"FILTER_STATUS='{filter_status}',"
        f"TRIP_NUMBER='{trip_number}',"
        f"STARTDATE='{start_date}',"
        f"ENDDATE='{end_date}')"
        f"/NAV_Get_Emp_Trips_List?sap-client=500"
    )

    url = base_url + endpoint

    headers = {
        "Accept": "application/json",
        "X-Requested-With": "X"
    }

    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), headers=headers)
        
        if response.status_code == 200:
            data = response.json()
            return True, data.get("d", {}).get("results", [])
        else:
            reason = f"FAILURE: Received status code {response.status_code}"
            return False, reason
    except requests.exceptions.RequestException as e:
        return False, f"FAILURE: An error occurred while making the request: {e}"



def get_trip_details(trip_json):
    user_id = trip_json.get("employee ID", "")
    trip_number = trip_json.get("trip_number", "")
    start_date = trip_json.get("start_date", "")
    end_date = trip_json.get("end_date", "")
    filter_status = ""

    base_url = "https://emssq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV"
    
    endpoint = (
        f"/ES_TRIP_GET_LIST_OF_EMPSet("
        f"USER_ID='{user_id}',"
        f"EMP_ID='',"
        f"FILTER_STATUS='{filter_status}',"
        f"TRIP_NUMBER='{trip_number}',"
        f"STARTDATE='{start_date}',"
        f"ENDDATE='{end_date}')"
        f"/NAV_Get_Emp_Trips_List?sap-client=500"
    )

    url = base_url + endpoint
    print('GET TRIP DETAILS URL')
    print(url)
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "X"
    }

    try:
        response = requests.get(url, auth=HTTPBasicAuth(username, password), headers=headers)

        if response.status_code == 200:
            data = response.json()
            trip_list = data.get("d", {}).get("results", [])
            extracted_trips = []

            for trip in trip_list:
                extracted_trips.append({
                    "trip_number": trip.get("TRIP_NUMBER", ""),
                    "start_date": trip.get("STARTDATE", ""),
                    "end_date": trip.get("ENDDATE", ""),
                    "approval_status": trip.get("APPROVALSTATUS", "")
                })

            return True, extracted_trips
        else:
            return False, f"FAILURE: Received status code {response.status_code}"

    except requests.exceptions.RequestException as e:
        return False, f"FAILURE: An error occurred while making the request: {e}"


def cancel_trip(trip_json):
    pernr = trip_json.get("employee ID", "")
    tripno = trip_json.get("trip_num", "")
    comments = "Trip cancellation requested by user"

    base_url = "https://emssq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV"
    endpoint = f"/ES_TRIP_CANCEL(PERNR='{pernr}',TRIPNO='{tripno}',COMMENTS='{comments}')?"
    url = base_url + endpoint

    headers = {
        "Accept": "application/json",
        "X-Requested-With": "X"
    }

    try:
        response = requests.get(url, headers=headers, auth=HTTPBasicAuth(username, password))

        if response.status_code == 200:
            data = response.json()
            message_type = data.get("d", {}).get("MESSAGE_TYPE", "")
            message = data.get("d", {}).get("MESSAGE", "")
            cancel_trip_output = {'MESSAGE_TYPE':message_type, "MESSAGE":message}
            return True, cancel_trip_output
        else:
            cancel_trip_output = f"Request failed with status code {response.status_code}"
            return False, cancel_trip_output

    except requests.exceptions.RequestException as e:
        cancel_trip_output = f"An error occurred: {e}"
        return False, cancel_trip_output




'''
https://emssq.mahindra.com/domestictravel/ES_GET

'''