# ----------  main.py  ----------
import contextlib, warnings, asyncio, json, re
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, Body, Header, HTTPException
from google.adk.agents import LlmAgent
from google.adk.runners import Runner, RunConfig
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioConnectionParams
from google.genai import types
from mcp import StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.session import ClientSession
import logging

# ----------  config ----------
load_dotenv()
warnings.filterwarnings("ignore", message=".*auth_config.*")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI()
SESSION_SVC = InMemorySessionService()
FLOW_MD = Path(__file__).with_name("flow.md").read_text(encoding="utf-8")

# Single global session data - no session management needed
current_data = { 
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
    "reimburse_percentage": 100 
}

# Single ADK session
adk_session = None

# ----------  Lifelong MCP bridge ----------
async def _mcp_bridge_lifespan():
    params = StdioServerParameters(command="python", args=["server.py"])
    async with stdio_client(params) as (read, write):
        session = ClientSession(read, write)
        async with session:
            await session.initialize()
            app.state.mcp_session = session
            logger.info("[MCP] Bridge ready")
            await asyncio.Event().wait()

@app.on_event("startup")
async def startup():
    global adk_session
    
    app.state.mcp_bridge_task = asyncio.create_task(_mcp_bridge_lifespan())
    while not hasattr(app.state, "mcp_session"):
        await asyncio.sleep(0.1)

    toolset = MCPToolset(
        connection_params=StdioConnectionParams(
            server_params=StdioServerParameters(command="python", args=["server.py"]),
            timeout=60,
        ),
    )

    agent = LlmAgent(
        model="gemini-2.5-pro",
        name="travel_agent",
        instruction=FLOW_MD,
        tools=[toolset],
    )

    app.state.runner = Runner(
        app_name="travel_bot",
        agent=agent,
        session_service=SESSION_SVC,
    )

    # Create single ADK session at startup
    adk_session = await SESSION_SVC.create_session(
        state=current_data,
        app_name="travel_bot",
        user_id="user_fs"
    )
    logger.info("Single ADK session created")

@app.on_event("shutdown")
async def shutdown():
    app.state.mcp_bridge_task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await app.state.mcp_bridge_task

# ----------  Chat ----------
@app.post("/chat")
async def chat(
    query: str = Body(..., media_type="text/plain"),
    session_id: str = Header(None),  # Ignored - keeping for API compatibility
):
    global current_data, adk_session
    runner = app.state.runner

    prompt = f"""USER QUERY: {query}

CURRENT TRAVEL DATA (PRESERVE ALL NON-EMPTY VALUES):
{json.dumps(current_data, indent=2)}

CRITICAL INSTRUCTION: You MUST include ALL existing non-empty field values in your travel_data response. Never send empty strings for fields that already have values.
"""
    content = types.Content(role="user", parts=[types.Part(text=prompt)])

    texts = []
    async for event in runner.run_async(
        session_id=adk_session.id,
        user_id=adk_session.user_id,
        new_message=content,
        run_config=RunConfig(),
    ):
        if event.content and event.content.parts:
            texts.extend(p.text for p in event.content.parts if p.text)

    raw = " ".join(texts)
    logger.info("LLM raw: %s", raw)

    try:                                                  # strip ```json â€¦ ```
        llm = json.loads(re.sub(r"^```[a-zA-Z]*\n?|\n?```$", "", raw.strip()))
    except Exception:
        llm = {}
    
    logger.info(("Previous data:", current_data))

    # Only copy LLM travel_data if it exists in the response
    llm_travel_data = llm.get("travel_data", {})
    
    if llm_travel_data:  # Only update if LLM returned travel_data
        # Iterate through LLM travel_data and copy only non-empty values to current_data
        for key, value in llm_travel_data.items():
            # Only update if the new value is not empty (for strings) or is a meaningful number
            if isinstance(value, str):
                if value.strip():  # Only update if string is not empty/whitespace
                    current_data[key] = value
            else:
                # For non-string values (numbers, etc.), always update
                current_data[key] = value
        logger.info("Updated data with non-empty LLM travel_data values")
    else:
        logger.info("No travel_data in LLM response - preserving existing data")

    logger.info(("Updated data:", current_data))

    return {
        "response": llm.get("response", ""),
        "session_id": "1",  # Always return same session ID
        "current_state": current_data,
    }

@app.get("/session/1")
async def get_session():
    """Get current session state"""
    return {"session_id": "1", "state": current_data}

@app.delete("/session/1")
async def reset_session():
    """Reset the global session data"""
    global current_data
    current_data = { 
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
        "reimburse_percentage": 100 
    }
    logger.info("Session data reset to initial values")
    return {"status": "session reset"}

@app.get("/health")
def health():
    return {"status": "ok"}