# langchain_chatbot_main.py

import os
import json
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains import LLMChain
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
from generate_es_get_payload import convert_to_es_get
from generate_es_final_payload import convert_to_es_final
from myrequests import check_user_eligibility, check_trip_validity, post_es_get, post_es_final, get_user_header_details, get_trip_details, cancel_trip
from helper_function import extract_travel_json, get_valid_city_codes, extract_employee_id, extract_trip_details_json, beautify_trip_list, extract_trip_cancel_json
from load_valid_cities_and_purposes import get_valid_cities, get_valid_purposes
from system_prompt import system_prompt

load_dotenv()
# Load from .env
openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
openai_api_base = os.getenv("AI_BASE")
openai_api_version = os.getenv("AZURE_OPENAI_VERSION")
deployment_name = os.getenv("AZURE_DEPLOYMENT")

# Azure Chat OpenAI Setup
llm = AzureChatOpenAI(
    azure_endpoint=openai_api_base,
    openai_api_version=openai_api_version,
    azure_deployment=deployment_name,
    temperature=0,
    max_tokens=None,
)

# Load allowed values
CITY_MAP = get_valid_cities("citynames.xlsx")
TRAVEL_PURPOSES = get_valid_purposes("Travel-Purpose.xlsx")
city_pairs = "\n".join([f"{city} → {code}" for city, code in CITY_MAP.items()])
purposes_list = ", ".join(TRAVEL_PURPOSES)

# pernr = str(25017514)

# Pre-injected static context for each session
session_context = [
    ("system", system_prompt),
    ("human", f"Here are the valid city options:\n{city_pairs}"),
    ("human", f"Here are the valid travel purposes:\n{purposes_list}")
]

# Main dynamic prompt for user input
prompt = ChatPromptTemplate.from_messages(
    session_context + [
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ]
)

# Conversation memory
store = {}
def get_memory(session_id: str):
    if session_id not in store:
        store[session_id] = ChatMessageHistory()
    return store[session_id]

chain = RunnableWithMessageHistory(
    runnable=prompt | llm,
    get_session_history=get_memory,
    input_messages_key="input",
    history_messages_key="history"
)

# Run the CLI bot
if __name__ == "__main__":
    session_id = "user-session"
    print("Hi, I'm your travel request assistant. Please choose if you want to create a new travel request, view you existing trip details or cancle your trips.")

    while True:
        user_input = input("[You]: ").strip()
        if user_input.lower() in ["exit", "quit"]:
            break

        response = chain.invoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}}
        ).content.strip()

        if response.startswith("<NEW_TRAVEL_REQUEST>"):
            global employee_details
            employee_json, remaining_text = extract_employee_id(response)

            if employee_json is None:
                print("❌ Cannot extract employee ID")
                break

            pernr = int(employee_json['employee ID'])
            print('📡 Getting Employee Details')
            header_check, employee_details = get_user_header_details(pernr)

            if not header_check:
                print('❌ Not able to receive employee details')
                break

            print("✅ User Validity Check API Called")
            # valid_user, remark = check_user_eligibility(pernr)
            # if not valid_user:
            #     print("❌", remark)
            #     break
            # response = remaining_text.replace("<NEW_TRAVEL_REQUEST>", "").strip()
            # print(response)


        elif response.startswith("<TRAVEL_DATA_COLLECTED>"):
            print("TRIP VALIDATION API CALLED")
            global city_code
            city_code = None
            travel_json, bot_response = extract_travel_json(response)

            if not isinstance(travel_json, dict):
                response = "Sorry, I couldn't extract your travel details. Could you please re-enter the start and end dates and times?"
            elif travel_json.get("travel_purpose") not in TRAVEL_PURPOSES:
                allowed = ", ".join(TRAVEL_PURPOSES[:5])
                response = (
                    f"'{travel_json.get('travel_purpose')}' is not a valid travel purpose.\n"
                    f"Please choose a valid purpose such as: {allowed}.\n"
                    "What is the purpose of your trip?"
                )
            else:
                city_code = get_valid_city_codes(travel_json, CITY_MAP)
                if not city_code:
                    allowed = ", ".join(list(CITY_MAP.keys())[:5])
                    response = (
                        f"One or both cities are not valid.\n"
                        f"Valid cities include: {allowed}.\n"
                        "Please re-enter your origin and destination cities."
                    )
                else:
                    # print("✅ City code:", city_code)
                    trip_valid_check, remark = check_trip_validity(
                        pernr,
                        travel_json['start_date'],
                        travel_json['end_date'],
                        travel_json['start_time'],
                        travel_json['end_time']
                    )
                    if not trip_valid_check:
                        print("❌ Trip validation failed:", remark)
                        continue
                    # print('bot response after trip validity')
                    # print(bot_response)
                    response = bot_response
                    print(response)
                     


        elif response.startswith("JSON_READY:"):
            print("📦 Generating payloads using city code:", city_code)
            json_text = response[len("JSON_READY:"):].strip()
            try:
                simple_json = json.loads(json_text)
                print("\nGenerated Travel Request JSON:")
                print(json.dumps(simple_json, indent=4))

                confirm = input("\nDo you want to submit this request? (yes/no): ").strip().lower()
                if confirm in ["yes", "y"]:
                    es_get_payload = convert_to_es_get(simple_json, city_code, employee_details)
                    es_final_payload = convert_to_es_final(simple_json, city_code, employee_details)

                    with open("es_get.json", "w") as f:
                        json.dump(es_get_payload, f, indent=4)

                    with open("es_final.json", "w") as f:
                        json.dump(es_final_payload, f, indent=4)

                    print('✅ Payloads saved to es_get.json and es_final.json')
                    print("🚀 Calling ES_GET and ES_FINAL APIs...")
                    post_es_get()
                    post_es_final()
                    print("✅ Travel request successfully submitted.")
                    continue 

            except Exception as e:
                print(f"❌ Failed to parse travel request JSON: {e}")

        
        elif response.startswith("<TRIP_DETAILS>"):
            global trip_json
            # print(response)
            trip_json = extract_trip_details_json(response)
            if trip_json is None:
                print("There is an issue in extracting trip details.")
                continue
            trip_detail_check, trips = get_trip_details(trip_json)
            if not trip_detail_check:
                print('Unable to extract trip details from API')
                continue
            elif all(not v for v in trips[0].values()):
                print('There are no trips created for the given dates')
                continue
            else:
                response = beautify_trip_list(trips)
                print(response)
                continue

        elif response.startswith("<TRIP_CANCEL>"):
            json_check, trip_cancel_json = extract_trip_cancel_json(response)
            if not json_check:
                print('Unable to extract trip cancel json')
            # print(trip_cancel_json)
            trip_cancel_status, cancel_trip_output = cancel_trip(trip_cancel_json)
            if not trip_cancel_status:
                print(cancel_trip_output)
            response = cancel_trip_output['MESSAGE']
            print(response)
        else:
            print(response)

            
## 2200118347
'''
I want to travel to pune from mumbai for RnD project, 5th aug 2025 9am to 10th aug 2025 10pm, I will travel in my own vehicle, its a round trip, my cost center is 852800 and WBS is ADRG.25IT.DG.GE.A01
'''