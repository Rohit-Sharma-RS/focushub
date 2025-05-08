def summarize_text(text):
    """
    A simple text summarization function.
    In a real implementation, this would use a more sophisticated model.
    """
    if not text:
        return "No text to summarize."
        
    # Simple extractive summarization using sentence importance
    sentences = text.split('. ')
    if len(sentences) <= 3:
        return text
        
    important_words = ['study', 'learn', 'important', 'key', 'remember', 'concept', 'understand']
    scored_sentences = []
    
    for sentence in sentences:
        score = 0
        for word in important_words:
            if word in sentence.lower():
                score += 1
        scored_sentences.append((sentence, score))
    
    # Sort by score and take top sentences
    sorted_sentences = sorted(scored_sentences, key=lambda x: x[1], reverse=True)
    summary_sentences = [s[0] for s in sorted_sentences[:3]]
    
    # Reconstruct summary
    summary = '. '.join(summary_sentences)
    if not summary.endswith('.'):
        summary += '.'
        
    return summary