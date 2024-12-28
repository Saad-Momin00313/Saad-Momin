import streamlit as st
import google.generativeai as genai
from dotenv import load_dotenv
import warnings
import json
from datetime import datetime
import random

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

# Function to save chat history
def save_chat_history(messages, language):
    try:
        # Use a single file for all chat history
        filename = "chat_database.json"
        
        # Load existing chat history or create new
        try:
            with open(filename, "r", encoding="utf-8") as f:
                all_chats = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            all_chats = {"chats": []}
        
        # Add new chat session with timestamp
        chat_session = {
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "language": language,
            "messages": messages
        }
        
        all_chats["chats"].append(chat_session)
        
        # Save updated chat history
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(all_chats, f, ensure_ascii=False, indent=2)
        
        return filename
    except Exception as e:
        st.error(f"Error saving chat history: {str(e)}")
        return None

# Function to load chat history
def load_chat_history():
    try:
        filename = "chat_database.json"
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"chats": []}
    except Exception as e:
        st.error(f"Error loading chat history: {str(e)}")
        return {"chats": []}

# Function to generate practice questions
def generate_practice_test(language, test_type="Comprehensive", test_length=20, difficulty="Mixed"):
    try:
        # Create language-specific prompts
        language_contexts = {
            "Spanish": {
                "Vocabulary": ["hola", "gracias", "por favor", "buenos días"],
                "Grammar": ["ser vs estar", "present tense", "past tense", "subjunctive"],
                "Cultural": ["Spain", "Mexico", "Argentina", "Latin America"],
                "Beginner": "basic greetings, numbers, colors",
                "Intermediate": "daily conversations, past tense, future plans",
                "Advanced": "subjunctive mood, idiomatic expressions, complex topics"
            }
        }

        # Get language context or use Spanish as default
        lang_context = language_contexts.get(language, language_contexts["Spanish"])
        
        prompt = f"""You are a {language} language teacher creating a test.
        Create {test_length} UNIQUE questions for a {difficulty.lower()} level {test_type.lower()} test.
        Each question must be different - DO NOT repeat questions or concepts.

        Question requirements:
        1. Write each question in both {language} AND English
        2. For vocabulary: focus on common words, phrases, and usage
        3. For grammar: test {lang_context['Grammar']}
        4. For cultural: include {lang_context['Cultural']}
        5. Match {difficulty} level: {lang_context[difficulty]}
        6. Make questions progressively harder
        7. Cover different topics and concepts

        Format EXACTLY as follows:
        {{
            "questions": [
                {{
                    "question": "¿Cómo se dice 'hello' en español? (How do you say 'hello' in Spanish?)",
                    "options": [
                        "A) Hola (Hello)",
                        "B) Adiós (Goodbye)",
                        "C) Gracias (Thank you)",
                        "D) Por favor (Please)"
                    ],
                    "correct_answer": "A) Hola (Hello)",
                    "explanation": "Hola is the most common greeting in Spanish, used in both formal and informal situations."
                }}
            ]
        }}

        Make sure:
        1. ALL text is in both languages (questions, options, explanations)
        2. Questions are appropriate for {difficulty} level
        3. Include real-world examples and contexts
        4. Provide cultural notes where relevant
        5. Give clear, educational explanations
        6. EVERY question must be unique - no repetition

        Return ONLY the JSON object with {test_length} questions."""

        # Generate test using AI
        response = model.generate_content(prompt, safety_settings=safety_settings)
        
        # Clean up the response text
        response_text = response.text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        try:
            # Parse JSON with error handling
            test_data = json.loads(response_text)
            
            # Validate structure
            if "questions" not in test_data:
                raise ValueError("Missing questions array in response")
            
            # Ensure we have the right number of questions
            if len(test_data["questions"]) < test_length:
                # Generate additional questions if needed
                additional_prompt = f"Generate {test_length - len(test_data['questions'])} more UNIQUE questions following the same format."
                additional_response = model.generate_content(additional_prompt, safety_settings=safety_settings)
                additional_text = additional_response.text.strip()
                if additional_text.startswith("```json"):
                    additional_text = additional_text[7:]
                if additional_text.endswith("```"):
                    additional_text = additional_text[:-3]
                additional_text = additional_text.strip()
                
                try:
                    additional_data = json.loads(additional_text)
                    if "questions" in additional_data:
                        test_data["questions"].extend(additional_data["questions"])
                except:
                    pass
            
            # Truncate if too many questions
            test_data["questions"] = test_data["questions"][:test_length]
            
            # Verify uniqueness
            seen_questions = set()
            unique_questions = []
            for q in test_data["questions"]:
                q_text = q["question"].lower()
                if q_text not in seen_questions:
                    seen_questions.add(q_text)
                    unique_questions.append(q)
            
            test_data["questions"] = unique_questions
            
            return test_data
            
        except json.JSONDecodeError as e:
            st.error(f"Error generating test questions. Please try again.")
            return None
            
    except Exception as e:
        st.error(f"Error in test generation: {str(e)}")
        return None

# Function to analyze learning progress
def analyze_learning_progress(chat_history, language):
    try:
        content = " ".join([msg["content"] for msg in chat_history])
        
        prompt = f"""Analyze this language learning session in {language}:
        
        Chat history: "{content}"
        
        Provide:
        1. Most frequently discussed topics
        2. Vocabulary level (beginner/intermediate/advanced)
        3. Grammar points covered
        4. Suggested areas for improvement
        5. Recommended next topics to study"""
        
        response = model.generate_content(prompt, safety_settings=safety_settings)
        return response.text.strip()
    except Exception as e:
        return f"Error analyzing progress: {str(e)}"

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
       - Idiomatic usage
    
    Provide complete linguistic information without filtering."""
    
    try:
        translation_response = model.generate_content(
            prompt,
            safety_settings=[
                {"category": k, "threshold": "BLOCK_NONE"} 
                for k in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HATE_SPEECH", 
                         "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]
            ]
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
       - Regional variants
    
    Format as an academic analysis. Include all information without filtering."""
    
    try:
        response = model.generate_content(
            prompt,
            safety_settings=[
                {"category": k, "threshold": "BLOCK_NONE"} 
                for k in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HATE_SPEECH", 
                         "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]
            ]
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
        7. Etymology and cultural background
        
        Format as a clear, academic analysis. This is for educational purposes - provide complete information without filtering."""
        
        response = model.generate_content(
            chat_prompt,
            safety_settings=[
                {"category": k, "threshold": "BLOCK_NONE"} 
                for k in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HATE_SPEECH", 
                         "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]
            ]
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
                safety_settings=[
                    {"category": k, "threshold": "BLOCK_NONE"} 
                    for k in ["HARM_CATEGORY_DANGEROUS_CONTENT", "HARM_CATEGORY_HATE_SPEECH", 
                             "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_SEXUALLY_EXPLICIT"]
                ]
            )
            return response.text.strip()
        except:
            return f"Linguistic analysis of: {prompt}"

# Streamlit UI
st.set_page_config(page_title="Language Learning Assistant", page_icon="🌎", layout="wide")

# Create tabs
tab1, tab2, tab3 = st.tabs(["💬 Chat", "📝 Practice Tests", "📊 Progress"])

# Chat Tab
with tab1:
    st.title("🌎 Interactive Language Learning Assistant")
    
    # Sidebar for settings and features
    with st.sidebar:
        st.header("Settings")
        selected_language = st.selectbox(
            "Select Language",
            ["Spanish", "English", "French", "German", "Italian", "Portuguese", 
             "Chinese", "Japanese", "Russian", "Arabic"]
        )
        
        st.markdown("""
        ### How to use:
        1. Chat naturally with the bot
        2. Use "Translate:" prefix for translations
        3. Use "Teach:" prefix for detailed word explanations
        
        Example:
        - "How do you say hello?"
        - "Translate: hello"
        - "Teach: hola"
        """)
        
        if st.button("Save Chat History"):
            if "messages" in st.session_state and len(st.session_state.messages) > 0:
                filename = save_chat_history(st.session_state.messages, selected_language)
                if filename:
                    st.success(f"Chat history saved to {filename}")
    
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

    # Quick Translation Tool
    st.divider()
    with st.expander("Quick Translation Tool"):
        col1, col2 = st.columns(2)
        with col1:
            quick_word = st.text_input("Enter a word to translate:")
        with col2:
            if st.button("Translate") and quick_word:
                st.write(translate_word(quick_word, selected_language))

# Practice Tests Tab
with tab3:
    st.title("📝 Language Practice Tests")
    
    # Test types
    test_type = st.selectbox(
        "Select Test Type",
        ["Vocabulary", "Grammar", "Cultural Knowledge", "Comprehensive", "Custom"]
    )
    
    # Test settings
    col1, col2 = st.columns(2)
    with col1:
        test_length = st.slider("Number of Questions", 10, 50, 20)
        difficulty = st.select_slider(
            "Difficulty Level",
            options=["Beginner", "Intermediate", "Advanced", "Mixed"]
        )
    
    with col2:
        if test_type == "Custom":
            vocab_ratio = st.slider("Vocabulary Questions %", 0, 100, 40)
            grammar_ratio = st.slider("Grammar Questions %", 0, 100, 40)
            cultural_ratio = st.slider("Cultural Questions %", 0, 100, 20)
    
    # Generate test button
    if st.button("Generate New Test"):
        with st.spinner("Generating test..."):
            test_data = generate_practice_test(
                language=selected_language,
                test_type=test_type,
                test_length=test_length,
                difficulty=difficulty
            )
            if test_data and "questions" in test_data and len(test_data["questions"]) > 0:
                st.session_state.current_test = test_data
                st.session_state.test_score = 0
                st.session_state.current_question = 0
                st.rerun()
            else:
                st.error("Failed to generate test questions. Please try again with different settings.")
                if "current_test" in st.session_state:
                    del st.session_state.current_test
                if "current_question" in st.session_state:
                    del st.session_state.current_question
                st.stop()

    # Display current test
    if "current_test" in st.session_state and "current_question" in st.session_state:
        test = st.session_state.current_test
        if test and "questions" in test and len(test["questions"]) > 0 and st.session_state.current_question < len(test["questions"]):
            st.divider()
            question = test["questions"][st.session_state.current_question]
            
            # Question header
            st.markdown(f"""
            ### Question {st.session_state.current_question + 1} of {len(test['questions'])}
            
            {question['question']}
            """)
            
            # Create columns for layout
            col1, col2 = st.columns([2, 1])
            
            with col1:
                # Display options in a more engaging way
                selected_answer = st.radio(
                    "Choose your answer:",
                    question["options"],
                    key=f"q_{st.session_state.current_question}",
                    index=None,
                    help="Select one option and click 'Submit Answer'"
                )
                
                # Submit button and feedback
                if st.button("Submit Answer", key=f"submit_{st.session_state.current_question}", 
                            use_container_width=True, type="primary"):
                    if selected_answer:
                        if selected_answer == question["correct_answer"]:
                            st.session_state.test_score += 1
                            st.success("✅ Correct!")
                            st.info(question["explanation"])
                        else:
                            st.error("❌ Incorrect!")
                            st.warning(f"The correct answer is: {question['correct_answer']}")
                            st.info(question["explanation"])
                        
                        # Progress to next question
                        st.session_state.current_question += 1
                        if st.session_state.current_question >= len(test["questions"]):
                            st.balloons()
                            st.success(f"""
                            # 🎉 Test Completed!
                            
                            Your final score: {st.session_state.test_score}/{len(test['questions'])}
                            ({(st.session_state.test_score/len(test['questions'])*100):.1f}%)
                            """)
                            
                            # Save test results
                            result_message = f"""Test Results:
                            - Score: {st.session_state.test_score}/{len(test['questions'])}
                            - Percentage: {(st.session_state.test_score/len(test['questions'])*100):.1f}%
                            - Test Type: {test_type}
                            - Difficulty: {difficulty}
                            - Language: {selected_language}"""
                            st.session_state.messages.append({"role": "system", "content": result_message})
                            
                            # Clear test state
                            if st.button("Start New Test", type="primary"):
                                del st.session_state.current_test
                                del st.session_state.current_question
                                st.rerun()
                        else:
                            st.rerun()
                    else:
                        st.warning("Please select an answer before submitting.")
            
            with col2:
                # Progress section
                st.markdown("### Progress")
                progress = st.session_state.current_question / len(test["questions"])
                st.progress(progress)
                
                # Score display
                st.metric(
                    "Current Score",
                    f"{st.session_state.test_score}/{st.session_state.current_question}",
                    f"{(st.session_state.test_score/max(1, st.session_state.current_question)*100):.1f}%"
                )
                
                # Exit button
                if st.button("Exit Test", type="secondary", use_container_width=True):
                    if st.session_state.current_question > 0:
                        result_message = f"""Partial Test Results:
                        - Score: {st.session_state.test_score}/{st.session_state.current_question}
                        - Percentage: {(st.session_state.test_score/st.session_state.current_question*100):.1f}%
                        - Test Type: {test_type}
                        - Difficulty: {difficulty}
                        - Language: {selected_language}
                        - Status: Incomplete"""
                        st.session_state.messages.append({"role": "system", "content": result_message})
                    del st.session_state.current_test
                    del st.session_state.current_question
                    st.rerun()

# Progress Tab
with tab3:
    st.title("📊 Learning Progress")
    
    # Load and display chat history
    chat_history = load_chat_history()
    
    # Display chat sessions
    if chat_history["chats"]:
        st.subheader("Chat History")
        for session in reversed(chat_history["chats"]):  # Show newest first
            with st.expander(f"Session: {session['timestamp']} - {session['language']}"):
                for msg in session["messages"]:
                    if msg["role"] == "user":
                        st.markdown(f"**You:** {msg['content']}")
                    elif msg["role"] == "assistant":
                        st.markdown(f"**Assistant:** {msg['content']}")
                    elif msg["role"] == "system":
                        if "Test Results" in msg["content"]:
                            st.markdown(f"**📝 {msg['content']}**")
    else:
        st.info("No chat history available yet. Start chatting to see your progress!")
    
    # Analyze progress button
    if st.button("Analyze Progress"):
        if "messages" in st.session_state and len(st.session_state.messages) > 0:
            analysis = analyze_learning_progress(st.session_state.messages, selected_language)
            st.session_state.progress_analysis = analysis
    
    # Display current analysis
    if "progress_analysis" in st.session_state:
        st.subheader("Current Session Analysis")
        st.write(st.session_state.progress_analysis)
        if st.button("Clear Analysis"):
            del st.session_state.progress_analysis
    
    # Display test history
    if "messages" in st.session_state:
        test_results = [msg for msg in st.session_state.messages if msg["role"] == "system" and "Test Results" in msg["content"]]
        if test_results:
            st.subheader("Recent Test Results")
            for result in test_results:
                st.markdown(result["content"])

# Footer
st.markdown("---")
st.markdown("Made with ❤️ for language learners") 