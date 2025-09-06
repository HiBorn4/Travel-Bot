import chainlit as cl
import httpx
import json
import asyncio
from typing import Optional

# FastAPI endpoint
FASTAPI_URL = "http://localhost:8001/agent"

class TravelAssistant:
    """Travel booking assistant client."""
    
    def __init__(self):
        self.session_data = {}
    
    async def send_query(self, query: str) -> str:
        """Send query to FastAPI backend."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    FASTAPI_URL,
                    json={"query": query},
                    timeout=30.0
                )
                response.raise_for_status()
                result = response.json()
                
                # Extract response from nested structure
                travel_response = result.get("result", {})
                return travel_response.get("response", str(travel_response))
                
        except httpx.HTTPError as e:
            return f"❌ Connection error: {str(e)}"
        except Exception as e:
            return f"❌ Unexpected error: {str(e)}"

# Initialize travel assistant
travel_assistant = TravelAssistant()

@cl.on_chat_start
async def start():
    """Initialize chat session."""
    await cl.Message(
        content="🧳 **Welcome to Travel Booking Assistant!**\n\n"
                "I can help you book your travel. To get started:\n"
                "1. Provide your 8-digit employee ID\n"
                "2. Share your travel details (purpose, destination, dates)\n"
                "3. I'll guide you through the booking process\n\n"
                "What's your employee ID?",
        author="Travel Assistant"
    ).send()

@cl.on_message
async def handle_message(message: cl.Message):
    """Process user messages."""
    user_query = message.content.strip()
    
    # Show typing indicator
    async with cl.Step(name="Processing", type="tool") as step:
        step.output = "Contacting travel service..."
        
        # Get response from FastAPI backend
        response = await travel_assistant.send_query(user_query)
        
        step.output = f"Query: {user_query}\nResponse: {response}"
    
    # Send response to user
    await cl.Message(
        content=response,
        author="Travel Assistant"
    ).send()

@cl.on_stop
async def stop():
    """Handle session stop."""
    await cl.Message(
        content="👋 Thank you for using Travel Booking Assistant!",
        author="Travel Assistant"
    ).send()