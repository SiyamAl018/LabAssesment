"""Conservative extraction: retain explicit statements, never invent missing facts."""
import re
import unicodedata
from datetime import date, datetime, time, timedelta

import dateparser
from rapidfuzz import fuzz

FIELDS = ('farmer', 'plot', 'crop', 'problem', 'advice', 'follow_up')
LABELS = {
    'farmer': r'farmer|farm(?: name)?|কৃষক|কৃষকের নাম',
    'plot': r'plot|field|জমি|প্লট',
    'crop': r'crop|ফসল',
    'problem': r'problem|সমস্যা',
    'advice': r'advice|পরামর্শ',
    'follow_up': r'follow[ -]?up|ফলো[ -]?আপ',
}
LABEL = re.compile(r'(?P<label>' + '|'.join(LABELS.values()) + r')\s*[:：]\s*', re.I)
NO_PROBLEM = re.compile(r'\b(?:no problems?|no issues?|nothing wrong)\b|কোনো সমস্যা নেই|কোন সমস্যা নেই|সমস্যা নেই', re.I)
NUMBERS = {'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5, 'six': 6,
           'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10, 'a': 1, 'an': 1,
           'এক': 1, 'দুই': 2, 'তিন': 3, 'চার': 4, 'পাঁচ': 5, 'সাত': 7}
RELATIVE = re.compile(r'\b(?:in|after)\s+(\d+|' + '|'.join(NUMBERS) + r')\s+(days?|weeks?|months?)\b|\b(?:next\s+(?:week|month)|tomorrow|day after tomorrow)\b|(?:আগামী সপ্তাহে|আগামীকাল)|(?:[০-৯\d]+|এক|দুই|তিন|চার|পাঁচ|সাত)\s*(?:দিন|সপ্তাহ|মাস)\s*(?:পরে|পর)', re.I)


def normalize_name(value: str) -> str:
    value = unicodedata.normalize('NFKC', value).casefold()
    value = ''.join(c if c.isalnum() or c.isspace() or unicodedata.category(c).startswith('M') else ' ' for c in value)
    tokens = [v for v in value.split() if v not in {'mia', 'miah', 'bhai', 'মিয়া', 'মিয়া', 'মিঞা', 'ভাই'}]
    variants = {'mohammad': 'muhammad', 'mohammed': 'muhammad', 'muhammed': 'muhammad', 'rahman': 'rahman', 'rehman': 'rahman'}
    return ' '.join(variants.get(v, v) for v in tokens)


def match_farm(name, farms):
    query = normalize_name(name or '')
    if not query:
        return {'status': 'no_match', 'farm_id': None, 'candidates': []}
    candidates = []
    for farm in farms:
        names = [normalize_name(n) for n in [farm['name'], farm.get('owner_name') or '', *farm['aliases']]]
        score = max((fuzz.ratio(query, n) for n in names if n), default=0)
        if score >= 65:
            candidates.append({'id': farm['id'], 'name': farm['name'], 'score': round(score, 2)})
    candidates.sort(key=lambda c: (-c['score'], c['id']))
    if not candidates:
        return {'status': 'no_match', 'farm_id': None, 'candidates': []}
    confident = candidates[0]['score'] >= 90 and (len(candidates) == 1 or candidates[0]['score'] - candidates[1]['score'] >= 10)
    return {'status': 'confident_match' if confident else 'uncertain',
            'farm_id': candidates[0]['id'] if confident else None, 'candidates': candidates[:5]}


def due_date(phrase: str | None, visit_date: str):
    if not phrase:
        return None
    base = datetime.combine(date.fromisoformat(visit_date), time())
    text = phrase.casefold().translate(str.maketrans('০১২৩৪৫৬৭৮৯', '0123456789'))
    text = text.replace('আগামী সপ্তাহে', 'next week').replace('আগামীকাল', 'tomorrow')
    for word, number in NUMBERS.items():
        text = re.sub(r'(?<!\w)' + word + r'(?!\w)', str(number), text)
    text = re.sub(r'(\d+)\s*(দিন|সপ্তাহ|মাস)\s*(?:পরে|পর)', lambda m: f"in {m[1]} { {'দিন': 'days', 'সপ্তাহ': 'weeks', 'মাস': 'months'}[m[2]]}", text)
    if 'day after tomorrow' in text:
        return (base.date() + timedelta(days=2)).isoformat()
    # Only pass recognizable temporal expressions to dateparser, not arbitrary prose.
    patterns = [r'\b(?:in|after)\s+\d+\s+(?:days?|weeks?|months?)\b',
                r'\bnext\s+(?:week|month|monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b',
                r'\btomorrow\b', r'\b\d{4}-\d{2}-\d{2}\b',
                r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:,?\s+\d{4})?\b']
    for pattern in patterns:
        found = re.search(pattern, text)
        if found:
            result = dateparser.parse(found[0], languages=['en'], settings={'RELATIVE_BASE': base, 'PREFER_DATES_FROM': 'future'})
            if result:
                return result.date().isoformat()
    return None


def parse_note(raw: str, visit_date: str):
    result = dict.fromkeys(FIELDS)
    labels = list(LABEL.finditer(raw))
    for i, label in enumerate(labels):
        field = next(k for k, pattern in LABELS.items() if re.fullmatch(pattern, label['label'], re.I))
        value = raw[label.end():labels[i + 1].start() if i + 1 < len(labels) else len(raw)].strip(' \r\n;।')
        if field in {'farmer', 'plot', 'crop'}:
            value = re.split(r'[;\n।]', value, maxsplit=1)[0].strip().rstrip('.')
        result[field] = value or None
    # Natural speech rules deliberately avoid extracting unsupported facts.
    if not result['farmer']:
        match = re.search(r'\b(?:visited|met)\s+(.+?)(?=\s+(?:at|in|on|and|whose|who|today|yesterday)\b|[.,;\n]|$)', raw, re.I)
        if match:
            result['farmer'] = re.sub(r"(?:'s|’s)?\s+farm$", '', match[1], flags=re.I).strip()
    for field, pattern in {
        'crop': r'\b(?:growing|crop is)\s+([^.;\n]+)',
        'plot': r'\b(?:plot|field)\s+([\w-]+)',
        'problem': r'\b(?:noticed|observed|problem is)\s+([^.;\n]+)',
        'advice': r'\b(?:advised|recommended|suggested)\s+([^.;\n]+)',
        'follow_up': r'\b(?:follow[ -]?up|come back|return|revisit|check again)\s+([^.;\n]+)',
    }.items():
        if not result[field]:
            match = re.search(pattern, raw, re.I)
            if match:
                result[field] = match[1].strip()
    if not result['follow_up']:
        match = RELATIVE.search(raw)
        if match:
            result['follow_up'] = match[0]
    result['no_problem'] = bool(NO_PROBLEM.search(result['problem'] or raw))
    result['due_date'] = due_date(result['follow_up'], visit_date)
    return result
