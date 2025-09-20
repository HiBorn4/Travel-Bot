# langchain_chatbot_main.py

import os
import json
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains import LLMChain
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
from load_valid_cities_and_purposes import get_valid_cities, get_valid_purposes
from system_prompt import system_prompt
from handle_responses import handle_new_travel_request, handle_travel_data_collected, handle_json_ready, handle_trip_details, handle_trip_cancel, handle_default_response


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
            global pernr, employee_details
            response, pernr, employee_details = handle_new_travel_request(response)
            if response is None:
                continue
            print(response)
            # continue

        elif response.startswith("<TRAVEL_DATA_COLLECTED>"):
            global city_code
            print("TRIP VALIDATION API CALLED")
            response, city_code = handle_travel_data_collected(response, pernr)
            if response is None:
                continue
            print(response)
            # continue


        elif response.startswith("JSON_READY:"):
            print('----------------')
            print("I GOT JSON_READY")
            print(response)
            print('----------------')
            try:
                handle_json_ready(response, city_code, employee_details)
                continue
            except Exception as e:
                print(f"❌ Failed to parse travel request JSON: {e}")
                break

        
        elif response.startswith("<TRIP_DETAILS>"):
            respone = handle_trip_details(respone)
            if respone is None:
                break
            print(respone)
            # continue

        elif response.startswith("<TRIP_CANCEL>"):
            respone = handle_trip_cancel(response)
            if respone is None:
                break
            print(respone)
            # continue

        respone = handle_default_response(response)
        print(respone)
        # continue


## 2200118347                                                                                                                                                                                                                                                          
