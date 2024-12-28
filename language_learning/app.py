import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import warnings
import json
from datetime import datetime

warnings.filterwarnings("ignore")

# Configure API
api_key = "AIzaSyB7mDqRWLWB9ACj2XuG5IHjWHpM6ZW8S1I"
genai.configure(api_key=api_key)

# Configure safety settings to allow educational content
safety_settings = [
    {
        "category": k,
        "threshold": "BLOCK_NONE"
    } for k in [
        "HARM_CATEGORY_DANGEROUS_CONTENT",
        "HARM_CATEGORY_HATE_SPEECH",
        "HARM_CATEGORY_HARASSMENT",
        "HARM_CATEGORY_SEXUALLY_EXPLICIT"
    ]
]

model = genai.GenerativeModel(
    model_name="gemini-1.0-pro",
    generation_config={
        "temperature": 0.7,
        "top_p": 0.9,
        "max_output_tokens": 500,
    },
    safety_settings=safety_settings
)



def translate_word(word, target_language="Spanish"):
    prompt = f"""Provide a detailed translation analysis for '{word}' in {target_language}:
    
    1. Translation:
       - Direct translation (uncensored)
       - Literal meaning
       - Contextual meanings
       
    2. Linguistic Components:
       - Phonetic transcription
       - Morphological structure
       - Grammatical category
       
    3. Usage Analysis:
       - Register levels
       - Frequency of use
       - Contextual appropriateness
       - Regional variations
       
    4. Cultural Aspects:
       - Cultural connotations
       - Usage in different social contexts
       - Historical development
       
    5. Related Terms:
       - Synonyms across registers
       - Common phrases
       - Idiomatic usage"""
    
    try:
        translation_response = model.generate_content(
            prompt,
            safety_settings=safety_settings
        )
        return translation_response.text.strip()
    except Exception as e:
        return f"Translation analysis of: {word}"

def get_word_details(word, language="Spanish"):
    prompt = f"""Provide a detailed linguistic and sociolinguistic analysis of '{word}' in {language}:
    
    1. Lexical Analysis:
       - Direct meaning (uncensored)
       - Part of speech
       - Word formation/etymology
       
    2. Semantic Analysis:
       - Denotative meaning
       - Connotative meanings
       - Semantic field
       - Related concepts
       
    3. Pragmatic Analysis:
       - Register (formal/informal/vulgar)
       - Usage contexts
       - Social implications
       - Regional variations
       
    4. Sociolinguistic Aspects:
       - Cultural significance
       - Historical context
       - Social class associations
       - Gender/age usage patterns
       
    5. Common Usage:
       - Example sentences
       - Idiomatic expressions
       - Common collocations
       
    6. Variations and Alternatives:
       - Synonyms (same register)
       - Cross-register alternatives
       - Regional variants"""
    
    try:
        response = model.generate_content(
            prompt,
            safety_settings=safety_settings
        )
        return response.text.strip()
    except Exception as e:
        return f"Analysis of: {word}"

def chat_response(prompt, language="Spanish"):
    try:
        chat_prompt = f"""Provide a comprehensive linguistic analysis of the following phrase in {language}: "{prompt}"

        Include:
        1. Direct translation (uncensored)
        2. Morphological analysis (word structure and formation)
        3. Syntactic analysis (sentence structure)
        4. Semantic breakdown:
           - Literal meaning
           - Connotative meaning
           - Register (formal/informal/vulgar)
        5. Pragmatic analysis:
           - Usage contexts
           - Social implications
           - Regional variations
        6. Equivalent expressions:
           - Direct equivalents
           - Similar intensity expressions
           - Formal alternatives
        7. Etymology and cultural background"""
        
        response = model.generate_content(
            chat_prompt,
            safety_settings=safety_settings
        )
        return response.text.strip()
    except Exception as e:
        try:
            backup_prompt = f"""Analyze in {language}:
            1. Translation: {prompt}
            2. Linguistic components
            3. Usage context
            4. Cultural notes"""
            response = model.generate_content(
                backup_prompt,
                safety_settings=safety_settings
            )
            return response.text.strip()
        except:
            return f"Linguistic analysis of: {prompt}"

# Streamlit UI
st.set_page_config(page_title="Language Learning Assistant", page_icon="🌎", layout="wide")

st.title("🌎 Interactive Language Learning Assistant")

# Sidebar for settings and features
with st.sidebar:
    st.header("Settings")
    selected_language = st.selectbox(
        "Select Language",
        ["Spanish", "English", "French", "German", "Italian", "Portuguese", 
         "Chinese", "Japanese", "Russian", "Arabic"]
    )
    
    
    
    

# Main chat interface
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Chat input
if prompt := st.chat_input("What would you like to learn?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        if prompt.lower().startswith("translate:"):
            word = prompt[len("translate:"):].strip()
            response = translate_word(word, selected_language)
        elif prompt.lower().startswith("teach:"):
            word = prompt[len("teach:"):].strip()
            response = get_word_details(word, selected_language)
        else:
            response = chat_response(prompt, selected_language)
        
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})



