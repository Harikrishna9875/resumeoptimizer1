import fitz
import re

def pdf_to_latex(pdf_path):
    """Convert PDF to clean, compilable LaTeX code"""
    try:
        doc = fitz.open(pdf_path)
        full_text = "\n".join([page.get_text() for page in doc])
        doc.close()
        
        if not full_text.strip():
            return get_default_template()
        
        # Extract components
        name = extract_name(full_text)
        contact = extract_contact(full_text)
        education = extract_section(full_text, ["EDUCATION", "ACADEMIC BACKGROUND"])
        skills = extract_section(full_text, ["SKILLS", "TECHNICAL SKILLS", "CORE COMPETENCIES"])
        experience = extract_section(full_text, ["EXPERIENCE", "WORK EXPERIENCE", "PROFESSIONAL EXPERIENCE", "PROJECTS"])
        
        # Build compilable LaTeX
        latex_code = f"""\\documentclass[a4paper,11pt]{{article}}
\\usepackage[utf8]{{inputenc}}
\\usepackage[margin=0.75in]{{geometry}}
\\usepackage{{enumitem}}
\\usepackage{{hyperref}}

\\pagestyle{{empty}}

\\begin{{document}}

\\begin{{center}}
{{\\Large \\textbf{{{escape_latex(name)}}}}}\\\\[0.2cm]
{escape_latex(contact)}
\\end{{center}}

\\vspace{{0.3cm}}

\\section*{{Education}}
{education or "Bachelor of Technology in Computer Science\\\\University Name, 2023"}

\\section*{{Skills}}
{skills or "Python, JavaScript, React, Django, PostgreSQL, Docker, Git"}

\\section*{{Experience}}
{experience or "Software Developer Intern - Company Name (2023)\\\\- Developed web applications using modern frameworks"}

\\end{{document}}"""
        
        return latex_code
        
    except Exception as e:
        return get_default_template()

def get_default_template():
    """Return a clean default template"""
    return """\\documentclass[a4paper,11pt]{article}
\\usepackage[utf8]{inputenc}
\\usepackage[margin=0.75in]{geometry}

\\pagestyle{empty}

\\begin{document}

\\begin{center}
{\\Large \\textbf{Your Name}}\\\\[0.2cm]
email@example.com | +91-1234567890 | linkedin.com/in/yourname
\\end{center}

\\vspace{0.3cm}

\\section*{Education}
Bachelor of Technology in Computer Science\\\\
University Name, Graduated 2023\\\\
GPA: 8.5/10

\\section*{Skills}
\\textbf{Languages:} Python, JavaScript, Java, C++\\\\
\\textbf{Frameworks:} Django, React, Node.js, Flask\\\\
\\textbf{Tools:} Git, Docker, PostgreSQL, MongoDB

\\section*{Experience}
\\textbf{Software Developer Intern} - Company Name (June 2023 - Dec 2023)
\\begin{itemize}
\\item Developed web applications using Django and React
\\item Implemented REST APIs serving 5000+ requests per day
\\item Collaborated with team of 5 developers using Agile methodology
\\end{itemize}

\\section*{Projects}
\\textbf{E-commerce Platform}
\\begin{itemize}
\\item Built full-stack application with React frontend and Django backend
\\item Integrated payment gateway and user authentication
\\end{itemize}

\\end{document}"""

def escape_latex(text):
    """Escape special LaTeX characters"""
    if not text:
        return ""
    replacements = {
        '&': '\\&',
        '%': '\\%',
        '$': '\\$',
        '#': '\\#',
        '_': '\\_',
        '{': '\\{',
        '}': '\\}',
        '~': '\\textasciitilde{}',
        '^': '\\textasciicircum{}',
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    return text

def extract_name(text):
    """Extract name from top of resume"""
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    
    for line in lines[:8]:
        # Skip lines with common keywords
        if any(keyword in line.upper() for keyword in ['EMAIL', 'PHONE', 'LINKEDIN', 'GITHUB', '@', 'HTTP', 'WWW']):
            continue
        
        # Name is usually 2-4 words, not too long
        words = line.split()
        if 2 <= len(words) <= 4 and len(line) < 50:
            # Check if it looks like a name (starts with capital letters)
            if all(word[0].isupper() for word in words if word):
                return line.title()
    
    return "Your Name"

def extract_contact(text):
    """Extract contact information"""
    email_match = re.search(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    phone_match = re.search(r'[\+\(]?[\d\s\-\(\)]{10,}', text)
    linkedin_match = re.search(r'linkedin\.com/in/[\w\-]+', text, re.IGNORECASE)
    
    parts = []
    if email_match:
        parts.append(email_match.group(0))
    if phone_match:
        parts.append(phone_match.group(0).strip())
    if linkedin_match:
        parts.append(linkedin_match.group(0))
    
    return ' | '.join(parts) if parts else 'email@example.com | +91-1234567890'

def extract_section(text, keywords):
    """Extract section content by keywords"""
    text_upper = text.upper()
    
    for keyword in keywords:
        pos = text_upper.find(keyword)
        if pos != -1:
            # Get text after keyword heading
            section_start = pos + len(keyword)
            
            # Find next section (another heading in caps)
            next_sections = []
            for search_keyword in ["EDUCATION", "EXPERIENCE", "SKILLS", "PROJECTS", "CERTIFICATIONS", "AWARDS"]:
                next_pos = text_upper.find(search_keyword, section_start)
                if next_pos > section_start:
                    next_sections.append(next_pos)
            
            section_end = min(next_sections) if next_sections else section_start + 800
            section_text = text[section_start:section_end].strip()
            
            # Clean and format
            lines = [l.strip() for l in section_text.split('\n') if l.strip()]
            if lines:
                formatted = []
                for line in lines[:10]:  # Limit lines
                    if line and len(line) > 3:
                        # Add bullet if not present
                        if not line.startswith(('-', '•', '·', '*')):
                            formatted.append(f"- {line}")
                        else:
                            formatted.append(line.replace('•', '-').replace('·', '-').replace('*', '-'))
                
                return '\\\\'.join(formatted)
    
    return ""
