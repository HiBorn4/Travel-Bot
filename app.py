# app.py
import chainlit as cl
import requests
import json

API = "http://localhost:8000"

def clean_response(answer: str) -> str:
    """
    Cleans backend responses:
    - If valid JSON with "response", return that.
    - If JSON has "travel_details" + "response", return just the response.
    - If it's double-encoded JSON (string containing JSON), parse again.
    - Otherwise, return raw text.
    """
    cleaned = answer

    try:
        parsed = json.loads(answer)

        # Case 1: JSON dict with response
        if isinstance(parsed, dict) and "response" in parsed:
            cleaned = parsed["response"]

        # Case 2: Double-encoded JSON string
        elif isinstance(parsed, str):
            try:
                parsed2 = json.loads(parsed)
                if isinstance(parsed2, dict) and "response" in parsed2:
                    cleaned = parsed2["response"]
                else:
                    cleaned = parsed
            except Exception:
                cleaned = parsed
    except Exception:
        cleaned = answer

    return cleaned.strip('"').strip()

@cl.on_chat_start
async def start_chat():
    await cl.Message(
        content="👋 Hello! I’m your Travel Assistant. Please provide your 8-digit Employee ID to get started.",
        author="Assistant",
        avatar="🤖"
    ).send()

@cl.on_message
async def handle_message(message: cl.Message):
    user_input = message.content

    # Show user message with avatar
    await cl.Message(content=user_input, author="You", avatar="👤").send()

    try:
        reply = requests.post(
            f"{API}/chat",
            data=user_input.encode(),
            headers={"content-type": "text/plain"},
            timeout=30,
        )
        answer = reply.text if reply.ok else f"⚠️ {reply.text}"
    except Exception as e:
        answer = f"⚠️ Error: {e}"

    # --- Clean the response ---
    cleaned_answer = clean_response(answer)

    # Send assistant reply with avatar
    await cl.Message(
        content=cleaned_answer,
        author="Assistant",
        avatar="🤖"
    ).send()
