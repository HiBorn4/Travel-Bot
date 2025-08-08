# backend_debug.py
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import os
import tempfile
import mimetypes
import json
import base64
import logging
import traceback
import time
from dotenv import load_dotenv
from pdf2image import convert_from_path
from utils import prompt_food, prompt_hotel, prompt_travel
from langchain_openai import AzureChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from PIL import Image

# -------------------------
# Logging / Debug setup
# -------------------------
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(message)s"
logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)
logger = logging.getLogger("reimbursement_debug")

# -------------------------
# Load env and create LLM
# -------------------------
load_dotenv()
AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_OPENAI_VERSION = os.getenv("AZURE_OPENAI_VERSION", "2024-02-01")
AZURE_OPENAI_DEPLOYMENT = os.getenv("AZURE_OPENAI_DEPLOYMENT", "gpt-4o-mini")

logger.debug("Environment variables loaded.")
logger.debug("AZURE_OPENAI_ENDPOINT present? %s", bool(AZURE_OPENAI_ENDPOINT))
logger.debug("AZURE_OPENAI_API_KEY present? %s", bool(AZURE_OPENAI_API_KEY))
logger.debug("AZURE_OPENAI_VERSION = %s", AZURE_OPENAI_VERSION)
logger.debug("AZURE_OPENAI_DEPLOYMENT = %s", AZURE_OPENAI_DEPLOYMENT)

# Initialize LangChain client
llm = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version=AZURE_OPENAI_VERSION,
    deployment_name=AZURE_OPENAI_DEPLOYMENT,
    temperature=0.0,
    max_tokens=2000,
)

# -------------------------
# FastAPI app
# -------------------------
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class FinalResponse(BaseModel):
    reimbursement_type: Optional[str] = None
    extracted_data: Optional[dict] = None

# -------------------------
# Utility helpers
# -------------------------
def encode_image_to_base64(image_path: str) -> str:
    logger.debug("Encoding image to base64: %s", image_path)
    with open(image_path, "rb") as img_file:
        encoded = base64.b64encode(img_file.read()).decode("utf-8")
    logger.debug("Base64 encoding complete (length=%d)", len(encoded))
    return encoded

def convert_pdf_to_image(pdf_path: str) -> str:
    logger.debug("Converting PDF to image: %s", pdf_path)
    images = convert_from_path(pdf_path, dpi=200, first_page=1, last_page=1)
    image_path = pdf_path.replace(".pdf", "_page1.jpg")
    images[0].save(image_path, "JPEG")
    logger.debug("PDF converted to image: %s (size=%s)", image_path, os.path.getsize(image_path))
    return image_path

def get_image_path(file_path: str, mime_type: str) -> str:
    logger.debug("Determining image path for file: %s mime: %s", file_path, mime_type)
    if "pdf" in mime_type:
        return convert_pdf_to_image(file_path)
    elif any(x in mime_type for x in ["jpeg", "jpg", "png"]):
        return file_path
    else:
        raise ValueError("Unsupported file format: %s" % mime_type)

def get_image_mime_type(image_path: str) -> str:
    if image_path.lower().endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    elif image_path.lower().endswith(".png"):
        return "image/png"
    else:
        return "application/octet-stream"

def safe_parse_json(text: str) -> dict:
    """
    Try multiple strategies to parse JSON returned by LLM.
    """
    logger.debug("Attempting safe JSON parse. input length=%d", len(text) if text else 0)
    # Quick attempt
    try:
        return json.loads(text)
    except Exception as ex1:
        logger.debug("Direct json.loads failed: %s", ex1)

    # Extract first {...} block
    try:
        start = text.index("{")
        end = text.rindex("}") + 1
        candidate = text[start:end]
        logger.debug("Trying substring JSON parse (start=%d end=%d) length=%d", start, end, len(candidate))
        return json.loads(candidate)
    except Exception as ex2:
        logger.debug("Substring parse failed: %s", ex2)

    # Try replacing single quotes
    try:
        replaced = text.replace("'", '"')
        return json.loads(replaced)
    except Exception as ex3:
        logger.debug("Single-quote replacement parse failed: %s", ex3)

    # At this point, raise helpful error with context
    raise ValueError("Failed to parse LLM response as JSON. Errors: %s | %s | %s" % (ex1, ex2, ex3))

# -------------------------
# Endpoint with expanded debugging
# -------------------------
@app.post("/analyze_reimbursement", response_model=FinalResponse)
async def analyze_reimbursement(file: UploadFile = File(...)):
    start_time = time.time()
    logger.info("Request received: filename=%s content_type=%s", file.filename, file.content_type)

    # Write uploaded file to temp location
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=file.filename) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = tmp.name
        logger.debug("Saved upload to tmp_path=%s size=%d bytes", tmp_path, os.path.getsize(tmp_path))
    except Exception as e:
        logger.exception("Failed to write uploaded file to temporary file: %s", e)
        return FinalResponse(reimbursement_type=None, extracted_data={"error": "Failed to save uploaded file", "trace": str(e)})

    # Optimize and process the image
    try:
        # First determine mime type
        mime_type = mimetypes.guess_type(file.filename)[0] or file.content_type or "application/octet-stream"
        logger.debug("Guessed mime_type=%s for filename=%s", mime_type, file.filename)
        
        # Get the appropriate image path (convert PDF if needed)
        image_path = get_image_path(tmp_path, mime_type)
        logger.debug("Resolved image_path=%s size=%d bytes", image_path, os.path.getsize(image_path))

        # Optimize the image
        # optimized_path = optimize_image(image_path)
        optimized_path = image_path  # For now, use the original path
        logger.debug("Optimized image created: %s size=%d bytes", optimized_path, os.path.getsize(optimized_path))

        # Get image details
        with Image.open(optimized_path) as im:
            logger.debug("Optimized image: format=%s mode=%s size=%s", im.format, im.mode, im.size)

        # Encode to base64
        image_mime = get_image_mime_type(optimized_path)
        image_b64 = encode_image_to_base64(optimized_path)
        image_data_url = f"data:{image_mime};base64,{image_b64}"
        logger.debug("Built data URL (length=%d)", len(image_data_url))

    except Exception as e:
        logger.exception("Failed to process image: %s", e)
        # Clean up any created files
        for path in [tmp_path, image_path if 'image_path' in locals() else None, 
                    optimized_path if 'optimized_path' in locals() else None]:
            if path and os.path.exists(path):
                try:
                    os.remove(path)
                except Exception:
                    pass
        return FinalResponse(reimbursement_type=None, extracted_data={"error": "Image processing failed", "trace": str(e)})

    # Build safe prompt that won't trigger content filters
    try:
        system_prompt = f"""
You are a helpful document analysis assistant. Please:
1. Identify if this is a Hotel, Food, or Travel document
2. Extract the key details in JSON format

For Hotels, look for:
{prompt_hotel}

For Food receipts:
{prompt_food}

For Travel tickets:
{prompt_travel}

Return your analysis in given JSON format.
"""
        logger.debug("Using safe system prompt (length=%d)", len(system_prompt))
    except Exception as e:
        logger.exception("Prompt construction error: %s", e)
        return FinalResponse(reimbursement_type=None, extracted_data={"error": "Prompt construction failed", "trace": str(e)})

    # Prepare messages with optimized approach
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=[
            {"type": "text", "text": "Please analyze this reimbursement document"},
            {"type": "image_url", "image_url": {"url": image_data_url}}
        ])
    ]

    # LLM invocation with enhanced error handling
    llm_start = time.time()
    try:
        logger.info("Invoking LLM with deployment: %s", AZURE_OPENAI_DEPLOYMENT)
        response = llm.invoke(messages)
        llm_elapsed = time.time() - llm_start
        logger.info("LLM invocation completed (%.2fs)", llm_elapsed)
        
        # Process response
        raw_content = getattr(response, "content", "")
        logger.debug("LLM response (truncated): %s", raw_content[:500])

        # Parse with multiple fallback strategies
        try:
            parsed = safe_parse_json(raw_content)
            logger.debug("Parsed JSON keys: %s", list(parsed.keys()))
            
            # Normalize response structure
            reimbursement_type = parsed.get("type") or parsed.get("reimbursement_type")
            extracted_data = parsed.get("details") or parsed.get("extracted_data") or \
                           {k: v for k, v in parsed.items() if k not in ["type", "reimbursement_type"]}
            
            final_response = FinalResponse(
                reimbursement_type=reimbursement_type,
                extracted_data=extracted_data
            )
            
        except Exception as parse_error:
            logger.exception("JSON parsing failed: %s", parse_error)
            final_response = FinalResponse(
                reimbursement_type=None,
                extracted_data={
                    "error": "Response parsing failed",
                    "llm_response": raw_content[:2000],
                    "parse_error": str(parse_error)
                }
            )

    except Exception as llm_error:
        logger.exception("LLM invocation failed: %s", llm_error)
        final_response = FinalResponse(
            reimbursement_type=None,
            extracted_data={
                "error": "LLM processing failed",
                "error_type": str(type(llm_error)),
                "error_details": str(llm_error),
                "trace": traceback.format_exc()
            }
        )

    # Cleanup all temporary files
    cleanup_paths = [tmp_path, image_path, optimized_path]
    for path in cleanup_paths:
        if path and os.path.exists(path):
            try:
                os.remove(path)
                logger.debug("Removed temp file: %s", path)
            except Exception as e:
                logger.warning("Failed to remove temp file %s: %s", path, str(e))

    total_elapsed = time.time() - start_time
    logger.info("Request completed in %.2f seconds", total_elapsed)
    return final_response