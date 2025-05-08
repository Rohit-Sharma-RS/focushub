import groq
import os
from django.conf import settings

# Initialize Groq client with API key from environment
try:
    client = groq.Groq(api_key=os.environ.get('GROQ_API_KEY', ''))
except Exception as e:
    print(f"Error initializing Groq client: {e}")
    client = None

def summarize_chat(messages, model="llama3-70b-8192"):
    """
    Use Groq API to summarize chat messages
    
    Args:
        messages: List of message objects or text content
        model: Groq model to use
        
    Returns:
        str: Summary of the chat
    """
    if not client:
        return "Groq API not configured. Please check your API key."
    
    # Format messages for the API
    if isinstance(messages[0], str):
        # If we're just given strings, create a formatted conversation
        message_texts = messages
    else:
        # Extract text from message objects
        message_texts = [msg.content for msg in messages]
    
    conversation_text = "\n".join(message_texts)
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that summarizes conversations. Provide a concise summary that captures the main points, questions, and outcomes of the discussion you can provide your insights and explain the summary in a brief way."},
                {"role": "user", "content": f"Please summarize this study room conversation:\n\n{conversation_text}"}
            ],
            max_tokens=500
        )
        summary = response.choices[0].message.content
        return summary
    except Exception as e:
        print(f"Error using Groq API: {e}")
        return "Error generating summary. Please try again later."

def answer_question(summary, question, model="llama3-70b-8192"):
    """
    Use Groq API to answer a question about the summary
    
    Args:
        summary: The summary text
        question: The user's question
        model: Groq model to use
        
    Returns:
        str: Answer to the question
    """
    if not client:
        return "Groq API not configured. Please check your API key."
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant that answers questions about a study session summary and all questions users might have in general related to studies."},
                {"role": "user", "content": f"This is a summary of a study session:\n\n{summary}\n\nPlease answer this question: {question}"}
            ],
            max_tokens=300
        )
        answer = response.choices[0].message.content
        return answer
    except Exception as e:
        print(f"Error using Groq API: {e}")
        return "Error answering question. Please try again later."