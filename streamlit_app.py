import streamlit as st
import os
import time
import google.generativeai as genai
import tempfile

# Set page configuration
st.set_page_config(page_title="Gemini PDF Chat", layout="wide")

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None
if "uploaded_file" not in st.session_state:
    st.session_state.uploaded_file = None

# Sidebar for API key input
with st.sidebar:
    api_key = st.text_input("Enter your Gemini API Key:", type="password")
    if api_key:
        os.environ["GEMINI_API_KEY"] = api_key
        genai.configure(api_key=api_key)

def upload_to_gemini(file_path, mime_type=None):
    """Uploads the given file to Gemini."""
    file = genai.upload_file(file_path, mime_type=mime_type)
    return file

def wait_for_files_active(files):
    """Waits for the given files to be active."""
    for name in (file.name for file in files):
        file = genai.get_file(name)
        while file.state.name == "PROCESSING":
            time.sleep(1)
            file = genai.get_file(name)
        if file.state.name != "ACTIVE":
            raise Exception(f"File {file.name} failed to process")

# Main interface
st.title("📄 Gemini PDF Chat")

# File uploader
uploaded_file = st.file_uploader("Upload your PDF", type=['pdf'])

if uploaded_file is not None and api_key:
    # Create a temporary file to save the uploaded content
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
        tmp_file.write(uploaded_file.getvalue())
        tmp_file_path = tmp_file.name

    # Initialize chat session if not exists or if new file is uploaded
    if st.session_state.chat_session is None:
        try:
            # Configure Gemini model
            generation_config = {
                "temperature": 1,
                "top_p": 0.95,
                "top_k": 40,
                "max_output_tokens": 8192,
                "response_mime_type": "text/plain",
            }

            model = genai.GenerativeModel(
                model_name="gemini-1.5-pro",
                generation_config=generation_config,
            )

            # Upload file to Gemini
            file = upload_to_gemini(tmp_file_path, mime_type="application/pdf")
            wait_for_files_active([file])

            # Start chat session
            st.session_state.chat_session = model.start_chat(history=[])
            st.session_state.uploaded_file = file
            st.session_state.messages = []  # Reset messages for new file

            # Clean up temporary file
            os.unlink(tmp_file_path)

        except Exception as e:
            st.error(f"Error initializing chat: {str(e)}")
            if os.path.exists(tmp_file_path):
                os.unlink(tmp_file_path)

    # Chat interface
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input("Ask something about the PDF..."):
        # Add user message
        st.chat_message("user").markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt})

        try:
            # Get response from Gemini
            response = st.session_state.chat_session.send_message([
                st.session_state.uploaded_file,
                prompt
            ])

            # Display assistant response
            with st.chat_message("assistant"):
                st.markdown(response.text)
            st.session_state.messages.append({"role": "assistant", "content": response.text})

        except Exception as e:
            st.error(f"Error getting response: {str(e)}")

elif not api_key:
    st.warning("Please enter your Gemini API key in the sidebar.")
else:
    st.info("Please upload a PDF file to start chatting.")

# Add a button to clear chat history
if st.button("Clear Chat History"):
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.uploaded_file = None
    st.rerun()
