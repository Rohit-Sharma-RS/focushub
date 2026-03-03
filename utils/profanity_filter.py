import re
import unicodedata

BAD_WORDS = {
    "fuck", "shit", "bitch", "asshole", "bastard", "dick", "cunt", "slut", "nigga",
    "chutiya", "chuteya", "bhenchod", "madarchod", "loda", "lund", "gaand", "gandu",
    "randi", "kamina", "harami", "gaandmasti", "bkl", "mc", "bc", "pgl", "pagal", "stupid", "mad", "crazy"
}

OBFUSCATION_PATTERNS = [
    r"[\*\#\@\!\$]+" 
]

def normalize_text(text):
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('utf-8', 'ignore')
    text = text.lower()
    for pattern in OBFUSCATION_PATTERNS:
        text = re.sub(pattern, '', text)
    return text

def contains_profanity(text):
    normalized = normalize_text(text)
    words = re.findall(r'\w+', normalized)
    for word in words:
        if word in BAD_WORDS:
            return True
    return False
