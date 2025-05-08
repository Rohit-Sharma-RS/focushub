# ai/views.py
import json
import groq
import os
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .summarize import summarize_text

@csrf_exempt
def summarize_chat(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        messages = data.get('messages', [])
        text = '. '.join(messages) + '.'

        # Fallback to existing summarization
        fallback_summary = summarize_text(text)
        
        try:
            # Initialize Groq client
            client = groq.Groq(api_key="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")  # Replace with actual API key
            
            # Create system prompt for summarization
            system_prompt = (
                "You are an AI that summarizes discussions and generates relevant questions. "
                "Summarize the following chat into 3-5 sentences, capturing key points. "
                "Then, generate 3 follow-up questions to deepen the discussion."
            )
            
            # Call Groq LLaMa 3.3 70B model
            response = client.chat.completions.create(
                model="llama3-70b-8192",  # Groq-hosted LLaMA 3.3 70B model
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                max_tokens=1024
            )
            
            ai_response = response.choices[0].message.content
            
            # Extract summary and questions
            parts = ai_response.split('\n\n', 1)
            summary_text = parts[0]
            
            # Get questions (assuming they're in a list format after the summary)
            questions = []
            if len(parts) > 1:
                question_text = parts[1]
                for line in question_text.split('\n'):
                    line = line.strip()
                    if line and (line.startswith('-') or line.startswith('1.') or 
                                line.startswith('2.') or line.startswith('3.')):
                        questions.append(line.lstrip('- 123.').strip())
            
            return JsonResponse({
                'summary': summary_text,
                'questions': questions
            })
            
        except Exception as e:
            return JsonResponse({
                'summary': fallback_summary,
                'questions': [],
                'error': str(e)
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@csrf_exempt
def followup_question(request):
    """Handle follow-up questions to the summarization model"""
    if request.method == 'POST':
        data = json.loads(request.body)
        original_text = data.get('original_text', '')
        question = data.get('question', '')
        
        try:
            # Initialize Groq client
            client = groq.Groq(api_key="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")  # Replace with actual API key
            
            # Create system prompt for answering follow-up questions
            system_prompt = (
                "You are an AI assistant helping with a study group discussion. "
                "First, you'll see the full discussion transcript, then a follow-up question. "
                "Provide a helpful, concise answer based on the information in the discussion."
            )
            
            # Call Groq LLaMa 3.3 70B model
            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Discussion transcript:\n\n{original_text}\n\nQuestion: {question}"}
                ],
                max_tokens=1024
            )
            
            answer = response.choices[0].message.content
            
            return JsonResponse({
                'answer': answer
            })
            
        except Exception as e:
            return JsonResponse({
                'answer': "I couldn't process your question. Please try again later.",
                'error': str(e)
            })
    
    return JsonResponse({'error': 'Invalid request'}, status=400)