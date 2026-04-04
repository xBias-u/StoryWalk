import re

from django import template

register = template.Library()


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
    return text
