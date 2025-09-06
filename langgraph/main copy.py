from fastapi import FastAPI
from pydantic import BaseModel
import os
import requests
from langchain_openai import AzureChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated, List, Dict, Callable
import operator
from langchain_core.messages import BaseMessage, HumanMessage
from dotenv import load_dotenv
import json
import inspect

load_dotenv()

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

# --- 1. Define the State ---
class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    selected_tool: str
    result: str

def new_travel_request(state: AgentState):

    global data
    # Get the latest user message
    user_input = state["messages"][-1].content if state["messages"] else ""
    prompt = f"""
User input: "{user_input}"

Is the user input exactly 8 digits? Check now:
- Input "23456789" = YES, 8 digits → employee_id = "23456789"
- Input "12345678" = YES, 8 digits → employee_id = "12345678"
- Input "hello" = NO → employee_id = ""

Current employee_id in data: {data.get('employee_id', 0)}

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
    response = llm.invoke(prompt)
    raw_result = response.content.strip() if hasattr(response, "content") else str(response).strip()
    print(f"LLM Raw Output: {raw_result}")

    try:
        parsed = json.loads(raw_result)
    except json.JSONDecodeError:
        parsed = {"employee_id": "", "response": "Sorry, I couldn't process that. Please repeat."}

    # Extract employee_id directly
    if parsed.get("employee_id"):
        data["employee_id"] = parsed["employee_id"]  # ✅ update without overwriting travel_data
        
        
        
        
    # -------------------------
    # 1st API
    # -------------------------
        
        
        

    print(f"Updated data: {data}")

    return {"response": parsed.get("response", "")}


def travel_data_collected(state: AgentState):
    
    global data

    # Build conversation history
    history = "\n".join(
        [f"{msg.type.upper()}: {msg.content}" for msg in state["messages"] if hasattr(msg, "content")]
    )
    
    
    # LLM Prompt  
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
    print(f"LLM Raw Output: {raw_result}")

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
    
    
    # ----------------------
    # 2nd API
    # ----------------------
    
    
    
    
    
    

    print(f"Updated data: {data}")
    return {"response": parsed.get("response", "")}


def out_of_domain_tool(state: AgentState):
        # Build conversation history
    msgs = [m for m in state["messages"] if hasattr(m, "content")]
    last_message = msgs[-1].content.lower().strip() if msgs else ""
    last_five = "\n".join(m.content for m in msgs[-5:])

    prompt = f"""
    Analyze this conversation to determine the correct travel assistant response.

    Current context:
    - Last message: "{last_message}"

    Last 5 messages:
    {last_five}

    CRITICAL DECISION RULES:
    1. Given the current context and conversation, you have been called because you could not determine the correct tool to use. Analyse what user is trying to say and respond appropriately, and accordingly.
    2. Also from the last five messages, try to understand the context of the conversation.
    3. If the user is asking for something related to travel booking, trip details, or trip cancellation, respond with a relevant message guiding them to use the appropriate tool.
    4. If the user is asking for something completely unrelated to travel, politely inform them that you can only assist with travel-related queries.

    Return ONLY the response to the user.
    """
    
    response = llm.invoke(prompt)
    llm_response = response.content.strip() if hasattr(response, "content") else str(response).strip()
    
    print(f"Response: {llm_response}")
    return {"response": llm_response}


# --- 3. Tool Registry ---
TOOL_REGISTRY: Dict[str, Callable] = {
    "Travel Request": new_travel_request,
    "Travel Data": travel_data_collected,
    "Out of Scope": out_of_domain_tool
}

# Updated Function Descriptions
FUNCTION_DESCRIPTIONS = {
    "Travel Request": (
        "Call this function if in the data we don't have the employee_id field"
        "ONLY call this when user explicitly wants to book/create/start a NEW trip. "
        "Examples: 'book a trip', 'I want to travel', 'plan new journey', 'create booking'. "
        "If User says 8 digit employee id"
    ),
    "Travel Data": (
        "CONTINUE collecting travel details for an existing booking request. "
        "ONLY use this when Employee ID already exists AND user is providing travel details. "
        "Examples: User provides dates, cities, purpose, times after Employee ID was captured. "
        "Keep calling this until ALL travel details are collected. "
        "DO NOT use for new booking requests or cancellations."
    ),
    "Out of Scope": (
        "If you are not able to undestand the user's request then call this function."
    ),
}

# --- 4. Initialize LLM ---
llm = AzureChatOpenAI(
    azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version="2024-10-01-preview",
    deployment_name="gpt-4o-sohit"
)

# --- 5. Define the Nodes ---
def select_tool(state: AgentState):
    """Choose the single best tool using active context + conversation analysis."""    
    # Build conversation history
    msgs = [m for m in state["messages"] if hasattr(m, "content")]
    last_message = msgs[-1].content.lower().strip() if msgs else ""
    last_five = "\n".join(m.content for m in msgs[-5:])
    
    
    # PRIORITY 3: Analyze user intent for new requests
    prompt = f"""
You are an expert travel assistant tool selector. Your task is to perform comprehensive analysis to determine the most appropriate tool for the current conversation context.

CONVERSATION DATA:
{data}

AVAILABLE TOOLS:
{TOOL_REGISTRY}

DETAILED TOOL DESCRIPTIONS:
{FUNCTION_DESCRIPTIONS}

CONVERSATION CONTEXT ANALYSIS:
Current Message: "{last_message}"

Recent Conversation History (CRITICAL - Analyze thoroughly):
{last_five}

IMPORTANT RULES:
- If the user input is exactly 8 digits (e.g., "12345678"), select 'Travel Request' to capture the employee ID.
- If the user provides a travel purpose (e.g., 'R&D Project', 'Business Meeting', 'Training', etc.) and an employee ID is already present, select 'Travel Data' to continue collecting travel details.
- If the user provides a valid booking method (e.g., 'Self Booked', 'Company Booked', 'Others') and an employee ID is already present, select 'Travel Data'.
- If the user provides a cost center (a 6-digit integer, e.g., '607402') and/or a project WBS (an alphanumeric code, e.g., 'ADRG.25IT.DG.GE.A01') and an employee ID is already present, select 'Travel Data'.
- Only select 'Out of Scope' if the message is completely unrelated to travel or cannot be understood.

EXAMPLES:
- Input: "607402 and ADRG.25IT.DG.GE.A01" (with employee ID present) → select 'Travel Data'
- Input: "Self Booked" (with employee ID present) → select 'Travel Data'
- Input: "R&D Project" (with employee ID present) → select 'Travel Data'

DEEP ANALYSIS FRAMEWORK:
1. CONVERSATION FLOW ANALYSIS:
   - Examine the progression of the last 5 messages carefully
   - Identify the user's evolving intent and requirements
   - Note any contextual shifts or clarifications in recent exchanges
   - Determine if the conversation is continuing a previous topic or starting new

2. TOOL DESCRIPTION EVALUATION:
   - Study each tool's capabilities, limitations, and intended use cases
   - Match tool functionalities against the specific user requirements
   - Consider which tool best addresses the user's current need state
   - Evaluate tool appropriateness based on conversation complexity

3. CONTEXTUAL DECISION FACTORS:
   - User's immediate request vs. underlying travel needs
   - Conversation stage (planning, booking, modification, inquiry)
   - Required data inputs and expected outputs
   - Tool dependencies and workflow continuity

4. CRITICAL SELECTION CRITERIA:
   - Does the tool directly address the user's current question/request?
   - Is this tool the most efficient path to resolution?
   - Will this tool maintain conversation flow and user experience?
   - Does the recent conversation history suggest a specific tool preference?

DECISION PROCESS:
1. First, thoroughly analyze the last 5 messages for context and intent
2. Cross-reference this analysis with detailed tool descriptions
3. Identify the tool that best matches both immediate needs and conversation trajectory
4. Validate your selection against the conversation's natural progression

SELECTION REQUIREMENTS:
- Select EXACTLY ONE tool name from the registry
- Base decision primarily on the last 5 messages context
- Ensure tool capabilities align with user's demonstrated needs
- Consider conversation continuity and logical flow

Your response must contain ONLY the selected tool name.
"""
    
    response = llm.invoke(prompt)
    selected_tool = response.content.strip() if hasattr(response, "content") else str(response).strip()
    
    # Clean up tool name
    selected_tool = selected_tool.replace('"', '').replace("'", "").strip()
    
    # Validate tool name
    if selected_tool not in TOOL_REGISTRY:
        selected_tool = "Out of Scope"
    
    print(f"Selected tool: {selected_tool}")
    return {"selected_tool": selected_tool}

def call_selected_tool(state: AgentState):
    """Dynamically call the selected tool with correct args (state or text)."""
    selected_tool = state.get("selected_tool", "out_of_domain_tool")
    user_input = state["messages"][-1].content
    print(f"Calling {selected_tool} with input: {user_input}")

    tool_function = TOOL_REGISTRY.get(selected_tool, TOOL_REGISTRY["Out of Scope"])

    try:
        sig = inspect.signature(tool_function)
        params = list(sig.parameters.values())

        # 0 params -> call with no args
        if len(params) == 0:
            result = tool_function()
        # 1 param -> state if named 'state', else pass user_input
        elif len(params) == 1:
            if params[0].name == "state":
                result = tool_function(state)
            else:
                result = tool_function(user_input)
        # 2+ params -> prefer (state, user_input) if names look like that; else just pass state
        else:
            names = [p.name for p in params]
            if "state" in names and ("text" in names or "query" in names or "message" in names):
                # e.g., def tool(state, text): ...
                result = tool_function(state=state, text=user_input) if "text" in names else tool_function(state=state, query=user_input)
            elif "state" in names:
                result = tool_function(state)
            else:
                result = tool_function(user_input)
    except Exception as e:
        result = {"error": f"Tool {selected_tool} failed with error: {str(e)}"}

    print(f"Tool result: {result}")
    return {"result": result}

# --- 6. Define the Graph ---
workflow = StateGraph(AgentState)

workflow.add_node("select_tool", select_tool)
workflow.add_node("call_tool", call_selected_tool)

workflow.set_entry_point("select_tool")

workflow.add_edge("select_tool", "call_tool")
workflow.add_edge("call_tool", END)

app_graph = workflow.compile()

# --- 7. FastAPI App ---
app = FastAPI()

class Query(BaseModel):
    query: str

@app.post("/agent")
async def run_agent(query: Query):
    inputs = {"messages": [HumanMessage(content=query.query)]}
    final_state = app_graph.invoke(inputs)
    
    return {
        "result": final_state.get("result", None)
    }