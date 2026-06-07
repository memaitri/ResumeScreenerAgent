from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from pathlib import Path
import requests

pdf_path = Path('test_resume.pdf')
with pdf_path.open('wb') as f:
    c = canvas.Canvas(f, pagesize=letter)
    c.drawString(72, 720, 'Software Engineer Resume')
    c.drawString(72, 700, 'Experience: Python, ML, data analysis, AWS')
    c.drawString(72, 680, 'Skills: Python, machine learning, cloud computing, Agile')
    c.save()

url = 'http://127.0.0.1:8000/screen'
files = {'resumes': ('test_resume.pdf', pdf_path.read_bytes(), 'application/pdf')}
data = {'jd': 'Seeking a software engineer with Python, machine learning, and cloud experience.'}
try:
    r = requests.post(url, data=data, files=files, timeout=120)
    print('STATUS', r.status_code)
    print(r.text)
except Exception as e:
    print('ERROR', e)
