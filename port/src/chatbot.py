import streamlit as st
import google.generativeai as genai
from typing import List, Dict
import json
import time

class FinanceChatbot:
    def __init__(self, api_key: str, max_history: int = 10):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-pro')
        self.max_history = max_history
        self._initialize_session_state()
        
    def _initialize_session_state(self):
        """Initialize session state variables for chat history and context"""
        if 'chat_history' not in st.session_state:
            st.session_state.chat_history = []
        if 'context_data' not in st.session_state:
            st.session_state.context_data = {
                'portfolio_data': {},
                'market_data': {},
                'user_preferences': {}
            }
        if 'current_message' not in st.session_state:
            st.session_state.current_message = ""
        if 'chat_expanded' not in st.session_state:
            st.session_state.chat_expanded = False
        if 'is_typing' not in st.session_state:
            st.session_state.is_typing = False
        if 'error_message' not in st.session_state:
            st.session_state.error_message = None
            
    def update_context(self, context_type: str, data: Dict):
        """Update the contextual data for the chatbot
        
        Args:
            context_type (str): Type of context to update ('portfolio_data', 'market_data', or 'user_preferences')
            data (Dict): The data to update the context with
        """
        valid_types = {'portfolio_data', 'market_data', 'user_preferences'}
        if context_type not in valid_types:
            raise ValueError(f"Invalid context_type. Must be one of: {valid_types}")
            
        if not isinstance(data, dict):
            raise TypeError("Data must be a dictionary")
            
        # Update the context data
        st.session_state.context_data[context_type] = data
        
        # Add a system message about context update if it's significant
        if context_type == 'portfolio_data' and data:
            self._add_system_message(f"Portfolio data updated. Total value: ${data.get('total_portfolio_value', 0):,.2f}")
            
    def _add_system_message(self, message: str):
        """Add a system message to chat history"""
        if st.session_state.chat_history and st.session_state.chat_history[-1].get('role') == 'system':
            # Update existing system message
            st.session_state.chat_history[-1]['content'] = message
        else:
            # Add new system message
            st.session_state.chat_history.append({
                "role": "system",
                "content": message
            })
        
    def _manage_chat_history(self):
        """Manage chat history size"""
        if len(st.session_state.chat_history) > self.max_history * 2:  # *2 for pairs of messages
            st.session_state.chat_history = st.session_state.chat_history[-self.max_history * 2:]
            
    def _get_conversation_context(self) -> str:
        """Get recent conversation context"""
        recent_messages = st.session_state.chat_history[-4:]  # Last 2 exchanges
        context = "\n".join([f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}" 
                           for msg in recent_messages])
        return context
        
    def _build_prompt(self, user_message: str) -> str:
        """Build a context-aware prompt for the AI model"""
        portfolio_data = st.session_state.context_data.get('portfolio_data', {})
        metrics = {
            'total_value': portfolio_data.get('total_portfolio_value', 0),
            'volatility': portfolio_data.get('performance_metrics', {}).get('volatility', 0),
            'sharpe_ratio': portfolio_data.get('performance_metrics', {}).get('sharpe_ratio', 0),
            'diversification': portfolio_data.get('risk_metrics', {}).get('diversification_score', 0),
            'asset_allocation': portfolio_data.get('asset_allocation', {})
        }
        
        return f"""You are a portfolio advisor. Keep answers short and direct.

Portfolio:
${metrics['total_value']:,.2f} total value
{metrics['volatility']:.2f}% volatility
{metrics['sharpe_ratio']:.2f} Sharpe ratio
{metrics['diversification']:.2f}% diversification
Assets: {metrics['asset_allocation']}

Rules:
1. Maximum 2 sentences per response
2. Always include one relevant number
3. Give clear buy/sell advice when asked
4. Focus on the most important metric

Question: {user_message}"""

    def _handle_message(self):
        """Handle the message submission"""
        if st.session_state.current_message.strip():
            user_message = st.session_state.current_message.strip()
            
            # Add user message to chat history
            st.session_state.chat_history.append({
                "role": "user",
                "content": user_message
            })
            
            # Set typing indicator
            st.session_state.is_typing = True
            st.session_state.error_message = None
            
            try:
                # Generate AI response
                prompt = self._build_prompt(user_message)
                response = self.model.generate_content(prompt)
                
                # Add AI response to chat history
                st.session_state.chat_history.append({
                    "role": "assistant",
                    "content": response.text
                })
                
                # Manage chat history size
                self._manage_chat_history()
                
            except Exception as e:
                st.session_state.error_message = f"Error: {str(e)}"
            finally:
                # Reset states
                st.session_state.is_typing = False
                st.session_state.current_message = ""
                st.rerun()

    def display_chat_ui(self):
        """Display the chatbot UI in the bottom right corner"""
        # Create a container for the chat interface
        chat_container = st.container()
        
        # Add minimal custom styling
        st.markdown(
            """
            <style>
            .chat-toggle {
                position: fixed;
                bottom: 20px;
                right: 20px;
                z-index: 1000;
            }
            .typing-indicator {
                color: #666;
                font-style: italic;
                margin-bottom: 10px;
            }
            .error-message {
                color: #ff4b4b;
                margin-bottom: 10px;
            }
            .chat-message {
                margin-bottom: 10px;
                padding: 8px 0;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        # Chat toggle button in bottom right
        col1, col2, col3 = st.columns([1, 1, 0.2])
        with col3:
            if st.button("💬", key="chat_toggle", help="Toggle chat"):
                st.session_state.chat_expanded = not st.session_state.chat_expanded
        
        # Only show chat interface if expanded
        if st.session_state.chat_expanded:
            with st.sidebar:
                st.markdown("### 💬 Finance Assistant")
                
                # Display chat messages (excluding system messages)
                for message in st.session_state.chat_history:
                    if message["role"] != "system":  # Skip system messages
                        with st.container():
                            if message["role"] == "user":
                                st.markdown(f"**You:** {message['content']}")
                            else:
                                st.markdown(f"**Assistant:** {message['content']}")
                
                # Show typing indicator
                if st.session_state.is_typing:
                    st.markdown("*Assistant is typing...*")
                
                # Show error message if any
                if st.session_state.error_message:
                    st.error(st.session_state.error_message)
                
                # Chat input
                st.text_input(
                    "",
                    placeholder="Ask me anything about your portfolio...",
                    key="current_message",
                    on_change=self._handle_message,
                    disabled=st.session_state.is_typing
                )
                
                # Help text
                with st.expander("💡 Tips"):
                    st.markdown("""
                    **Ask about:**
                    - Portfolio performance and metrics
                    - Risk analysis and recommendations
                    - Asset allocation suggestions
                    - Trading recommendations
                    - Market analysis and trends
                    """)
                    
                # Clear chat button
                if st.button("🗑️ Clear Chat"):
                    st.session_state.chat_history = []
                    st.rerun()