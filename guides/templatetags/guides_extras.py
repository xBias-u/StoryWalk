import re

from django import template

register = template.Library()


@register.filter
def clean_guide_text(value: str):
    if not value:
        return ''
    text = str(value).replace('\r\n', '\n')

    # Remove service headings often coming from DOCX drafts
    patterns = [
        r'(?im)^\s*длинные?\s*$\n?',
        r'(?im)^\s*короткие?\s*$\n?',
        r'(?im)^\s*вступление\s*:\s*',
    ]
    for p in patterns:
        text = re.sub(p, '', text)

    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return text
