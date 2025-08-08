import streamlit as st
import requests
import json

# Page config
st.set_page_config(page_title="Reimbursement Extractor", layout="centered")

# Title and description
st.title("📄 Reimbursement Extractor (PDF/Image)")
st.write("Upload a hotel, food, or travel bill (PDF/image) to classify and extract structured information.")

# File uploader
uploaded_file = st.file_uploader("Upload your file", type=["pdf", "png", "jpg", "jpeg"])

# Store uploaded file in session for reuse
if uploaded_file:
    st.session_state["uploaded_file"] = uploaded_file

# Resend and process button
if "uploaded_file" in st.session_state:
    if st.button("📤 Process / Resend File"):
        with st.spinner("Processing your document..."):
            uploaded_file = st.session_state["uploaded_file"]
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}

            try:
                # Call the API
                response = requests.post("http://localhost:8000/analyze_reimbursement", files=files)
                # Ensure the response is successful before attempting to parse
                response.raise_for_status() 
                
                # Directly display the JSON response as it is expected to be a valid object now
                st.subheader("📑 API Response")
                st.json(response.json())

                # Optionally, if you still want to display specific fields
                # result = response.json()
                # st.success(f"✅ Reimbursement Type: {result.get('reimbursement_type', 'N/A')}")
                # st.subheader("📑 Extracted Data")
                # st.json(result.get("extracted_data", {}))

            except requests.exceptions.RequestException as e:
                st.error(f"❌ API Error: {str(e)}")
            except json.JSONDecodeError:
                st.error("❌ Invalid JSON response from server. Check backend logs.")
            except Exception as e:
                st.error(f"❌ Unexpected error: {str(e)}")
