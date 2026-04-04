import re

from django import template

register = template.Library()


def _capitalize_first(s: str) -> str:
    s = s.strip()
    if not s:
        return s
    return s[0].upper() + s[1:]


@register.filter
def clean_guide_text(value: str):
    if not value:
        return ''

    text = str(value).replace('\r\n', '\n').replace('\r', '\n').replace('\xa0', ' ')

    junk_tokens = {
        'длинный', 'длинные',
        'короткий', 'короткие',
        'вступление', 'вкладка', 'вкладка 2',
    }

    cleaned_lines = []
    for raw in text.split('\n'):
        line = re.sub(r'\s+', ' ', raw).strip()
        if not line:
            cleaned_lines.append('')
            continue

        low = line.lower().strip(' :.-—–')

        # remove headings like "Вступление: ..."
        if low.startswith('вступление:'):
            line = line.split(':', 1)[1].strip()
            low = line.lower().strip(' :.-—–')

        if low in junk_tokens:
            continue

        cleaned_lines.append(line)

    text = '\n'.join(cleaned_lines)
    text = re.sub(r'\n{3,}', '\n\n', text).strip()
    return _capitalize_first(text)


@register.filter
def format_guide_text(value: str):
    """Improve readability: force semantic paragraph breaks for long OCR/docx blocks."""
    if not value:
        return ''

    text = str(value).replace('\r\n', '\n').replace('\r', '\n').strip()

    # If there are already many paragraph breaks, preserve them.
    if text.count('\n\n') >= 3:
        return _capitalize_first(text)

    # Split into sentences and group by 2-3 sentences per paragraph.
    parts = [p.strip() for p in re.split(r'(?<=[.!?…])\s+', text) if p.strip()]
    if len(parts) <= 3:
        return _capitalize_first(text)

    paragraphs = []
    chunk = []
    for i, s in enumerate(parts, start=1):
        chunk.append(s)
        # paragraph break roughly every 2-3 sentences
        if len(chunk) >= 3 or (len(chunk) >= 2 and len(s) > 170):
            paragraphs.append(' '.join(chunk).strip())
            chunk = []
    if chunk:
        paragraphs.append(' '.join(chunk).strip())

    out = '\n\n'.join(paragraphs)
    out = re.sub(r'\n{3,}', '\n\n', out).strip()
    return _capitalize_first(out)
