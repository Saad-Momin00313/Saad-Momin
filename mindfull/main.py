import streamlit as st
import time
from datetime import datetime
import pandas as pd

from activity_generator import MindfulnessActivityGenerator
from visualizations import create_mood_chart, create_practice_heatmap

def main():
    st.set_page_config(
        page_title="Mindful Moments",
        page_icon="🧘",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    # Initialize
    generator = MindfulnessActivityGenerator()
    
    # Session State
    if 'user_id' not in st.session_state:
        st.session_state.user_id = 1
    if 'current_activity' not in st.session_state:
        st.session_state.current_activity = None
    
    st.title("🧘 Mindful Moments")
    
    tabs = st.tabs(["Practice", "Progress", "Settings"])
    
    with tabs[0]:  # Practice Tab
        # Create two columns for better organization
        left_col, right_col = st.columns([2, 1])
        
        with left_col:
            st.markdown("### 🎯 Quick Practice")
            
            # Group related inputs in expanders
            with st.expander("Your Current State", expanded=True):
                mood = st.select_slider(
                    "How are you feeling right now?",
                    options=["Very Low", "Low", "Neutral", "Good", "Excellent"],
                    value="Neutral",
                    key="current_mood"
                )
                
                col1, col2 = st.columns(2)
                with col1:
                    energy = st.slider("Energy Level", 1, 10, 5, key="energy_level")
                with col2:
                    stress = st.slider("Stress Level", 1, 10, 5, key="stress_level")
                
                time_available = st.select_slider(
                    "How much time do you have?",
                    options=[5, 10, 15, 20, 30, 45, 60],
                    value=10,
                    key="time_available"
                )
            
            with st.expander("Your Interests", expanded=True):
                custom_interest = st.text_input("Add a new interest:", key="custom_interest_input")
                default_interests = ["Meditation", "Yoga", "Nature", "Reading", "Art", "Music", "Breathing", "Walking", "Journaling", "Body Scan"]
                
                if custom_interest:
                    # Validate the custom interest
                    validation_prompt = f"""
                    Is '{custom_interest}' a valid mindfulness or wellness-related interest/activity? 
                    Consider if it can be meaningfully incorporated into mindfulness practices.
                    Respond with only 'yes' or 'no'.
                    """
                    try:
                        response = generator.model.generate_content(validation_prompt)
                        is_valid = response.text.strip().lower() == 'yes'
                        
                        if is_valid and custom_interest not in default_interests:
                            default_interests.append(custom_interest)
                            st.success(f"Added '{custom_interest}' to your interests!")
                        elif not is_valid:
                            st.error(f"'{custom_interest}' doesn't seem to be a valid mindfulness-related interest. Please try something related to wellness, meditation, or mindful activities.")
                    except Exception as e:
                        st.warning("Unable to validate the interest at the moment. Please try again.")
                
                interests = st.multiselect(
                    "Select or add interests:",
                    options=default_interests,
                    default=["Meditation"],
                    key="interests_multiselect"
                )
        
        with right_col:
            st.markdown("### 🔄 Your Routines")
            
            # Default routines
            default_routines = [
                {
                    'name': 'Breathe Practice',
                    'duration': 10,
                    'description': 'Simple breathing exercises for relaxation',
                    'steps': [
                        'Find a comfortable position',
                        'Take deep breaths in through your nose',
                        'Hold for 4 seconds',
                        'Exhale slowly through your mouth',
                        'Repeat for 10 minutes'
                    ]
                },
                {
                    'name': 'Sleep Routine',
                    'duration': 10,
                    'description': 'Calming practice for better sleep',
                    'steps': [
                        'Lie down comfortably',
                        'Focus on slow, deep breathing',
                        'Relax each part of your body',
                        'Clear your mind',
                        'Continue until you feel sleepy'
                    ]
                }
            ]
            
            # Display default routines
            for routine in default_routines:
                with st.container():
                    st.markdown(f"**{routine['name']}** ({routine['duration']} min)")
                    st.caption(f"{routine['description']}")
                    if st.button("Start", key=f"default_routine_{routine['name'].lower().replace(' ', '_')}", use_container_width=True):
                        st.session_state.current_activity = {
                            'category': 'Custom Practice',
                            'text': "STEPS:\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(routine['steps'])]),
                            'duration': routine['duration']
                        }
                        st.rerun()
            
            # Get user's saved routines
            user_routines = generator.db.get_user_routines(st.session_state.user_id)
            
            if user_routines:
                for routine in user_routines:
                    with st.container():
                        st.markdown(f"**{routine['name']}** ({routine['duration']} min)")
                        st.caption(f"{routine['description']}")
                        if st.button("Start", key=f"user_routine_{routine['id']}", use_container_width=True):
                            st.session_state.current_activity = {
                                'category': routine['category'],
                                'text': "STEPS:\n" + "\n".join([f"{i+1}. {step}" for i, step in enumerate(routine['steps'])]),
                                'duration': routine['duration']
                            }
                            st.rerun()
            
            st.divider()
            with st.expander("✨ Create New Routine", expanded=False):
                new_routine_name = st.text_input("Routine Name", key="new_routine_name")
                new_routine_duration = st.number_input("Duration (minutes)", min_value=1, value=10, key="new_routine_duration")
                new_routine_steps = st.text_area("Steps (one per line)", key="new_routine_steps")
                
                if st.button("Save New Routine", key="save_new_routine_button"):
                    if new_routine_name and new_routine_steps:
                        steps = [step.strip() for step in new_routine_steps.split('\n') if step.strip()]
                        if steps:
                            new_routine = {
                                'name': new_routine_name,
                                'steps': steps,
                                'duration': new_routine_duration,
                                'category': 'Custom',
                                'description': f"Custom {new_routine_duration}-minute routine",
                                'created_at': datetime.now().isoformat(),
                                'last_practiced': None,
                                'practice_count': 0
                            }
                            try:
                                generator.db.save_routine(st.session_state.user_id, new_routine)
                                st.success("Routine saved successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error saving routine: {str(e)}")
                        else:
                            st.warning("Please add at least one step to your routine")
                    else:
                        st.warning("Please provide both a name and steps for your routine")

        st.divider()
        
        # Generate Activity button moved here
        if st.button("Generate Personalized Activity", key="generate_activity_button", use_container_width=True):
            # Create a comprehensive user profile using all parameters
            user_profile = {
                'mood': mood,
                'energy_level': energy,
                'stress_level': stress,
                'interests': interests,
                'time_available': time_available
            }
            
            with st.spinner("Creating your personalized mindful moment..."):
                # Generate activity based on all current parameters
                activity = generator.generate_personalized_activity(
                    user_profile=user_profile,
                    mood=mood,
                    energy_level=energy,
                    stress_level=stress,
                    time_available=time_available,
                    interests=interests
                )
                
                # Store the generated activity in session state
                st.session_state.current_activity = {
                    'category': 'Personalized Practice',
                    'text': activity['text'] if isinstance(activity, dict) else activity,
                    'duration': time_available,
                    'timestamp': datetime.now().strftime("%H:%M")
                }
                st.rerun()
        
        # Quick Access Features below both columns
        quick_access = st.expander("🚀 Quick Access Features", expanded=True)
        with quick_access:
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("⚡ Stress Relief")
                stress_trigger = st.text_input("What's causing stress right now?")
                if st.button("Get Quick Relief Practice"):
                    with st.spinner("Generating stress relief practice..."):
                        practice = generator.generate_stress_relief_practice(
                            stress_trigger, 
                            stress
                        )
                        st.markdown(practice)
            
            with col2:
                st.write("😴 Better Sleep")
                sleep_quality = st.select_slider(
                    "Recent sleep quality?",
                    options=["Poor", "Fair", "Good", "Excellent"],
                    value="Fair"
                )
                if st.button("Get Bedtime Practice"):
                    with st.spinner("Generating sleep practice..."):
                        practice = generator.generate_sleep_recommendation(
                            sleep_quality,
                            stress
                        )
                        st.markdown(practice)
        
        # Daily Recommendation
        current_hour = datetime.now().hour
        time_of_day = (
            "morning" if 5 <= current_hour < 12
            else "afternoon" if 12 <= current_hour < 17
            else "evening" if 17 <= current_hour < 22
            else "night"
        )
        
        daily_rec = st.expander(f"🌟 Your {time_of_day.title()} Practice Recommendation", expanded=True)
        with daily_rec:
            if st.button("Get Personalized Recommendation"):
                with st.spinner("Generating your personalized practice..."):
                    user_profile = {
                        'stress_level': stress,
                        'avg_duration': time_available,
                        'interests': interests
                    }
                    recommendation = generator.generate_daily_recommendation(
                        user_profile,
                        time_of_day
                    )
                    st.markdown(recommendation)
        
        if st.session_state.current_activity:
            activity = st.session_state.current_activity
            
            # Initialize timer state if not exists
            if 'timer_running' not in st.session_state:
                st.session_state.timer_running = False
            if 'time_left' not in st.session_state:
                st.session_state.time_left = activity.get('duration', 10) * 60
            if 'start_time' not in st.session_state:
                st.session_state.start_time = None
            
            # Display practice guide
            st.markdown(f"### {activity['category']} Practice Guide")
            st.markdown(f"**Duration:** {activity.get('duration', 10)} minutes")
            
            # Parse and display steps and benefits
            text = activity.get('text', '')
            if 'STEPS:' in text:
                # Display steps
                steps_text = text.split('STEPS:')[1].split('BENEFITS:')[0] if 'BENEFITS:' in text else text.split('STEPS:')[1]
                steps = [step.strip() for step in steps_text.split('\n') if step.strip()]
                for step in steps:
                    st.markdown(f"{step}")
                
                # Display benefits if present
                if 'BENEFITS:' in text:
                    st.markdown("\n**Benefits:**")
                    benefits = [benefit.strip() for benefit in text.split('BENEFITS:')[1].split('\n') if benefit.strip()]
                    for benefit in benefits:
                        st.markdown(benefit)
            else:
                # Fallback display if format is different
                st.markdown(text)
            
            # Timer display and controls
            col1, col2 = st.columns([3, 1])
            with col1:
                minutes = st.session_state.time_left // 60
                seconds = st.session_state.time_left % 60
                st.header(f"{minutes:02d}:{seconds:02d}")
            
            # Single container for timer controls
            timer_controls = st.container()
            with timer_controls:
                col1, col2, col3 = st.columns(3)
                
                # Initialize paused state if not exists
                if 'is_paused' not in st.session_state:
                    st.session_state.is_paused = False
                
                # Show different buttons based on timer state
                if not st.session_state.timer_running and not st.session_state.is_paused:
                    with col1:
                        if st.button("▶️ Start", key="start_timer", use_container_width=True):
                            st.session_state.timer_running = True
                            st.session_state.start_time = datetime.now()
                            st.rerun()
                else:
                    with col2:
                        button_text = "⏸️ Pause" if st.session_state.timer_running else "▶️ Resume"
                        if st.button(button_text, key="pause_resume_timer", use_container_width=True):
                            st.session_state.timer_running = not st.session_state.timer_running
                            st.session_state.is_paused = not st.session_state.timer_running
                            if st.session_state.timer_running:
                                st.session_state.start_time = datetime.now()
                            st.rerun()
                
                with col3:
                    if st.button("🔄 Reset", key="reset_timer", use_container_width=True):
                        st.session_state.timer_running = False
                        st.session_state.is_paused = False
                        st.session_state.time_left = activity.get('duration', 10) * 60
                        st.session_state.start_time = None
                        st.rerun()
            
            # Update timer if running
            if st.session_state.timer_running:
                if st.session_state.time_left > 0:
                    time.sleep(1)  # Update every second
                    st.session_state.time_left -= 1
                    st.rerun()
                else:
                    st.session_state.timer_running = False
                    st.success("Timer Complete! 🎉")
            
            # Feedback section
            st.divider()
            col1, col2 = st.columns(2)
            with col1:
                post_mood = st.select_slider(
                    "How do you feel after the practice?",
                    options=["Much Better", "Better", "Same", "Worse", "Much Worse"],
                    value="Same"
                )
                rating = st.slider("How helpful was this activity?", 1, 5, 3)
            with col2:
                feedback = st.text_area("Any feedback or notes?")
            
            if st.button("Save Progress"):
                try:
                    # Start a transaction
                    with generator.db.conn:
                        # Calculate actual duration from timer
                        initial_duration = activity.get('duration', 10) * 60  # in seconds
                        actual_duration = initial_duration - st.session_state.time_left  # in seconds
                        actual_minutes = max(1, round(actual_duration / 60))  # convert to minutes, minimum 1 minute
                        
                        # Save activity completion
                        activity_id = generator.db.save_activity(
                            st.session_state.user_id,
                            {
                                'text': activity['text'],
                                'category': activity['category'],
                                'actual_duration': actual_minutes,
                                'mood_before': mood
                            }
                        )
                        
                        # Update activity with completion details
                        if activity_id:
                            generator.db.update_activity_completion(
                                activity_id,
                                duration=actual_minutes,
                                mood_after=post_mood,
                                rating=rating,
                                feedback=feedback
                            )
                            
                            # Save mood data
                            generator.db.conn.execute('''
                                INSERT INTO mood_tracker (
                                    user_id, mood, energy_level, stress_level, notes
                                ) VALUES (?, ?, ?, ?, ?)
                            ''', (
                                st.session_state.user_id,
                                post_mood,
                                energy,
                                stress,
                                feedback
                            ))
                            
                            st.success(f"Progress saved! You practiced for {actual_minutes} minutes. Keep up the great work! 🌟")
                            time.sleep(1)  # Give user time to see the success message
                            
                            # Clear the current activity and rerun
                            st.session_state.current_activity = None
                            st.session_state.timer_running = False
                            st.session_state.is_paused = False
                            st.rerun()
                except Exception as e:
                    st.error("There was an error saving your progress. Please try again.")
    
    with tabs[1]:  # Progress Tab
        st.subheader("Your Mindfulness Journey")
        
        # Get all necessary data first
        stats = generator.db.get_user_stats(st.session_state.user_id)
        mood_data = generator.db.get_mood_data(st.session_state.user_id, days=30)
        
        # Get practice data for insights
        practice_data = generator.db.conn.execute('''
            SELECT date(created_at) as practice_date,
                   SUM(duration) as minutes
            FROM activities
            WHERE user_id = ?
              AND created_at >= date('now', '-30 days')
              AND completed = 1
            GROUP BY date(created_at)
            ORDER BY practice_date
        ''', (st.session_state.user_id,)).fetchall()
        
        # Create three columns for key metrics
        metric_col1, metric_col2, metric_col3 = st.columns(3)
        
        with metric_col1:
            st.metric("Total Practice Time", f"{stats.get('total_minutes', 0)} min")
        with metric_col2:
            weekly_minutes = stats.get('minutes_this_week', 0)  # Using the correct key name
            st.metric("Weekly Progress", f"{weekly_minutes} min")
        with metric_col3:
            st.metric("Daily Streak", f"{stats.get('current_streak', 0)} days")
        
        # Progress Insights in a clean container
        st.markdown("### 📊 Progress Insights")
        insights = generator.generate_progress_insights(stats, mood_data, practice_data)
        st.markdown(insights)
        
        # Visual Progress Section
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### 📅 Monthly Progress")
            # Monthly Calendar code remains the same
            current_month = datetime.now().strftime("%B %Y")
            dates = pd.date_range(start=datetime.now().replace(day=1), periods=30)
            practice_minutes = [0] * 30
            
            for date, minutes in practice_data:
                day_of_month = datetime.strptime(date, "%Y-%m-%d").day
                if 1 <= day_of_month <= 30:
                    practice_minutes[day_of_month - 1] = minutes
            
            weekly_data = [practice_minutes[i:i+7] for i in range(0, 28, 7)]
            fig = create_practice_heatmap({
                'values': weekly_data,
                'dates': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
            })
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("### 📈 Trends")
            if mood_data['dates']:
                fig = create_mood_chart(mood_data)
                st.plotly_chart(fig, use_container_width=True)
    
    with tabs[2]:  # Settings Tab
        st.subheader("⚙️ Customize Your Experience")
        
        # Get current settings
        current_settings = generator.db.get_user_settings(st.session_state.user_id)
        
        # Practice Preferences
        st.write("🎯 Practice Goals")
        col1, col2 = st.columns(2)
        with col1:
            daily_goal = st.number_input(
                "Daily practice goal (minutes)", 
                min_value=5, 
                value=current_settings['daily_goal']
            )
            reminder_time = st.time_input(
                "Daily reminder time",
                datetime.now().time()
            )
        with col2:
            weekly_goal = st.number_input(
                "Weekly practice goal (minutes)",
                min_value=30,
                value=daily_goal * 7
            )
            enable_notifications = st.checkbox("Enable notifications")
        
        # Custom Practice Routines
        st.write("🎨 Custom Practice Routines")
        routine_name = st.text_input("Routine Name", key="routine_name_settings")
        routine_steps = st.text_area("Steps (one per line)", key="routine_steps_settings")
        
        if st.button("Save Routine"):
            # TODO: Implement custom routine saving
            st.success("Custom routine saved!")
        
        # Theme Settings
        st.write("🎨 Appearance")
        theme = st.selectbox(
            "Theme",
            ["Dark", "Light"],
            index=0 if current_settings['theme'] == "Dark" else 1
        )
        accent_color = st.color_picker(
            "Accent Color",
            current_settings['accent_color']
        )
        
        # Export Data
        st.write("📤 Export Your Progress")
        if st.button("Export Progress (CSV)"):
            try:
                # Get actual progress data
                progress_df = generator.db.export_user_progress(st.session_state.user_id)
                
                if not progress_df.empty:
                    # Convert to CSV
                    csv = progress_df.to_csv(index=False)
                    
                    # Add timestamp to filename
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"mindfulness_progress_{timestamp}.csv"
                    
                    st.download_button(
                        label="Download Progress Data",
                        data=csv,
                        file_name=filename,
                        mime="text/csv"
                    )
                    st.success("Your progress data is ready for download!")
                else:
                    st.info("No progress data available yet. Complete some sessions to see your progress!")
            except Exception as e:
                st.error("There was an error exporting your progress. Please try again.")
        
        # Save Settings
        if st.button("Save Settings"):
            try:
                # Format reminder time as string
                reminder_time_str = reminder_time.strftime("%H:%M") if reminder_time else None
                
                # Update settings in database
                new_settings = {
                    'daily_goal': daily_goal,
                    'theme': theme,
                    'accent_color': accent_color,
                    'reminder_time': reminder_time_str,
                    'enable_notifications': enable_notifications
                }
                
                generator.db.update_user_settings(st.session_state.user_id, new_settings)
                st.success("Settings saved successfully! 🎉")
                time.sleep(1)  # Give user time to see success message
                st.rerun()
            except Exception as e:
                st.error(f"There was an error saving your settings: {str(e)}")

if __name__ == "__main__":
    main() 