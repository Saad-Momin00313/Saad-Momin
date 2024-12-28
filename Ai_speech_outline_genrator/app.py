import streamlit as st
import google.generativeai as genai
import os
import io
import base64
from dotenv import load_dotenv 
# Load environment variables from .env file
load_dotenv()

# Initialize Gemini AI client using the environment variable
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-pro')

def generate_speech_outline(topic, language, tone, sections, duration, audience_type, presentation_style, purpose, template, word_limit, formatting_style, topic_details=None):
    """
    Generate a speech outline using Gemini AI with enhanced parameters
    """
    # Dictionary for translations of structural elements
    translations = {
        "French": {
            "key_points": "Points Clés",
            "potential_subtopics": "Sous-thèmes Potentiels",
            "suggested_transitions": "Transitions Suggérées",
            "closing_recommendations": "Recommandations Finales"
        },
        "Spanish": {
            "key_points": "Puntos Clave",
            "potential_subtopics": "Subtemas Potenciales",
            "suggested_transitions": "Transiciones Sugeridas",
            "closing_recommendations": "Recomendaciones Finales"
        },
        "German": {
            "key_points": "Hauptpunkte",
            "potential_subtopics": "Mögliche Unterthemen",
            "suggested_transitions": "Vorgeschlagene Übergänge",
            "closing_recommendations": "Abschließende Empfehlungen"
        },
        "Mandarin": {
            "key_points": "要点",
            "potential_subtopics": "潜在子主题",
            "suggested_transitions": "建议过渡",
            "closing_recommendations": "结束建议"
        },
        "Japanese": {
            "key_points": "主要ポイント",
            "potential_subtopics": "考えられるサブトピック",
            "suggested_transitions": "推奨される移行",
            "closing_recommendations": "最終提案"
        },
        "Korean": {
            "key_points": "주요 포인트",
            "potential_subtopics": "잠재적 하위 주제",
            "suggested_transitions": "제안된 전환",
            "closing_recommendations": "마무리 권장사항"
        },
        "Italian": {
            "key_points": "Punti Chiave",
            "potential_subtopics": "Possibili Sottotemi",
            "suggested_transitions": "Transizioni Suggerite",
            "closing_recommendations": "Raccomandazioni Finali"
        },
        "Portuguese": {
            "key_points": "Pontos-Chave",
            "potential_subtopics": "Subtópicos Potenciais",
            "suggested_transitions": "Transições Sugeridas",
            "closing_recommendations": "Recomendações Finais"
        },
        "Russian": {
            "key_points": "Ключевые Моменты",
            "potential_subtopics": "Возможные Подтемы",
            "suggested_transitions": "Предлагаемые Переходы",
            "closing_recommendations": "Заключительные Рекомендации"
        },
        "Arabic": {
            "key_points": "النقاط الرئيسية",
            "potential_subtopics": "المواضيع الفرعية المحتملة",
            "suggested_transitions": "الانتقالات المقترحة",
            "closing_recommendations": "التوصيات الختامية"
        },
        "Hindi": {
            "key_points": "मुख्य बिंदु",
            "potential_subtopics": "संभावित उप-विषय",
            "suggested_transitions": "सुझाए गए संक्रमण",
            "closing_recommendations": "समापन सिफारिशें"
        },
        "Turkish": {
            "key_points": "Ana Noktalar",
            "potential_subtopics": "Olası Alt Konular",
            "suggested_transitions": "Önerilen Geçişler",
            "closing_recommendations": "Kapanış Önerileri"
        },
        "English": {
            "key_points": "Key Points",
            "potential_subtopics": "Potential Subtopics",
            "suggested_transitions": "Suggested Transitions",
            "closing_recommendations": "Closing Recommendations"
        }
    }

    # Get translations for the selected language
    lang_trans = translations.get(language, translations["English"])

    prompt = f"""Create a speech outline with the following specifications:
    - Topic: {topic}
    - Strict Language: {language} (Please ensure ALL text, including section headers and structural elements, is in {language})
    - Tone: {tone}
    - Number of Sections: {sections}
    - Speech Duration: {duration} minutes
    - Target Audience: {audience_type}
    - Presentation Style: {presentation_style}
    - Purpose/Goal: {purpose}
    - Word Limit: {word_limit} words
    - Formatting Style: {formatting_style}
    {f'- Additional Details: {topic_details}' if topic_details else ''}
    {f'- Template Style: {template}' if template != 'Standard' else ''}

    Outline Structure:
    1. Title (in {language})
    2. Target Audience and Purpose Statement
    3. Time Allocation per Section
    4. For each section include:
       - {lang_trans["key_points"]}
       - {lang_trans["potential_subtopics"]}
       - {lang_trans["suggested_transitions"]}
       - Estimated Time
    5. {lang_trans["closing_recommendations"]}
    6. Visual Aid Suggestions
    7. Engagement Techniques

    Important: 
    - Ensure that ALL text, including section headers, structural elements, and content is in {language}
    - Keep within the {word_limit} word limit
    - Format according to the {formatting_style} style
    - Include time markers for each section to total {duration} minutes"""

    try:
        response = model.generate_content([
            {"role": "user", "parts": [f"You are an expert speech and content outline generator. Always respond entirely in {language}.\n\n{prompt}"]}
        ])
        return response.text
    except Exception as e:
        return f"An error occurred: {str(e)}"

def get_download_link(content, filename):
    """
    Generate a download link for the text file
    """
    # Encode the content as UTF-8 bytes
    text_bytes = content.encode('utf-8')
    b64 = base64.b64encode(text_bytes).decode()
    return f'<a href="data:text/plain;charset=utf-8;base64,{b64}" download="{filename}">Download Text File</a>'

def main():
    st.set_page_config(page_title="AI Speech Outline Generator", page_icon="🎤", layout="wide")
    
    st.title("🎤 AI Speech Outline Generator")
    
    # Create two columns for better layout
    col1, col2 = st.columns(2)
    
    with col1:
        # Basic Parameters
        topic = st.text_input("What is the topic of your speech?", 
                            placeholder="Enter your speech topic")
        
        topic_details = st.text_area("Additional Topic Details (Optional)", 
                                    placeholder="Enter any specific details, context, or focus areas for your topic")
        
        language = st.selectbox("Select Language", 
                                ["English", "Spanish", "French", "German", "Mandarin", 
                                 "Japanese", "Korean", "Italian", "Portuguese", "Russian",
                                 "Arabic", "Hindi", "Turkish"])
        
        tone = st.selectbox("Select Tone", 
                            ["Formal", "Conversational", "Inspirational", 
                             "Academic", "Persuasive", "Technical", "Humorous",
                             "Professional", "Motivational"])
    
    with col2:
        # Enhanced Parameters
        duration = st.slider("Speech Duration (minutes)", 
                           min_value=5, max_value=60, value=15, step=5)
        
        audience_type = st.selectbox("Target Audience",
                                   ["General Public", "Professional", "Academic",
                                    "Technical", "Students", "Executives",
                                    "Mixed Audience", "Industry Specific"])
        
        presentation_style = st.selectbox("Presentation Style",
                                        ["Traditional", "Interactive",
                                         "Story-based", "Data-driven",
                                         "Workshop Style", "Q&A Format"])
        
        purpose = st.selectbox("Speech Purpose",
                             ["Inform", "Persuade", "Motivate",
                              "Educate", "Entertain", "Call to Action"])
    
    # Advanced Options Expander
    with st.expander("Advanced Options"):
        col3, col4 = st.columns(2)
        
        with col3:
            sections = st.slider("Number of Sections", 
                               min_value=3, max_value=10, value=5)
            
            template = st.selectbox("Template Style",
                                  ["Standard", "Problem-Solution",
                                   "Chronological", "Compare-Contrast",
                                   "Cause-Effect", "Process Analysis"])
        
        with col4:
            word_limit = st.select_slider("Word Limit",
                                        options=[500, 750, 1000, 1500, 2000, 2500, 3000],
                                        value=1500)
            
            formatting_style = st.selectbox("Formatting Style",
                                          ["Standard", "Bullet Points",
                                           "Numbered Lists", "Hierarchical",
                                           "Mind Map Style"])
    
    # Generate Button
    if st.button("Generate Outline", type="primary"):
        if topic:
            with st.spinner("Generating your speech outline..."):
                outline = generate_speech_outline(
                    topic, language, tone, sections, duration,
                    audience_type, presentation_style, purpose,
                    template, word_limit, formatting_style, topic_details
                )
                
                st.write("### 📝 Generated Speech Outline")
                st.markdown(outline)
                
                # Create download options
                st.markdown("### 📥 Download Options")
                filename = f"speech_outline_{topic.lower().replace(' ', '_')}.txt"
                st.markdown(get_download_link(outline, filename), unsafe_allow_html=True)
                
                # Display speech statistics
                st.markdown("### 📊 Speech Statistics")
                word_count = len(outline.split())
                st.info(f"""
                - Estimated Word Count: {word_count}
                - Estimated Speaking Time: {duration} minutes
                - Number of Sections: {sections}
                """)
        else:
            st.warning("Please enter a topic for your speech.")
    
    # Add helpful tips in the sidebar
    st.sidebar.title("💡 Tips for Better Speeches")
    st.sidebar.markdown("""
    - Keep your main points clear and concise
    - Use relevant examples and stories
    - Practice your timing for each section
    - Engage with your audience
    - Use appropriate gestures and body language
    """)

if __name__ == "__main__":
    main()