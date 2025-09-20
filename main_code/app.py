import gradio as gr
import os
import json
import logging
from langchain_openai import AzureChatOpenAI
from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_community.chat_message_histories import ChatMessageHistory
from langchain.chains import LLMChain
from langchain_core.runnables.history import RunnableWithMessageHistory
from dotenv import load_dotenv
from helper_function import extract_travel_json, get_valid_city_codes, extract_employee_id, extract_trip_details_json, beautify_trip_list, extract_trip_cancel_json
from load_valid_cities_and_purposes import get_valid_cities, get_valid_purposes
from myrequests import check_user_eligibility, check_trip_validity, post_es_get, post_es_final, get_user_header_details, get_trip_details, cancel_trip
from generate_es_get_payload import convert_to_es_get
from generate_es_final_payload import convert_to_es_final
from system_prompt import system_prompt

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("travel_chatbot")

load_dotenv()

# Setup OpenAI
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AI_BASE"),
    openai_api_version=os.getenv("AZURE_OPENAI_VERSION"),
    azure_deployment=os.getenv("AZURE_DEPLOYMENT"),
    temperature=0,
    max_tokens=None,
)

CITY_MAP = get_valid_cities("citynames.xlsx")
TRAVEL_PURPOSES = get_valid_purposes("Travel-Purpose.xlsx")
city_pairs = "\n".join([f"{city} → {code}" for city, code in CITY_MAP.items()])
purposes_list = ", ".join(TRAVEL_PURPOSES)

session_context = [
    ("system", system_prompt),
    ("human", f"Here are the valid city options:\n{city_pairs}"),
    ("human", f"Here are the valid travel purposes:\n{purposes_list}")
]

prompt = ChatPromptTemplate.from_messages(
    session_context + [
        MessagesPlaceholder(variable_name="history"),
        ("human", "{input}")
    ]
)

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

session_id = "user-session"
employee_details, city_code = None, None

def chatbot_response(user_input, history):
    global employee_details, city_code, pernr
    logger.info(f"User input received: {user_input}")

    response = chain.invoke(
        {"input": user_input},
        config={"configurable": {"session_id": session_id}}
    ).content.strip()
    logger.info(f"LLM Response: {response}")

    if response.startswith("<NEW_TRAVEL_REQUEST>"):
        employee_json, _ = extract_employee_id(response)
        logger.info(f"Extracted employee JSON: {employee_json}")

        if employee_json is None:
            return history + [[user_input, "❌ Cannot extract employee ID"]]

        pernr = int(employee_json['employee ID'])
        header_check, employee_details = get_user_header_details(pernr)
        logger.info(f"Employee details fetched: {employee_details}")

        if not header_check:
            return history + [[user_input, "❌ Not able to receive employee details"]]
        return history + [[user_input, "✅ Employee details fetched. Continue..."]]

    elif response.startswith("<TRAVEL_DATA_COLLECTED>"):
        travel_json, bot_response = extract_travel_json(response)
        logger.info(f"Extracted travel JSON: {travel_json}")

        if not isinstance(travel_json, dict):
            return history + [[user_input, "❌ Couldn't extract travel details. Re-enter."]]
        elif travel_json.get("travel_purpose") not in TRAVEL_PURPOSES:
            logger.warning(f"Invalid travel purpose: {travel_json.get('travel_purpose')}")
            return history + [[user_input, "❌ Invalid travel purpose. Re-enter."]]
        city_code = get_valid_city_codes(travel_json, CITY_MAP)
        logger.info(f"City codes resolved: {city_code}")

        if not city_code:
            return history + [[user_input, "❌ Invalid city. Re-enter."]]

        valid, remark = check_trip_validity(
            pernr,
            travel_json['start_date'],
            travel_json['end_date'],
            travel_json['start_time'],
            travel_json['end_time']
        )
        logger.info(f"Trip validation result: {valid}, Remark: {remark}")

        if not valid:
            return history + [[user_input, f"❌ Trip validation failed: {remark}"]]
        return history + [[user_input, bot_response]]

    elif response.startswith("JSON_READY:"):
        json_text = response[len("JSON_READY:"):].strip()
        try:
            simple_json = json.loads(json_text)
            logger.info(f"Parsed travel JSON for payloads: {simple_json}")
            es_get_payload = convert_to_es_get(simple_json, city_code, employee_details)
            es_final_payload = convert_to_es_final(simple_json, city_code, employee_details)
            logger.info("Calling ES GET and FINAL APIs")
            post_es_get()
            post_es_final()
            return history + [[user_input, "✅ Travel request submitted successfully."]]
        except Exception as e:
            logger.error(f"Failed to parse or process travel JSON: {e}")
            return history + [[user_input, f"❌ Error parsing JSON: {e}"]]

    elif response.startswith("<TRIP_DETAILS>"):
        trip_json = extract_trip_details_json(response)
        logger.info(f"Extracted trip JSON for viewing: {trip_json}")
        valid, trips = get_trip_details(trip_json)
        logger.info(f"Trip detail API result: {valid}, trips: {trips}")

        if not valid or all(not v for v in trips[0].values()):
            return history + [[user_input, "❌ No trips found for given dates"]]
        return history + [[user_input, beautify_trip_list(trips)]]

    elif response.startswith("<TRIP_CANCEL>"):
        json_check, trip_cancel_json = extract_trip_cancel_json(response)
        logger.info(f"Trip cancel JSON extracted: {trip_cancel_json}")

        if not json_check:
            return history + [[user_input, "❌ Failed to extract trip cancel JSON"]]
        success, cancel_trip_output = cancel_trip(trip_cancel_json)
        logger.info(f"Cancel trip result: {cancel_trip_output}")
        return history + [[user_input, cancel_trip_output['MESSAGE']]]

    else:
        return history + [[user_input, response]]

with gr.Blocks(css="""
    * { font-family: 'Comic Sans MS'; box-sizing: border-box; }
    html, body, .gradio-container {
        margin: 0;
        padding: 0;
        height: 100vh;
        width: 100vw;
        display: flex;
        flex-direction: column;
        background-color: #0f0f0f;
    }
    .gradio-container > div {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    .gr-block, .gr-form, .gr-row, .gr-column {
        height: auto !important;
    }
    footer {
        display: none !important;
    }
""") as demo:
    chatbot = gr.Chatbot(label="Travel Assistant", elem_id="chatbot")
    input_box = gr.Textbox(label="Type your request here", placeholder="Book travel, view trip, cancel...")
    clear_btn = gr.Button("Clear Chat")

    input_box.submit(fn=chatbot_response, inputs=[input_box, chatbot], outputs=chatbot)
    clear_btn.click(lambda: [], None, chatbot, queue=False)

if __name__ == "__main__":
    demo.launch()