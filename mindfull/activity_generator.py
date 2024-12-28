import google.generativeai as genai
from datetime import datetime
from typing import Dict
from config import logger, GEMINI_API_KEY, BASE_CATEGORIES
from database import Database

class MindfulnessActivityGenerator:
    def __init__(self):
        genai.configure(api_key=GEMINI_API_KEY)
        self.safety_settings = [
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            }
        ]
        self.model = genai.GenerativeModel('gemini-pro', safety_settings=self.safety_settings)
        self.db = Database()
        self.base_categories = BASE_CATEGORIES

    def generate_personalized_activity(self, user_profile: Dict, mood: str = None, energy_level: int = None, 
                                     stress_level: int = None, time_available: int = None, interests: list = None) -> Dict:
        """Generate a personalized mindfulness activity using AI."""
        try:
            current_hour = datetime.now().hour
            time_context = (
                "morning" if 5 <= current_hour < 12
                else "afternoon" if 12 <= current_hour < 17
                else "evening" if 17 <= current_hour < 22
                else "night"
            )

            # Use parameters from user_profile if not provided directly
            mood = mood or user_profile.get('mood', 'Neutral')
            energy_level = energy_level or user_profile.get('energy_level', 5)
            stress_level = stress_level or user_profile.get('stress_level', 5)
            time_available = time_available or user_profile.get('time_available', 10)
            interests = interests or user_profile.get('interests', ['Meditation'])

            prompt = f"""
            Generate a detailed mindfulness activity for {time_context} that is:
            - Tailored for current mood: {mood}
            - Energy level consideration: {energy_level}/10
            - Safe and evidence-based
            - Appropriate for stress level: {stress_level}/10
            - Duration: {time_available} minutes
            - Incorporating interests: {', '.join(interests)}
            
            Format the response as a step-by-step guide with:
            1. A clear title
            2. Duration
            3. Numbered steps
            4. Expected benefits
            
            Keep the steps clear, concise, and easy to follow.
            """

            response = self.model.generate_content(prompt)
            if response.text:
                return self._parse_activity_response(response.text)
            return self._fallback_activity()
            
        except Exception as e:
            logger.error(f"Error generating personalized activity: {str(e)}")
            return self._fallback_activity()

    def _parse_activity_response(self, response_text: str) -> Dict:
        """Parse the AI response into a structured format."""
        try:
            # Default structure
            activity = {
                'category': 'Personalized Practice',
                'duration': 10,
                'text': '',
                'steps': [],
                'benefits': []
            }
            
            # Clean and format the response
            lines = response_text.strip().split('\n')
            current_section = None
            formatted_text = []
            steps = []
            benefits = []
            
            for line in lines:
                line = line.strip()
                if not line:
                    continue
                    
                if line.lower().startswith('step') or line[0].isdigit():
                    steps.append(line)
                elif line.lower().startswith('benefit'):
                    benefits.append(line)
                else:
                    formatted_text.append(line)
            
            # Ensure we have at least some steps
            if not steps:
                steps = [
                    "1. Find a comfortable position",
                    "2. Take deep breaths",
                    "3. Focus on your breath",
                    "4. Observe your thoughts without judgment",
                    "5. Gently return focus to your breath"
                ]
            
            # Format the final text with proper list handling
            formatted_steps = "\n".join(steps)
            default_benefits = ["- Reduced stress", "- Improved focus", "- Better emotional balance"]
            formatted_benefits = "\n".join(benefits if benefits else default_benefits)
            
            activity['text'] = f"STEPS:\n{formatted_steps}\n\nBENEFITS:\n{formatted_benefits}"
            
            return activity
            
        except Exception as e:
            logger.error(f"Error parsing activity response: {str(e)}")
            return self._fallback_activity()

    def _fallback_activity(self) -> Dict:
        """Return a default activity if generation fails."""
        return {
            'category': 'Basic Meditation',
            'duration': 10,
            'text': """STEPS:
1. Find a comfortable seated position
2. Close your eyes and take three deep breaths
3. Focus on your natural breathing pattern
4. When your mind wanders, gently return to your breath
5. Continue for the remaining time
6. Slowly open your eyes when ready

BENEFITS:
- Reduced stress and anxiety
- Improved focus and clarity
- Better emotional regulation
- Enhanced self-awareness"""
        }

    def generate_progress_insights(self, stats: Dict, mood_data: Dict, practice_data: list) -> str:
        """Generate personalized insights using AI based on user's progress data."""
        try:
            # Get user's goals
            goals = self.db.get_practice_goals(stats.get('user_id')) or {
                'daily_goal': 10,
                'weekly_goal': 70,
                'focus_areas': [],
                'difficulty_level': 'Beginner'
            }
            
            # Calculate goal completion rates
            daily_completion = (stats.get('minutes_today', 0) / goals['daily_goal']) * 100
            weekly_completion = (stats.get('minutes_this_week', 0) / goals['weekly_goal']) * 100
            
            # Analyze practice patterns
            practice_times = []
            for date, minutes in practice_data:
                try:
                    dt = datetime.strptime(date, "%Y-%m-%d")
                    practice_times.append(dt)
                except (ValueError, TypeError):
                    continue
            
            preferred_times = []
            if practice_times:
                hours = [t.hour for t in practice_times]
                from collections import Counter
                time_counter = Counter(hours)
                preferred_times = [f"{h}:00" for h, _ in time_counter.most_common(3)]
            
            prompt = f"""
            You are an expert mindfulness and meditation coach analyzing this practitioner's data.
            
            Progress Data:
            - Total Lifetime Practice: {stats.get('total_minutes', 0)} minutes
            - Current Streak: {stats.get('current_streak', 0)} days
            - Daily Goal Progress: {daily_completion:.1f}%
            - Weekly Goal Progress: {weekly_completion:.1f}%
            - Focus Areas: {goals.get('focus_areas', [])}
            - Preferred Practice Times: {preferred_times}
            - Current Level: {goals.get('difficulty_level', 'Beginner')}
            
            Mood Data:
            {mood_data.get('summary', 'No mood data available')}
            
            Please provide a comprehensive analysis in these sections:
            1. 🎯 Goal Progress Analysis
            2. 🌟 Key Achievements
            3. 🧠 Impact on Wellbeing
            4. 💡 Personalized Recommendations
            5. 🌱 Growth Opportunities
            6. 🎉 Next Level Milestone
            
            Format in clear markdown with emoji indicators.
            Base insights strictly on their data.
            Include specific recommendations for reaching their goals.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating insights: {str(e)}")
            return self._fallback_insights()

    def _fallback_insights(self) -> str:
        """Generate fallback insights when data is limited."""
        return """
        # 🌟 Begin Your Mindfulness Journey

        I notice you're just starting your mindfulness practice - that's wonderful! 
        Every expert practitioner began exactly where you are now.
        
        ## 🎯 Next Steps
        1. Start with short daily practices
        2. Track your sessions regularly
        3. Notice how you feel before and after
        
        ## 💡 Quick Tip
        Consistency matters more than duration when starting.
        Focus on making meditation a regular part of your day.
        
        ## 🌱 Remember
        Every moment of practice is an investment in your wellbeing.
        Let's build this transformative habit together! 🙏
        """

    def generate_daily_recommendation(self, user_profile: Dict, time_of_day: str) -> str:
        """Generate personalized daily practice recommendation based on time of day and user data."""
        try:
            # Get user's practice goals and progress
            goals = self.db.get_practice_goals(user_profile.get('user_id')) or {
                'daily_goal': 10,
                'weekly_goal': 70,
                'focus_areas': [],
                'difficulty_level': 'Beginner'
            }
            progress = self.db.get_user_stats(user_profile.get('user_id'))
            
            # Calculate remaining daily and weekly goals
            now = datetime.now()
            daily_remaining = goals['daily_goal'] - progress.get('minutes_today', 0)
            weekly_remaining = goals['weekly_goal'] - progress.get('minutes_this_week', 0)
            
            # Get user's routines for recommendations
            user_routines = self.db.get_user_routines(user_profile.get('user_id'))
            recent_routines = [r for r in user_routines if r['last_practiced']]
            recent_routines.sort(key=lambda x: x['last_practiced'], reverse=True)

            prompt = f"""
            As an expert mindfulness coach, provide a personalized practice recommendation.
            
            Context:
            - Time of day: {time_of_day}
            - User's current stress level: {user_profile.get('stress_level', 'Moderate')}
            - Daily goal remaining: {daily_remaining} minutes
            - Weekly goal remaining: {weekly_remaining} minutes
            - Focus areas: {goals.get('focus_areas', [])}
            - Difficulty level: {goals.get('difficulty_level', 'Beginner')}
            - Previous practice duration: {user_profile.get('avg_duration', '10')} minutes
            - Interests: {user_profile.get('interests', ['Meditation'])}
            
            Additional Context:
            - User has {len(user_routines)} custom routines
            - Most recent practice: {recent_routines[0]['name'] if recent_routines else 'None'}
            
            Please provide:
            1. A specific practice recommendation for this time of day
            2. How this practice aligns with their goals
            3. Expected benefits based on their focus areas
            4. Tips for optimal practice
            5. Suggestion for a custom routine if applicable
            
            Format the response in a clear, engaging way with emoji indicators.
            Keep it concise but informative.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating daily recommendation: {str(e)}")
            return "Unable to generate recommendation at this time."

    def generate_sleep_recommendation(self, sleep_quality: str, stress_level: int) -> str:
        """Generate personalized bedtime mindfulness practice."""
        try:
            prompt = f"""
            As a mindfulness and sleep expert, provide a personalized evening practice.
            
            Context:
            - Recent sleep quality: {sleep_quality}
            - Current stress level: {stress_level}/10
            
            Please provide:
            1. A specific 5-10 minute bedtime mindfulness routine
            2. How it helps with sleep quality
            3. Tips for maintaining good sleep hygiene
            4. When to practice it before bed
            
            Format as a clear, step-by-step guide with relevant emojis.
            Focus on practical, science-backed techniques.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            logger.error(f"Error generating sleep recommendation: {str(e)}")
            return "Unable to generate sleep recommendation at this time."

    def generate_stress_relief_practice(self, stress_trigger: str, stress_level: int) -> str:
        """Generate immediate stress relief practice based on trigger and level."""
        try:
            # Check for critical keywords indicating emergency situations
            emergency_keywords = {
                'abuse': {
                    'message': """🚨 IMPORTANT: If you're experiencing abuse, your safety is the top priority.

EMERGENCY RESOURCES:
1. Emergency Services: Call 911 if you're in immediate danger
2. National Domestic Violence Hotline: 1-800-799-SAFE (7233)
3. Crisis Text Line: Text HOME to 741741
4. National Sexual Assault Hotline: 1-800-656-HOPE (4673)

These services are:
- Available 24/7
- Confidential
- Staffed by trained professionals
- Free to use

Please reach out for help. You don't have to face this alone."""
                },
                'suicide': {
                    'message': """🚨 IMMEDIATE ACTION NEEDED:

If you're having thoughts of suicide, please reach out for help immediately:

1. National Suicide Prevention Lifeline: 988 or 1-800-273-8255
2. Crisis Text Line: Text HOME to 741741
3. Emergency Services: Call 911

You are not alone. Help is available 24/7, and people care about you.
Please talk to someone right now."""
                },
                'heart': {
                    'message': """�� MEDICAL EMERGENCY WARNING:

If you're experiencing:
- Chest pain or pressure
- Difficulty breathing
- Severe dizziness
- Other concerning physical symptoms

TAKE IMMEDIATE ACTION:
1. Call 911 or your local emergency number
2. If available, take aspirin (if advised by emergency services)
3. Try to stay calm and seated/lying down
4. If alone, try to alert a neighbor or nearby person

Do not delay seeking medical help. Minutes matter in heart-related emergencies."""
                }
            }

            # Check if the stress trigger contains any emergency keywords
            for keyword, info in emergency_keywords.items():
                if keyword in stress_trigger.lower():
                    prompt = f"""
                    As a mindfulness expert with crisis management training, provide:
                    
                    1. First acknowledge the seriousness of the situation
                    2. Provide immediate grounding techniques that can be used alongside professional help
                    3. Emphasize the importance of seeking professional support
                    4. Offer gentle coping strategies for use after getting professional help
                    
                    Context:
                    - Situation: {stress_trigger}
                    - Current stress level: {stress_level}/10
                    
                    Start the response with this exact emergency message:
                    {info['message']}
                    
                    Then provide gentle support techniques.
                    Keep the tone supportive and empowering while emphasizing the importance of professional help.
                    """
                    
                    response = self.model.generate_content(prompt)
                    return response.text

            # For non-emergency situations, proceed with regular stress relief
            prompt = f"""
            As a stress management expert, provide an immediate mindfulness intervention.
            
            Context:
            - Stress trigger: {stress_trigger}
            - Current stress level: {stress_level}/10
            
            Please provide:
            1. A quick (2-5 minute) stress relief technique
            2. Why this technique works for this type of stress
            3. How to implement it in any setting
            4. Follow-up practices for longer-term stress management
            
            Format as an easy-to-follow guide with calming language.
            Focus on immediate relief while building long-term resilience.
            """
            
            response = self.model.generate_content(prompt)
            return response.text
            
        except Exception as e:
            logger.error(f"Error generating stress relief practice: {str(e)}")
            return """🚨 System Error: If you're experiencing a crisis or emergency, please:
            1. Call Emergency Services (911) if you're in immediate danger
            2. Contact Crisis Text Line: Text HOME to 741741
            3. Call National Suicide Prevention Lifeline: 988
            
            Your safety and wellbeing are the top priority.""" 