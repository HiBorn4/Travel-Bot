import chainlit as cl
from main2 import chain, get_memory, CITY_MAP, TRAVEL_PURPOSES
from handle_responses import (
    handle_new_travel_request,
    handle_travel_data_collected,
    handle_json_ready,
    handle_trip_details,
    handle_trip_cancel,
    handle_default_response
)

# Globals for state
pernr = None
employee_details = None
city_code = None

@cl.on_chat_start
async def start_chat():
    await cl.Message(
        "👋 Hi, I'm your travel request assistant. You can:\n\n"
        "• Create a new travel request\n"
        "• View your existing trip details\n"
        "• Cancel a trip\n\n"
        "Type your request to begin."
    ).send()

    # We are loading CITY_MAP and TRAVEL_PURPOSES in background for prompt context only.
    # Nothing is printed in the UI.


@cl.on_message
async def on_message(msg: cl.Message):
    global pernr, employee_details, city_code
    user_input = msg.content.strip()
    session_id = cl.user_session.get("id", "default")

    try:
        response = await chain.ainvoke(
            {"input": user_input},
            config={"configurable": {"session_id": session_id}}
        )
        content = response.content.strip()

        # Handle response tags
        if content.startswith("<NEW_TRAVEL_REQUEST>"):
            content, pernr, employee_details = handle_new_travel_request(content)
            if content:
                await cl.Message(content).send()
            else:
                pass
            return

        elif content.startswith("<TRAVEL_DATA_COLLECTED>"):
            await cl.Message("🛂 Validating travel request...").send()
            content, city_code = handle_travel_data_collected(content, pernr)
            if content:
                await cl.Message(content).send()
            else:
                pass
            return

        elif content.startswith("JSON_READY:"):
            print('----------------')
            print("I GOT JSON_READY")
            print(content)
            print('----------------')
            try:
                handle_json_ready(content, city_code, employee_details)
                await cl.Message("✅ Travel request JSON submitted successfully.").send()
            except Exception as e:
                await cl.Message(f"❌ Failed to parse travel request JSON: {e}").send()
            return

        elif content.startswith("<TRIP_DETAILS>"):
            content = handle_trip_details(content)
            if content:
                await cl.Message(content).send()
            return

        elif content.startswith("<TRIP_CANCEL>"):
            content = handle_trip_cancel(content)
            if content:
                await cl.Message(content).send()
            return

        # Fallback
        content = handle_default_response(content)
        await cl.Message(content).send()

    except Exception as e:
        await cl.Message(f"❌ Backend error: {str(e)}").send()
