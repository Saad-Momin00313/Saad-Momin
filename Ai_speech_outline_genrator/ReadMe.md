# AI Speech Outline Generator

## Overview
The AI Speech Outline Generator is a web application built using Streamlit that allows users to generate structured speech outlines based on various parameters. It utilizes Google's Gemini AI to create outlines tailored to specific topics, languages, tones, and audience types.

## Features
- Generate speech outlines with customizable parameters.
- Support for multiple languages with translations for structural elements.
- Options for tone, audience type, presentation style, and more.
- Downloadable text file of the generated outline.
- User-friendly interface with helpful tips for better speeches.

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd Ai_speech_outline_genrator
   ```

2. Install the required packages:
   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables:
   - Create a `.env` file in the root directory and add your Google API key:
     ```
     GOOGLE_API_KEY=your_api_key_here
     ```

4. Run the application:
   ```bash
   streamlit run app.py
   ```

## Input Parameters
The application accepts the following input parameters:

- **Topic**: The main subject of the speech (string).
- **Language**: The language in which the speech will be generated (string).
- **Tone**: The tone of the speech (e.g., Formal, Conversational) (string).
- **Sections**: The number of sections in the speech (integer).
- **Duration**: The total duration of the speech in minutes (integer).
- **Audience Type**: The target audience for the speech (string).
- **Presentation Style**: The style of presentation (string).
- **Purpose**: The goal of the speech (string).
- **Template**: The style of the outline template (string).
- **Word Limit**: The maximum number of words for the speech (integer).
- **Formatting Style**: The desired formatting style for the outline (string).
- **Topic Details**: Additional details about the topic (optional, string).

## Output
The application generates a speech outline based on the provided inputs. The output includes:

- A structured outline with key points, potential subtopics, suggested transitions, and closing recommendations.
- The generated outline is displayed on the web page and can be downloaded as a text file.

### Example Output
1. Title (in English)
2. Target Audience and Purpose Statement
3. Time Allocation per Section
4. For each section include:
Key Points
Potential Subtopics
Suggested Transitions
Estimated Time
Closing Recommendations
6. Visual Aid Suggestions
7. Engagement Techniques


## Usage
1. Open the application in your web browser.
2. Fill in the input fields with the desired parameters.
3. Click the "Generate Outline" button to create the speech outline.
4. Download the generated outline using the provided link.

## Tips for Better Speeches
- Keep your main points clear and concise.
- Use relevant examples and stories.
- Practice your timing for each section.
- Engage with your audience.
- Use appropriate gestures and body language.

## License
This project is licensed under the MIT License. See the LICENSE file for details.