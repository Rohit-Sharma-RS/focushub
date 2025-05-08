import random

# Motivational responses categorized by sentiment level
POSITIVE_RESPONSES = [
    "Great job! Keep up the positive energy!",
    "You're doing amazing work! 🌟",
    "Your enthusiasm is contagious!"
]

NEUTRAL_RESPONSES = [
    "Remember to take breaks when needed.",
    "Stay focused, you've got this!",
    "One step at a time, you're making progress."
]

NEGATIVE_RESPONSES = [
    "It's okay to feel frustrated sometimes. Take a deep breath.",
    "Don't be too hard on yourself. You're doing great!",
    "Perhaps it's time for a short break? Clearing your mind can help.",
    "Remember why you started this journey. You've got this!",
    "Everyone faces challenges. You're not alone in this."
]

def get_motivational_response(mood_score):
    """Return a motivational message based on the mood score"""
    if mood_score < 0.3:
        return random.choice(NEGATIVE_RESPONSES)
    elif mood_score < 0.7:
        return random.choice(NEUTRAL_RESPONSES)
    else:
        return random.choice(POSITIVE_RESPONSES)