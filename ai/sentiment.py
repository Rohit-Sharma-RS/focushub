import nltk
from nltk.sentiment.vader import SentimentIntensityAnalyzer

# Download necessary NLTK data
try:
    nltk.data.find('vader_lexicon')
except LookupError:
    nltk.download('vader_lexicon')

# Initialize sentiment analyzer
sia = SentimentIntensityAnalyzer()

def analyze_sentiment(text):
    """
    Analyze the sentiment of text and return a score between 0 and 1,
    where 0 is very negative and 1 is very positive.
    """
    if not text:
        return 0.5  # Neutral for empty text
        
    sentiment = sia.polarity_scores(text)
    # Convert from -1 to 1 scale to 0 to 1 scale
    normalized_score = (sentiment['compound'] + 1) / 2
    return normalized_score