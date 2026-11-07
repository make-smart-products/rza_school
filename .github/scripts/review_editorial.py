"""Review the actual queue before its first Telegram delivery in each run."""
import json
import hashlib
import os
from pathlib import Path
import re
import sys
import unicodedata

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'media'))
from render import caption, describe, editorial_sources, frame
from drawing_v3 import illustration_path


def words(text):
    normalized = unicodedata.normalize('NFKC', text).casefold().replace('ё', 'е')
    return re.findall(r'[^\W\d_]+', normalized)


def fingerprint(body):
    tokens = words('\n'.join(body.splitlines()[1:]))
    return set(zip(tokens, tokens[1:], tokens[2:], tokens[3:], tokens[4:]))


def review(queue, state, catalog):
    sources = editorial_sources()
    published = {entry['file'] for entry in state}
    lessons = {entry['file']: entry for entry in catalog}
    history = []
    ready = []
    artwork = {}
    for lesson in catalog:
        if lesson.get('editorial_profile') != 'equipment':
            continue
        if lesson.get('illustration') != 'cartoon-electrician':
            raise ValueError(f"{lesson['file']}: нужна мультяшная иллюстрация энергетика")
        asset = illustration_path(lesson)
        digest = hashlib.sha256(asset.read_bytes()).hexdigest()
        if digest in artwork:
            raise ValueError(f"{lesson['file']}: изображение повторяет {artwork[digest]}")
        artwork[digest] = lesson['file']
    for path in sorted(queue.glob('*.txt')):
        body = path.read_text(encoding='utf-8-sig').strip()
        lesson = lessons.get(path.name)
        title = lesson['title'] if lesson else body.splitlines()[0]
        record = (path.name, tuple(words(title)), fingerprint(body))
        if path.name in published:
            history.append(record)
            continue
        ready.append((record, body, lesson))

    for (name, title, shingles), body, lesson in ready:
        if not lesson:
            raise ValueError(f'{name}: материал отсутствует в редакционном каталоге')
        unknown_sources = set(lesson['source_ids']) - sources.keys()
        if unknown_sources:
            raise ValueError(f'{name}: неизвестные источники {sorted(unknown_sources)}')
        if lesson.get('editorial_profile') != 'equipment':
            raise ValueError(f'{name}: для новой публикации нужен профиль equipment')
        if lesson.get('illustration') != 'cartoon-electrician':
            raise ValueError(f'{name}: нужна мультяшная иллюстрация энергетика')
        if not re.search(r'\n\n(?:Проектирование|Эксплуатация|Наладка)\. .+', body):
            raise ValueError(f'{name}: отсутствует инженерный разбор')
        if not re.search(r'\n\nПроверка на объекте: .{35,}', body):
            raise ValueError(f'{name}: отсутствует конкретная проверка на объекте')
        for other, other_title, other_shingles in history:
            common = len(shingles & other_shingles)
            union = len(shingles | other_shingles)
            if title == other_title or (common >= 12 and common / union >= 0.75):
                raise ValueError(f'{name}: возможный повтор {other}, требуется редактура')
        data = describe(name, body)
        caption(data)
        frame(data)
        history.append((name, title, shingles))

    return len(ready)


if __name__ == '__main__':
    state_path = ROOT / '.publisher-state.json'
    state = json.loads(state_path.read_text(encoding='utf-8')) if state_path.exists() else []
    catalog = json.loads((ROOT / 'content/advanced.json').read_text(encoding='utf-8'))
    try:
        count = review(ROOT / 'posts/lessons', state, catalog)
    except (ValueError, KeyError) as error:
        sys.exit(f'Редакционная проверка остановила публикацию: {error}')
    message = f'Редакционная проверка пройдена. Готовых материалов: {count}.'
    if not count:
        message = 'Редакционная очередь пуста. Для продолжения нужен новый проверенный материал.'
    print(message)
    if summary := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(summary, 'a', encoding='utf-8') as report:
            report.write(message + '\n')
