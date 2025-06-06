# ai/views.py
import json
import groq
import os
import requests # For OCR
import speech_recognition as sr 
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import dotenv
from .summarize import summarize_text
from .groq_integration import answer_question as ask_groq_general_question 

dotenv.load_dotenv()

OCR_API_KEY = os.getenv('OCR_API_KEY') # Replace with your actual key or load from env/settings

# --- OCR Functions (from your example) ---
def ocr_space_file(filename, overlay=False, api_key=OCR_API_KEY, language='auto', OCREngine=2):
    payload = {'isOverlayRequired': overlay,
               'apikey': api_key,
               'language': language,
               'OCREngine': OCREngine
               }
    try:
        with open(filename, 'rb') as f:
            r = requests.post('https://api.ocr.space/parse/image',
                              files={os.path.basename(filename): f},
                              data=payload,
                              timeout=30) # Added timeout
        r.raise_for_status() # Raise an exception for HTTP errors
        return r.content.decode()
    except requests.exceptions.RequestException as e:
        print(f"OCR API request error: {e}")
        return None
    except FileNotFoundError:
        print(f"OCR file not found: {filename}")
        return None


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
            client = groq.Groq(api_key=os.environ.get('GROQ_API_KEY'))  # Replace with actual API key
            
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
                max_tokens=300
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
            client = groq.Groq(api_key=os.getenv("GROQ_API_KEY"))
            
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

@csrf_exempt  # Use csrf_protect in production
def clear_doubts_handler(request, room_id):
    if request.method == 'POST':
        text_doubt = request.POST.get('text_doubt', '')
        image_file = request.FILES.get('image_doubt', None)

        combined_input_text = text_doubt
        image_text = ""

        fs = FileSystemStorage()

        # --- OCR Handling (Image-to-Text) ---
        if image_file:
            filename = fs.save(image_file.name, image_file)
            uploaded_image_path = fs.path(filename)

            ocr_result_json = ocr_space_file(
                filename=uploaded_image_path,
                api_key=getattr(settings, 'OCR_API_KEY', os.getenv('OCR_API_KEY'))
            )

            if ocr_result_json:
                try:
                    ocr_data = json.loads(ocr_result_json)
                    if not ocr_data.get('IsErroredOnProcessing') and ocr_data.get('ParsedResults'):
                        image_text = ocr_data['ParsedResults'][0]['ParsedText']
                        combined_input_text += f"\n\n[Image Content: {image_text.strip()}]"
                    elif ocr_data.get('ErrorMessage'):
                        print(f"OCR Error: {ocr_data['ErrorMessage']}")
                except json.JSONDecodeError:
                    print("OCR Error: Could not decode JSON.")
                except Exception as e:
                    print(f"OCR Processing Error: {e}")

            try:
                os.remove(uploaded_image_path)
            except OSError as e:
                print(f"Error deleting image file: {e}")

        if not combined_input_text.strip():
            return JsonResponse({'error': 'No input provided for clarification.'}, status=400)

        # --- Groq API Call ---
        try:
            client = groq.Groq(api_key=os.environ.get("GROQ_API_KEY"))
            system_prompt_doubt = (
                "You are an AI assistant. A user has a doubt or a question. "
                "Provide a clear, concise, and helpful clarification based on the input provided. "
                "The input might include text and image content."
            )

            response = client.chat.completions.create(
                model="llama3-70b-8192",
                messages=[
                    {"role": "system", "content": system_prompt_doubt},
                    {"role": "user", "content": combined_input_text}
                ],
                max_tokens=1024
            )
            clarification = response.choices[0].message.content

            return JsonResponse({'clarification': clarification})

        except Exception as e:
            print(f"Groq API Error: {e}")
            return JsonResponse({'error': f'Could not get clarification from AI: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=405)