import streamlit as st
import google.generativeai as genai
import os
from PIL import Image
import speech_recognition as sr  # For audio-to-text conversion
from pydub import AudioSegment  # For audio file conversion
import tempfile
from streamlit_mic_recorder import mic_recorder  # For recording audio

# Configure API Key (use environment variable or Streamlit secrets)
GENAI_API_KEY = os.getenv("GENAI_API_KEY") or st.secrets["GENAI_API_KEY"]
genai.configure(api_key=GENAI_API_KEY)

# Streamlit UI
st.title("AI Blog Generator using Streamlit & Gemini")

# User inputs
input_type = st.selectbox("Select Input Type", ["Text", "Image", "Audio", "Video"])

# Topic is optional for non-text inputs
if input_type == "Text":
    topic = st.text_input("Enter Blog Topic", placeholder="e.g., The Future of AI")
else:
    topic = None

tone = st.selectbox("Select Tone", ["Informative", "Casual", "Formal", "Storytelling"])
word_limit = st.slider("Word Limit", 100, 1000, 500)
model_name = st.selectbox("Select Model", ["gemini-2.0-flash", "gemini-pro-vision"])  # Use gemini-pro-vision for images
generate_btn = st.button("Generate Blog")

# Function to convert audio to WAV format
def convert_audio_to_wav(audio_file):
    try:
        # Save the uploaded file to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as tmp_file:
            tmp_file.write(audio_file.read())
            tmp_file_path = tmp_file.name

        # Convert to WAV format using pydub
        audio = AudioSegment.from_file(tmp_file_path)
        wav_file_path = tmp_file_path.replace(".mp3", ".wav")
        audio.export(wav_file_path, format="wav")
        return wav_file_path
    except Exception as e:
        st.error(f"Error converting audio file: {e}")
        return None

# Function to convert audio to text
def audio_to_text(audio_file):
    recognizer = sr.Recognizer()
    try:
        with sr.AudioFile(audio_file) as source:
            audio = recognizer.record(source)
            text = recognizer.recognize_google(audio)  # Use Google Speech-to-Text API
            return text
    except sr.UnknownValueError:
        return "Google Speech-to-Text could not understand the audio."
    except sr.RequestError as e:
        return f"Could not request results from Google Speech-to-Text; {e}"
    except Exception as e:
        return f"An error occurred during audio processing: {e}"

# File upload or audio recording based on input type
uploaded_file = None
transcribed_text = ""
if input_type == "Image":
    uploaded_file = st.file_uploader("Upload an Image", type=["jpg", "jpeg", "png"])
elif input_type == "Audio":
    # Option to upload or record audio
    audio_option = st.radio("Choose Audio Input Method", ["Upload Audio File", "Record Audio"])
    
    if audio_option == "Upload Audio File":
        uploaded_file = st.file_uploader("Upload an Audio File", type=["wav", "mp3"])
    else:
        # Record audio using the mic_recorder component
        st.write("Click the microphone to start recording:")
        recorded_audio = mic_recorder(start_prompt="Start recording", stop_prompt="Stop recording", key="recorder")
        if recorded_audio:
            # Save the recorded audio to a temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                tmp_file.write(recorded_audio['bytes'])
                uploaded_file = tmp_file.name
            st.audio(recorded_audio['bytes'], format="audio/wav")  # Play the recorded audio

    # Convert audio to text (for both uploaded and recorded audio)
    if uploaded_file:
        with st.spinner("Converting audio to text..."):
            if isinstance(uploaded_file, str):  # Recorded audio (temporary file path)
                audio_file_path = uploaded_file
            else:  # Uploaded audio file
                if uploaded_file.size > 10 * 1024 * 1024:  # 10 MB limit
                    st.error("Audio size exceeds the 10 MB limit. Please upload a smaller audio file.")
                else:
                    # Convert audio to WAV format (if it's an MP3 file)
                    if uploaded_file.name.endswith(".mp3"):
                        audio_file_path = convert_audio_to_wav(uploaded_file)
                    else:
                        # For WAV files, save directly
                        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp_file:
                            tmp_file.write(uploaded_file.read())
                            audio_file_path = tmp_file.name
            
            if audio_file_path:
                # Convert audio to text
                transcribed_text = audio_to_text(audio_file_path)
                st.write("Transcribed Text:")
                transcribed_text = st.text_area("Edit Transcribed Text", transcribed_text, height=200)
elif input_type == "Video":
    uploaded_file = st.file_uploader("Upload a Video File", type=["mp4", "mov"])

# Function to generate blog
def generate_blog(topic, tone, word_limit, model_name, input_type, uploaded_file=None, transcribed_text=""):
    prompt = f"Write a {tone.lower()} blog in {word_limit} words."
    if topic:
        prompt += f" The topic is '{topic}'."
    if transcribed_text:
        prompt += f" The following text was transcribed from an audio file: {transcribed_text}"
    
    try:
        model = genai.GenerativeModel(model_name)
        
        # Handle different input types
        if input_type == "Text":
            response = model.generate_content(prompt)
        elif input_type == "Image" and uploaded_file is not None:
            # Validate image size
            if uploaded_file.size > 20 * 1024 * 1024:  # 20 MB limit
                return "Image size exceeds the 20 MB limit. Please upload a smaller image."
            image = Image.open(uploaded_file)
            response = model.generate_content([prompt, image])
        elif input_type == "Audio" and transcribed_text:
            response = model.generate_content(prompt)
        elif input_type == "Video" and uploaded_file is not None:
            # Validate video size
            if uploaded_file.size > 50 * 1024 * 1024:  # 50 MB limit
                return "Video size exceeds the 50 MB limit. Please upload a smaller video file."
            response = model.generate_content([prompt, uploaded_file.read()])
        else:
            return "Please upload a file or record audio for the selected input type."
        
        return response.text
    except Exception as e:
        return f"An error occurred: {str(e)}"

# Generate and display blog
if generate_btn:
    if input_type == "Text" and not topic.strip():
        st.error("Please enter a blog topic.")
    else:
        with st.spinner("Generating blog..."):
            blog_content = generate_blog(topic, tone, word_limit, model_name, input_type, uploaded_file, transcribed_text)
            st.subheader("Generated Blog")
            st.markdown(blog_content)