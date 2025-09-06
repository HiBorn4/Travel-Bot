import os, json, asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Body, Header
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_openai import AzureChatOpenAI
from dotenv import load_dotenv
from main import data

load_dotenv()

from main import llm

session_holder = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    params = StdioServerParameters(command="python", args=["main.py"])
    async with stdio_client(params) as (read, write):
        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()
        session_holder["s"] = session
        yield
        await session.__aexit__(None, None, None)
        session_holder.clear()

app = FastAPI(lifespan=lifespan)

@app.post("/chat")
async def chat(
    query: str = Body(..., media_type="text/plain"),
    history: str = Header(default="", alias="X-History")
) -> str:
    session: ClientSession = session_holder.get("s")
    if not session:
        raise HTTPException(500, "MCP session not ready")

    print("\n[DEBUG] /chat endpoint called")
    print(f"[DEBUG] User query: {query}")
    print(f"[DEBUG] History (last 10 turns): {history[-10:]}")
    print(f"[DEBUG] Current data: {json.dumps(data, indent=2)}")

    tools = await session.list_tools()
    desc = "\n".join(f"- {t.name}: {t.description}" for t in tools.tools)
    print(f"[DEBUG] Available tools:\n{desc}")

    # ---- build context-aware prompt ----
    prompt = f"""
        You are the **router** for a travel-assistant MCP server.

        Available tools:
        {desc}          ← already contains name + doc-string

        Current state:
        {json.dumps(data, indent=2)}

        Last 10 turns:
        {history[-10:]}

        User:
        {query}

        
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

        Output **exactly** one of:
        - JSON to call tool: {{"tool": "name", "arguments": {{...}}}}
        - Plain text to answer directly.
        """
    print(f"[DEBUG] Prompt sent to LLM:\n{prompt}")

    raw = llm.invoke(prompt).content.strip()
    print(f"[DEBUG] LLM raw output: {raw}")

    try:
        call = json.loads(raw)
        print(f"[DEBUG] Tool to be called: {call.get('tool')}")
        print(f"[DEBUG] Arguments for tool: {call.get('arguments')}")
        # Patch: Ensure arguments is a dict
        if isinstance(call.get("arguments"), str):
            # Map tool name to expected argument key
            tool_arg_keys = {
                "new_travel_request": "user_query",
                "travel_data_collected": "messages",
                # Add more tool mappings as needed
            }
            tool_name = call.get("tool")
            arg_key = tool_arg_keys.get(tool_name, "input")
            call["arguments"] = {arg_key: call["arguments"]}
        result = await session.call_tool(call["tool"], call["arguments"])
        print(f"[DEBUG] Tool result: {result.content[0].text}")
        print(f"[DEBUG] Data after tool call: {json.dumps(data, indent=2)}")
        return result.content[0].text
    except Exception as e:
        print(f"[ERROR] Exception in tool call or parsing: {e}")
        print(f"[DEBUG] Returning raw LLM output")
        return raw

@app.get("/health")
def health():
    print("[DEBUG] /health endpoint called")
    return "ok"