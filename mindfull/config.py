import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration and API Setup
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Base categories for mindfulness activities
BASE_CATEGORIES = {
    'Meditation': 'Focused mental exercises for clarity and peace',
    'Breathing': 'Controlled breathing techniques for relaxation',
    'Movement': 'Gentle physical activities with mindful awareness',
    'Gratitude': 'Practices to cultivate appreciation and positivity',
    'Stress Relief': 'Techniques for reducing stress and anxiety',
    'Emotional Awareness': 'Exercises to understand and process emotions'
} 