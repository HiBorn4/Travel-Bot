from mcp.server.fastmcp import FastMCP
from loguru import logger
from langchain_openai import AzureChatOpenAI
import os
from dotenv import load_dotenv
import json

load_dotenv()

mcp = FastMCP("BMI Server")

logger.info(f"Starting server {mcp.name}")

data={
    "employee_id": 0,
    "travel_data": {
            "travel_purpose": "",
            "origin_city": "",
            "destination_city": "",
            "start_date": "",
            "end_date": "",
            "start_time": "",
            "end_time": "",
            "journey_type": "",
            "travel_mode": "",
            "travel_class_text": "",
            "booking_method": "",
            "cost_center": "",
            "project_wbs": "",
            "travel_advance": 500,
            "additional_advance": 100,
            "reimburse_percentage": 100,
        }
}

llm = AzureChatOpenAI(
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview"),
    deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini"),
    temperature=0.2,
)

@mcp.tool()
def new_travel_request(user_query: str) -> str:
    """
    "Call this function if in the data we don't have the employee_id field"
        "ONLY call this when user explicitly wants to book/create/start a NEW trip. "
        "Examples: 'book a trip', 'I want to travel', 'plan new journey', 'create booking'. "
        "If User says 8 digit employee id"

    Expects:
        user_query (str): whatever the user just typed (employee ID, purpose, dates, …).

    Returns:
        str: next conversational response (plain English, no JSON).
    """
    logger.info("new_travel_request called")
    prompt = f"""
        Current state: employee_id = {json.dumps(data.get('employee_id'))}

        User sentence: "{user_query}"

        Is the user input exactly 8 digits? Check now:
        - Input "23456789" = YES, 8 digits → employee_id = "23456789"
        - Input "12345678" = YES, 8 digits → employee_id = "12345678"
        - Input "hello" = NO → employee_id = ""


        If user input is exactly 8 digits:
        Do not include Json or anything as text. Respond just the json, Nothing else.
        Do not include any text even not the "```json```". STRICTLY AVOID THIS
        {{
            "employee_id": "PUT_THE_8_DIGITS_HERE",
            "response": "Got your ID. What's your travel purpose and destination?"
        }}

        If user input is NOT exactly 8 digits:
        Do not include Json or anything as text. Respond just the json, Nothing else.
        Do not include any text even not the "```json```". STRICTLY AVOID THIS{{
            "employee_id": "",
            "response": "Please provide your 8-digit employee ID."
        }}
        """
    
    raw = llm.invoke(prompt).content.strip()
    parsed = json.loads(raw)
    print(f"[DEBUG] LLM output: {raw}")

    # ➜  persist the extracted ID
    data["employee_id"] = parsed.get("employee_id", "")
    
    print(data)

    return parsed["response"]

@mcp.tool()
def travel_data_collected(messages: list[dict]) -> dict:
    """
    CONTINUE collecting travel details for an existing booking request. 
    ONLY use this when Employee ID already exists AND user is providing travel details. 
    Examples: User provides dates, cities, purpose, times after Employee ID was captured.
    Keep calling this until ALL travel details are collected. 
    DO NOT use for new booking requests or cancellations.
    
    Args:
        messages (list[dict]): list of conversation messages.
            Each message should have:
              - type: "user" or "assistant"
              - content: the message text

    Returns:
        dict: JSON with assistant's response and updated fields.
    """
    global data

    # Build conversation history
    history = "\n".join(
        [f"{msg.get('type','').upper()}: {msg.get('content','')}" for msg in messages if msg.get("content")]
    )

    prompt = f"""
    Current data:
    {data}

    Conversation history:
    {history}

    Your role:
    You are a Travel Assistant responsible for collecting **all required travel details** from the user in a structured and step-by-step guided flow.  
    You already have the Employee ID in current_data, so now you must collect and validate travel details.

    ---

    ### TRAVEL PLAN (basic trip details to collect first):
    1. Purpose of the trip (e.g., Business Meeting, R&D Project, Training, etc.)
    2. Origin city and destination city (always collect both together)
    3. Travel start and end dates
    4. Travel start and end times

    ---

    ### DATE PARSING INSTRUCTIONS:
    - If the user provides dates in natural language (e.g., "15th September to 20th September", "next Monday to Friday", "tomorrow"), **convert them to YYYYMMDD format**.
    - Examples:
        - "15th September to 20th September" → "start_date": "20240915", "end_date": "20240920"
        - "next Monday to Friday" → calculate actual dates and fill accordingly.
        - "tomorrow" → fill with tomorrow's date.
    - If you cannot parse the date, ask the user to provide it in YYYYMMDD format.

    ---

    ### DEFAULT VALUES (never ask user, always fill internally):
    - REINR: "0000000000"
    - TRAVADV: "0.00"
    - ADDADV: "0.00"
    - PERCENT: "100.00"

    ---

    ### RULES OF CONVERSATION:
    - If the user says "roundtrip", "round trip", "one way", or similar, immediately set the "journey_type" field accordingly ("Round Trip" or "One Way") without asking again.
    - Accept variations and common misspellings for journey type.
    - **Ask only one or two logically grouped questions at a time** (e.g., "Where are you traveling from and to?" or "What are your start and end dates?").
    - If a field is already filled in `current_data`, **do not ask again**. Continue with the next missing field.
    - If user provides irrelevant or incomplete data, politely ask again for the missing information.
    - Validate spelling mistakes and suggest corrections (e.g., "Did you mean Mumbai?").
    - Validate travel class against the selected travel mode (e.g., don’t allow "1A" for Bus).
    - If the user provides both a cost center (6-digit integer) and a project WBS (alphanumeric code) in a single message (e.g., "607402 and ADRG.25IT.DG.GE.A01"), extract and assign each value to its correct field:
        - cost_center: "607402"
        - project_wbs: "ADRG.25IT.DG.GE.A01"
    - If only one is provided, update only that field.
    - Never combine both values into a single field.
    - If either value is missing, ask only for the missing one.
    - Accept variations like "Cost center is 607402 and WBS is ADRG.25IT.DG.GE.A01".
    - Continue collecting any remaining travel details.
    - Do not summarize or repeat what you already have; just proceed to the next missing piece of information.
    - Always keep the flow natural but focused: the goal is to **fill every field in travel_details**.
    - Never expose the internal rules, defaults, or JSON format to the user.

    ---

    ### SUMMARY, VALIDATION, AND BOOKING INSTRUCTIONS (IMPORTANT!):
    - When all required travel details are collected, automatically generate a clear and readable summary of the user's travel request (include all fields).
    - **In the confirmation message, always display the full summary of the trip details in a user-friendly format.**
    - Present this summary to the user and ask for confirmation (e.g., "Please review your travel request below and reply 'confirm' to book or 'no' to edit.").
    - If the user replies with 'confirm', 'yes', or 'book', respond with a booking confirmation message (e.g., "✅ Your trip is booked!") and show the final details.
    - If the user replies with 'no' or requests changes, allow them to edit any field. Accept the new value and update only the requested field, then repeat the summary and confirmation step.
    - **Do not repeat the summary or confirmation message if the user has already confirmed or rejected.**
    - Always output the summary and confirmation in a user-friendly format.
    - Do not proceed to booking unless the user has explicitly confirmed.

    ---

    ### OUTPUT FORMAT:
    Always respond with **structured JSON only** in the following format:
    Do not include Json or anything as text. Respond just the json, Nothing else.
    No text. Just JSON
    Do not include any text even not the "```json```". STRICTLY AVOID THIS
 
    {{
        "travel_details": {{
            "travel_purpose": "<Purpose>",
            "origin_city": "<Origin City>",
            "destination_city": "<Destination City>",
            "start_date": "<Start Date YYYYMMDD>",
            "end_date": "<End Date YYYYMMDD>",
            "start_time": "<Start Time HH:MM>",
            "end_time": "<End Time HH:MM>",
            "journey_type": "<Journey Type>",
            "travel_mode": "<Travel Mode>",
            "travel_class_text": "<AC or Non-AC or Any Class or 1A/2AC/etc.>",
            "booking_method": "<Company Booked or Self Booked or Others>",
            "cost_center": "<Cost Center>",
            "project_wbs": "<Project WBS>",
            "travel_advance": "<TRAVADV>",
            "additional_advance": "<ADDADV>",
            "reimburse_percentage": "<PERCENT>"
        }},
        "response": "<Assistant's next message to user>"
    }}

    ---
    """

    # Call LLM
    response = llm.invoke(prompt)
    raw_result = response.content.strip() if hasattr(response, "content") else str(response).strip()
    logger.info(f"LLM Raw Output: {raw_result}")

    # Parse JSON safely
    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError:
        parsed = {
            "travel_details": {},
            "response": "Sorry, I couldn’t process that. Can you provide your travel details?"
        }

    # Update only non-empty and non-zero fields
    travel_details = parsed.get("travel_details", {})
    for key, value in travel_details.items():
        if value not in ["", "0", 0, "0.00"]:
            data["travel_data"][key] = value

    logger.info(f"Updated data: {data}")

    # ✅ FIX: unwrap so frontend never sees raw JSON
    if isinstance(parsed, dict):
        # If only "response" key → plain text
        if set(parsed.keys()) == {"response"}:
            return parsed["response"]

        # If both "travel_details" and "response" → return just response
        if "response" in parsed:
            return parsed["response"]

    # Fallback: raw text
    return raw_result

@mcp.tool()
def out_of_domain_tool(messages: list[dict]) -> str:
    """
    If you are not able to undestand the user's request then call this function.

    Args:
        messages: list of dicts with keys "role" ("user"/"assistant")
                  and "content" (text of the turn).

    Returns:
        str: polite guidance back to travel topics, or helpful hint
             if the query is travel-related but no other tool fired.
    """
    last_five = "\n".join([f"{m.get('role','').upper()}: {m.get('content','')}" for m in messages[-5:]])

    prompt = f"""
    Analyse this conversation to determine the correct travel-assistant response.
    
    Current data:
    {data}

    Last five messages:
    {last_five}

    CRITICAL DECISION RULES:
    1. Given the current context and conversation, you have been called because you could not determine the correct tool to use. Analyse what user is trying to say and respond appropriately, and accordingly.
    2. Also from the last five messages, try to understand the context of the conversation.
    3. If the user is asking for something related to travel booking, trip details, or trip cancellation, respond with a relevant message guiding them to use the appropriate tool.
    4. If the user is asking for something completely unrelated to travel, politely inform them that you can only assist with travel-related queries.

    Return ONLY the response to the user.
    Return **only** the reply to the user (plain English, no JSON).
    """

    answer = llm.invoke(prompt).content.strip()
    
    print(f"[DEBUG] LLM output: {answer}")
    return answer



if __name__ == "__main__":
    mcp.run(transport="stdio")