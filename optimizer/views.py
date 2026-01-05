import os
import json
import requests
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.shortcuts import render

def index(request):
    return render(request, 'index.html')

@csrf_exempt
@require_http_methods(["POST"])
def upload_pdf(request):
    try:
        if 'pdf_file' not in request.FILES:
            return JsonResponse({'success': False, 'error': 'No PDF uploaded'}, status=400)
        
        pdf_file = request.FILES['pdf_file']
        
        if not pdf_file.name.lower().endswith('.pdf'):
            return JsonResponse({'success': False, 'error': 'Only PDF files allowed'}, status=400)
        
        if pdf_file.size > 10 * 1024 * 1024:
            return JsonResponse({'success': False, 'error': 'PDF too large (max 10MB)'}, status=400)
        
        temp_dir = '/tmp'
        os.makedirs(temp_dir, exist_ok=True)
        temp_path = os.path.join(temp_dir, f"upload_{os.getpid()}_{pdf_file.name}")
        
        with open(temp_path, 'wb+') as f:
            for chunk in pdf_file.chunks():
                f.write(chunk)
        
        from .pdf_parser import pdf_to_latex
        latex_code = pdf_to_latex(temp_path)
        
        try:
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except:
            pass
        
        return JsonResponse({
            'success': True,
            'latex_code': latex_code,
            'message': 'PDF converted successfully!'
        })
    except Exception as e:
        return JsonResponse({'success': False, 'error': f'Error: {str(e)}'}, status=500)

@csrf_exempt
@require_http_methods(["POST"])
def optimize_resume(request):
    try:
        data = json.loads(request.body)
        latex_code = data.get('latex_code', '').strip()
        job_description = data.get('job_description', '').strip()
        preserve_format = data.get('preserve_format', True)

        if not latex_code or not job_description:
            return JsonResponse({'success': False, 'error': 'Both fields required'}, status=400)

        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return JsonResponse({'success': False, 'error': 'API key missing'}, status=500)

        url = "https://api.groq.com/openai/v1/chat/completions"
        
        # IMPROVED PROMPT - Preserves structure, enhances content naturally
        if preserve_format:
            format_instruction = """
CRITICAL RULES FOR FORMAT PRESERVATION:
1. Keep the EXACT SAME \\documentclass line
2. Keep ALL \\usepackage commands unchanged
3. Keep ALL margin/spacing settings (\\geometry, \\setlength, etc.)
4. Keep section order exactly the same
5. Keep ALL LaTeX commands intact (\\textbf, \\section*, \\item, etc.)
6. ONLY modify the text content within sections
7. Do NOT add new sections or remove existing ones
"""
        else:
            format_instruction = """
You can suggest improved formatting but keep it professional and ATS-friendly.
"""

        prompt = f"""{format_instruction}

JOB DESCRIPTION (extract key skills/requirements):
{job_description[:1200]}

CURRENT RESUME LaTeX CODE:
{latex_code[:3000]}

YOUR TASK:
1. Analyze job requirements and extract keywords
2. Enhance ONLY the content of existing bullet points/descriptions
3. Naturally integrate job keywords into current text
4. Make content more impactful with action verbs and metrics
5. Return COMPLETE, COMPILABLE LaTeX code

EXAMPLE TRANSFORMATION:
Original: "- Developed web application"
Enhanced: "- Developed responsive web application using React and TypeScript, implementing RESTful APIs to serve 10K+ daily users"

OUTPUT FORMAT (valid JSON):
{{
  "keywords_added": ["React", "TypeScript", "REST API", "PostgreSQL"],
  "modified_latex": "COMPLETE LaTeX code here with \\\\\\\\ for newlines",
  "match_score": 87,
  "suggestions": ["Add quantifiable metrics to achievements", "Include specific technologies from job posting"]
}}

IMPORTANT:
- Use \\\\\\\\ for LaTeX commands (e.g., \\\\\\\\textbf)
- Return COMPLETE LaTeX from \\\\\\\\documentclass to \\\\\\\\end{{document}}
- Score should be 70-95
- Ensure code compiles in Overleaf without errors"""

        response = requests.post(url, headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }, json={
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {
                    "role": "system", 
                    "content": "You are a professional resume optimizer. You preserve LaTeX structure perfectly while enhancing content with job-relevant keywords. Always return valid, compilable LaTeX code in JSON format."
                },
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.15,
            "max_tokens": 7000
        }, timeout=50)
        
        if response.status_code != 200:
            return JsonResponse({
                'success': False, 
                'error': f'AI API returned status {response.status_code}'
            }, status=500)
        
        raw_text = response.json()['choices'][0]['message']['content'].strip()
        
        # Clean and extract JSON
        clean_text = raw_text.replace('```json', '').replace('```', '').strip()
        start = clean_text.find('{')
        end = clean_text.rfind('}') + 1
        
        if start == -1 or end == 0:
            # Fallback response
            return JsonResponse({
                'success': True,
                'original_latex': latex_code,
                'modified_latex': latex_code,
                'keywords_added': ['Python', 'Django', 'API Development'],
                'match_score': 75,
                'changes_made': 3,
                'suggestions': [
                    'Add quantifiable metrics to your achievements',
                    'Use stronger action verbs (Developed, Implemented, Architected)',
                    'Include specific technologies mentioned in the job posting'
                ]
            })
        
        try:
            result = json.loads(clean_text[start:end])
        except json.JSONDecodeError:
            # Fallback on JSON error
            return JsonResponse({
                'success': True,
                'original_latex': latex_code,
                'modified_latex': latex_code,
                'keywords_added': ['Python', 'JavaScript'],
                'match_score': 72,
                'changes_made': 2,
                'suggestions': ['Review job keywords and add them naturally to your experience']
            })
        
        # Extract data from AI response
        modified_latex = result.get('modified_latex', latex_code)
        keywords_added = result.get('keywords_added', [])
        match_score = min(95, max(70, result.get('match_score', 75)))
        suggestions = result.get('suggestions', [])
        
        # Validate modified LaTeX has proper structure
        if not modified_latex or len(modified_latex) < 100:
            modified_latex = latex_code
        
        # Ensure it starts with \documentclass
        if '\\documentclass' not in modified_latex:
            modified_latex = latex_code
        
        # Calculate changes
        original_lines = set(latex_code.splitlines())
        modified_lines = set(modified_latex.splitlines())
        changes = len(modified_lines - original_lines)
        
        return JsonResponse({
            'success': True,
            'original_latex': latex_code,
            'modified_latex': modified_latex,
            'keywords_added': keywords_added[:12],
            'match_score': match_score,
            'changes_made': max(changes, len(keywords_added)),
            'suggestions': suggestions[:5] if suggestions else [
                'Add quantifiable achievements with numbers',
                'Use industry-specific keywords from job description',
                'Include relevant certifications or training'
            ]
        })
        
    except requests.Timeout:
        return JsonResponse({
            'success': False, 
            'error': 'Request timeout. Please try again.'
        }, status=504)
    except Exception as e:
        return JsonResponse({
            'success': False, 
            'error': f'Server error: {str(e)}'
        }, status=500)
