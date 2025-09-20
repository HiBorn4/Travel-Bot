from loguru import logger
import os
from dotenv import load_dotenv
import json
import redis
import requests
from requests.auth import HTTPBasicAuth

load_dotenv()

REINR=""

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REDIS_TTL = int(os.getenv("REDIS_TTL_SEC", "3600"))  # seconds; default 1 hour

try:
    redis_client = redis.from_url(REDIS_URL, decode_responses=True)
    # quick connection check (optional)
    redis_client.ping()
    logger.info(f"Connected to Redis at {REDIS_URL}")
except Exception as e:
    redis_client = None
    logger.warning(f"Could not connect to Redis ({REDIS_URL}): {e}. Caching disabled.")

ES_USERNAME = os.getenv("ES_USERNAME", "")
ES_PASSWORD = os.getenv("ES_PASSWORD", "")

EMP_API_KEY = os.getenv("EMP_API_KEY", None)

def check_trip_validity(pernr, dept_date, arr_date, dept_time, arr_time, action="", tripno="0000000000"):
    """
    Calls trip validation endpoint and returns (True, remarks) when trip is valid, else (False, remarks).
    Date inputs expected as 'YYYYMMDD' strings, times as 'HH:MM' or 'HHMM' (we will normalize).
    """
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "X"
    }

    # normalize times (remove colon)
    def normalize_time(t):
        if t is None:
            return ""
        t = str(t).strip()
        return t.replace(":", "") if ":" in t else t

    dept_time_norm = normalize_time(dept_time)
    arr_time_norm = normalize_time(arr_time)
    
    base_url = "https://emssq.mahindra.com/sap/opu/odata/sap/ZHR_DOMESTIC_TRAVEL_SRV/ES_TRIPVALD"

    url = f"{base_url}(PERNR='{pernr}',DEPT_DATE='{dept_date}',ARR_DATE='{arr_date}',DEPT_TIME='{dept_time_norm}',ARR_TIME='{arr_time_norm}',ACTION='{action}',TRIPNO='{tripno}')?"
    logger.info(f"📡 Calling trip validation: {url}")

    try:
        auth = HTTPBasicAuth(ES_USERNAME, ES_PASSWORD) if (ES_USERNAME or ES_PASSWORD) else None
        resp = requests.get(url, headers=headers, auth=auth, timeout=10)
    except requests.exceptions.RequestException as e:
        logger.error(f"Trip validation request failed: {e}")
        return False, f"Request failed: {e}"

    if resp.status_code == 200:
        try:
            body = resp.json()
        except Exception as e:
            logger.error(f"Trip validation returned non-json: {e}")
            return False, "Invalid response from trip validation service."

        d = body.get("d", body)
        status = d.get("STATUS", "")
        remarks = d.get("REMARKS", "")

        # follow your provided logic:
        if status == "S" and "No trip available for given period" in remarks:
            logger.info(f"Trip validation success: {remarks}")
            return True, remarks
        elif status == "E" and "already exists" in remarks:
            logger.info(f"Trip validation invalid (already exists): {remarks}")
            return False, remarks
        else:
            logger.warning(f"Trip validation unknown status: {status} / {remarks}")
            return False, f"UNKNOWN STATUS: {status}, REMARKS: {remarks}"

    elif resp.status_code == 404:
        logger.info("Trip validation returned 404")
        return False, "Trip validation returned 404 - not found"
    else:
        logger.error(f"Trip validation unexpected status: {resp.status_code}")
        return False, f"Trip validation error: status {resp.status_code}"


def post_es_get(travel: dict, pernr: str):
    """
    Build the full ES_GET payload using the given travel dict and post it.
    Only known fields (dates, cities, reason, etc.) are substituted;
    all other fields remain identical to the template required by ES_GET.
    """
    headers = {
        "Accept": "application/json",
        "X-Requested-With": "X",
        "Authorization": EMP_API_KEY,
    }
    auth = HTTPBasicAuth(ES_USERNAME, ES_PASSWORD) if (ES_USERNAME or ES_PASSWORD) else None

    # helper to format YYYYMMDD to YYYY-MM-DDT00:00:00 for NAV_TRAVELDET
    def det_date(val):
        if not val:
            return ""
        v = str(val)
        if len(v) == 8 and v.isdigit():      # e.g. 20251015
            return f"{v[:4]}-{v[4:6]}-{v[6:]}T00:00:00"
        return v

    # base template with default constants
    payload = {
        "ACTION": "",
        "ADDADV": "0.00",
        "DATE_BEG": travel.get("start_date", ""),
        "DATE_END": travel.get("end_date", ""),
        "FLAG": "",
        "LOC_START": travel.get("origin_city", ""),
        "LOCATION_END": travel.get("destination_city", ""),
        "LOCSTART": "",
        "MOBILE": "9759206343",
        "NAV_APPROVERS": [],
        "NAV_GETSEARCH": [],
        "NAV_J12WAY": [],
        "NAV_PREFERRED_FLIGHT": [],
        "NAV_REPRICE": [],
        "NAV_TRAVELDET": [
            {
                "PERNR": pernr,
                "DATE_BEG": det_date(travel.get("start_date", "")),
                "TIME_BEG": travel.get("start_time", ""),
                "DATE_END": det_date(travel.get("end_date", "")),
                "TIME_END": travel.get("end_time", ""),
                "LOCATION_BEG": travel.get("origin_city", ""),
                "COUNTRY_BEG": "IN",
                "ORIGIN_CODE": "BOM",
                "LOCATION_END": travel.get("destination_city", ""),
                "COUNTRY_END": "IN",
                "DEST_CODE": "PNQ",
                "TRAVEL_MODE": travel.get("travel_mode","B"),
                "TRAVEL_MODE_CODE": "B",
                "TRAVEL_CLASS": "BAC",
                "TRAVEL_CLASS_TEXT": travel.get("travel_class_text", "AC"),
                "PREFERRED_FLIGHT": "",
                "MRC_1_2_WAY_FLAG": "",
                "ITENARY": "1",
                "TICKET_METHOD": travel.get("booking_method", "1"),
                "TICK_METH_TXT": travel.get("booking_method_text", "Self Booked")
            },
            {
                "PERNR": pernr,
                "DATE_BEG": det_date(travel.get("end_date", "")),
                "TIME_BEG": travel.get("start_time", ""),
                "DATE_END": det_date(travel.get("end_date", "")),
                "TIME_END": travel.get("end_time", ""),
                "LOCATION_BEG": travel.get("destination_city", ""),
                "COUNTRY_BEG": "IN",
                "ORIGIN_CODE": "PNQ",
                "LOCATION_END": travel.get("origin_city", ""),
                "COUNTRY_END": "IN",
                "DEST_CODE": "BOM",
                "TRAVEL_MODE": travel.get("travel_mode", "B"),
                "TRAVEL_MODE_CODE": "B",
                "TRAVEL_CLASS": "BAC",
                "TRAVEL_CLASS_TEXT": travel.get("travel_class_text", "AC"),
                "PREFERRED_FLIGHT": "",
                "MRC_1_2_WAY_FLAG": "",
                "ITENARY": "2",
                "TICKET_METHOD": travel.get("booking_method", "1"),
                "TICK_METH_TXT": travel.get("booking_method_text", "Self Booked")
            },
        ],
        "OLOC_START": "",
        "OLOCATION_END": "",
        "OTHERREASON": "",
        "PAYMODE": "Bank Transfer To A/C -4248735076",
        "PERNR": pernr,
        "PERSA": "CCRP",
        "PERSK": "A3",
        "REASON": travel.get("travel_purpose", ""),
        "REINR": "0000000000",
        "SEARCHMANDT": "X",
        "SEARCHVISIBLE": "X",
        "TIME_BEG": travel.get("start_time", ""),
        "TIME_END": travel.get("end_time", ""),
        "TRAVADV": "0.00",
    }

    logger.warning(f"Trip validation payload: {payload}")

    # Save for debugging
    try:
        with open("es_get.json", "w") as f:
            json.dump(payload, f, indent=2)
    except Exception:
        logger.exception("Failed to write es_get.json (non-fatal)")

    try:
        api_url = "https://emssq.mahindra.com/domestictravel/ES_GET"
        logger.info(f"Posting to ES_GET: {api_url}")
        resp = requests.post(api_url, auth=auth, json=payload, headers=headers, timeout=(500,1000))
    except requests.exceptions.RequestException as e:
        logger.error(f"ES_GET request failed: {e}")
        return False, f"ES_GET request failed: {e}"

    if resp.status_code == 201:
        logger.info("ES_GET posted successfully (201).")
        return True, None
    else:
        reason = f"ES_GET failed status {resp.status_code}: {resp.text[:400]}"
        logger.error(reason)
        return False, reason



def post_es_final(travel: dict, pernr: str):
    """
    Build full ES_FINAL payload and POST it.
    Uses template defaults and substitutes known travel data.
    """
    
    global REINR

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Requested-With": "X",
        "Authorization": EMP_API_KEY,
    }
    auth = HTTPBasicAuth(ES_USERNAME, ES_PASSWORD) if (ES_USERNAME or ES_PASSWORD) else None

    def det_date(val):
        # format YYYYMMDD to /Date(ms)/ for NAV_FIN_TO_IT
        if not val:
            return ""
        v = str(val)
        if len(v) == 8 and v.isdigit():
            # convert to epoch ms at midnight
            from datetime import datetime
            dt = datetime.strptime(v, "%Y%m%d")
            return f"/Date({int(dt.timestamp()) * 1000})/"
        return v

    payload = {
        "ACTION": "",
        "ADDADV": f"{travel.get('additional_advance', 0):.2f}",
        "AGE": "27",
        "ATTACHMANDT": "",
        "ATTACHVISIBLE": "",
        "COMMENT": "",
        "CREAT_DATE": "",
        "DATE_BEG": travel.get("start_date", ""),
        "DATE_END": travel.get("end_date", ""),
        "DOB": "19980901",
        "EMAIL": travel.get("email", f"{pernr}@MAHINDRA.COM"),
        "FNAME": "",
        "ISSFUSERID": "",
        "LNAME": "",
        "LOC_START": travel.get("origin_city", ""),
        "LOCATION_END": travel.get("destination_city", ""),
        "MNAME": "",
        "MOBILE": "",
        "MODE": "",
        "NAV_FIN_BOOK": [],
        "NAV_FIN_COMING": [],
        "NAV_FIN_COST": [
            {
                "AUFNR": "",
                "KOSTL": travel.get("cost_center", ""),
                "PERCENT": "100.00",
                "POSNR": travel.get("project_wbs", ""),
                "POSNR2W": "",
            }
        ],
        "NAV_FIN_EMPFLIGHTS": [],
        "NAV_FIN_FILES": [],
        "NAV_FIN_GOING": [],
        "NAV_FIN_J12WAY": [],
        "NAV_FIN_ONEWAY": [],
        "NAV_FIN_REPRICE": [],
        "NAV_FIN_SEGMENT": [],
        "NAV_FIN_TO_IT": [
            {
                "CITY_CLASS": "",
                "COUNTRY_BEG": "IN",
                "COUNTRY_END": "IN",
                "DATE_BEG": det_date(travel.get("start_date", "")),
                "DATE_END": det_date(travel.get("end_date", "")),
                "DEL_BUTTON_READ_ONLY": "",
                "DEST_CODE": "PNQ",
                "EDIT_BUTTON_READ_ONLY": "",
                "ITENARY": "1",
                "LOCATION_BEG": travel.get("origin_city", ""),
                "LOCATION_END": travel.get("destination_city", ""),
                "MRC_1_2_WAY_FLAG": "",
                "ORIGIN_CODE": "BOM",
                "PERNR": pernr,
                "PREFERRED_FLIGHT": "",
                "TIME_BEG": travel.get("start_time", ""),
                "TIME_END": travel.get("end_time", ""),
                "TRAVEL_CLASS": travel.get("travel_class", "*"),
                "TRAVEL_CLASS_TEXT": travel.get("travel_class_text", "Any Class"),
                "TRAVEL_MODE": travel.get("travel_mode", "O"),
                "TRAVEL_MODE_CODE": "O",
                "TICK_METH_TXT": travel.get("booking_method", ""),
                "TICKET_METHOD": travel.get("booking_method", ""),
            },
            {
                "CITY_CLASS": "",
                "COUNTRY_BEG": "IN",
                "COUNTRY_END": "IN",
                "DATE_BEG": det_date(travel.get("end_date", "")),
                "DATE_END": det_date(travel.get("end_date", "")),
                "DEL_BUTTON_READ_ONLY": "",
                "DEST_CODE": "BOM",
                "EDIT_BUTTON_READ_ONLY": "",
                "ITENARY": "2",
                "LOCATION_BEG": travel.get("destination_city", ""),
                "LOCATION_END": travel.get("origin_city", ""),
                "MRC_1_2_WAY_FLAG": "",
                "ORIGIN_CODE": "PNQ",
                "PERNR": pernr,
                "PREFERRED_FLIGHT": "",
                "TIME_BEG": travel.get("start_time", ""),
                "TIME_END": travel.get("end_time", ""),
                "TRAVEL_CLASS": travel.get("travel_class", "*"),
                "TRAVEL_CLASS_TEXT": travel.get("travel_class_text", "Any Class"),
                "TRAVEL_MODE": travel.get("travel_mode", "O"),
                "TRAVEL_MODE_CODE": "O",
                "TICK_METH_TXT": travel.get("booking_method", ""),
                "TICKET_METHOD": travel.get("booking_method", ""),
            },
        ],
        "NO_VALIDATIONS": "X",
        "OLOC_START": "",
        "OLOCATION_END": "",
        "OTHERREASON": "",
        "PAYMODE": "Bank Transfer To A/C -4248735076",
        "PERNR": pernr,
        "PERSA": "CCRP",
        "PERSK": "A3",
        "REASON": travel.get("travel_purpose", ""),
        "REINR": "0000000000",
        "SEARCHMANDT": "X",
        "SEARCHMODE": "",
        "SEARCHVISIBLE": "X",
        "SEX": "Male",
        "TIME_BEG": travel.get("start_time", ""),
        "TIME_END": travel.get("end_time", ""),
        "TITLE": "Mr",
        "TRAVADV": f"{travel.get('travel_advance', 0):.2f}",
        "TRIPDEL": "",
        "TRIPEDIT": "",
        "WAERS": "",
        "WBSMAND": "",
    }

    logger.warning(f"ES_FINAL payload: {payload}")

    try:
        api_url = "https://emssq.mahindra.com/domestictravel/ES_FINAL"
        logger.info(f"Posting to ES_FINAL: {api_url}")
        resp = requests.post(api_url, auth=auth, json=payload, headers=headers, timeout=(250, 300))
    except requests.exceptions.RequestException as e:
        logger.error(f"ES_FINAL request failed: {e}")
        return False, f"ES_FINAL request failed: {e}"

    # ---- NEW: extract REINR from SAP response ----
    if resp.status_code in {200, 201}:
        try:
            sap_answer = resp.json()          # OData JSON
            reinr = sap_answer["d"]["REINR"]  # Trip number SAP just created
            REINR = reinr     # keep it for later use
            logger.info(f"SAP trip created successfully – REINR: {reinr}")
            return True, None
        except (KeyError, ValueError) as e:
            logger.warning(f"Could not extract REINR from SAP reply: {e}")
            return True, None                 # still success, just no number
    else:
        reason = f"ES_FINAL failed status {resp.status_code}: {resp.text[:400]}"
        logger.error(reason)
        return False, reason

def cancel_trip(trip_json: dict):
    """
    Calls ES_TRIP_CANCEL endpoint to cancel a trip.
    Expects trip_json with:
        {
            "employee_id": "<8-digit ID>",
            "trip_num": "<Trip number>"
        }
    Returns (True, dict) on success else (False, reason)
    """
    pernr = trip_json.get("employee_id", "")
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
        auth = HTTPBasicAuth(ES_USERNAME, ES_PASSWORD) if (ES_USERNAME or ES_PASSWORD) else None
        resp = requests.get(url, headers=headers, auth=auth, timeout=10)
    except requests.exceptions.RequestException as e:
        logger.error(f"Trip cancel request failed: {e}")
        return False, f"Request failed: {e}"

    if resp.status_code == 200:
        try:
            data = resp.json().get("d", {})
            result = {
                "MESSAGE_TYPE": data.get("MESSAGE_TYPE", ""),
                "MESSAGE": data.get("MESSAGE", "")
            }
            logger.info(f"Trip cancel success: {result}")
            return True, result
        except Exception as e:
            return False, f"Invalid JSON response: {e}"
    else:
        reason = f"Request failed with status code {resp.status_code}"
        logger.error(reason)
        return False, reason
