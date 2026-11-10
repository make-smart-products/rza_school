"""Deterministic educational cards. No AI service or network is used."""
import argparse
import hashlib
import html
import json
import re
from decimal import Decimal
from pathlib import Path

from drawing_v3 import draw_frame, encode_animation, is_animated, illustration_path, W, H

VERSION = 4
CONTENT_DIR = Path(__file__).resolve().parents[1] / 'content'
BG, PANEL, INK, MUTED, ACCENT, AMBER = '#081b2b', '#123047', '#f1f7fb', '#b5cbd8', '#31d7d0', '#ffca70'
PLANS = [
    ('Измерительная цепочка', ['Силовая цепь', 'ТТ / ТН', 'Терминал', 'Команда'], 'Результат зависит от всей цепи измерения.'),
    ('Первичные и вторичные величины', ['Первичная сторона', 'Коэффициент K', 'Вторичная сторона'], 'Сравнивайте величины, приведённые к одной стороне.'),
    ('Полярность измерений', ['Значение', 'Направление', 'Фазовый угол'], 'Одинаковые модули ещё не означают одинаковые фазоры.'),
    ('Насыщение трансформатора тока', ['Первичный ток', 'Магнитопровод', 'Искажённый сигнал'], 'Идеальная пропорция имеет границы применимости.'),
    ('Напряжение в алгоритме', ['Ток', 'Напряжение', 'Логика функции'], 'Состав необходимых сигналов зависит от функции.'),
    ('Перегрузка или повреждение?', ['Величина тока', 'Длительность', 'Контекст режима'], 'Повышенный ток сам по себе не устанавливает причину.'),
    ('От пуска к действию', ['Пуск', 'Логические условия', 'Выходная команда'], 'Пуск не всегда завершается отключением.'),
    ('Временная характеристика', ['Значение тока', 'Характеристика', 'Время действия'], 'Сравнивают весь требуемый диапазон, а не одну точку.'),
    ('Согласование токовых функций', ['Условия пуска', 'Зона действия', 'Время / логика'], 'Название функции не заменяет описание алгоритма.'),
    ('Направленность', ['Измерения', 'Фазовые соотношения', 'Решение о направлении'], 'Один модуль тока не определяет направление.'),
    ('Дифференциальный принцип', ['Токи границ зоны', 'Приведение', 'Сравнение'], 'Учитываются коэффициенты, направления и фазы.'),
    ('Граница защищаемой зоны', ['ТТ на входе', 'Защищаемый объект', 'ТТ на выходе'], 'Место повреждения оценивают относительно границ зоны.'),
    ('Включение трансформатора', ['Момент включения', 'Переходный ток', 'Анализ признаков'], 'Большой ток не всегда означает внутреннее повреждение.'),
    ('Замыкание на землю', ['Режим нейтрали', 'Схема сети', 'Признаки повреждения'], 'Решение для одной сети нельзя переносить автоматически.'),
    ('Нулевая последовательность', ['Фазор IА', '+ IВ + IС', '= 3I₀'], 'Это векторная сумма, а не сумма модулей.'),
    ('Основная и резервная защита', ['Основная цепочка', 'Контроль отказа', 'Резервное действие'], 'Резерв может иметь другое время и охват отключений.'),
    ('Резервирование отказа выключателя', ['Команда', 'Контроль отключения', 'Логика УРОВ'], 'Пуск и окончательное действие — разные события.'),
    ('Повторное включение', ['Отключение', 'Разрешения / запреты', 'Условия АПВ'], 'Разрешение повторного включения проверяют отдельно.'),
    ('Ввод резервного питания', ['Основной источник', 'Готовность резерва', 'Логика АВР'], 'Потеря основного питания не доказывает готовность резерва.'),
    ('Оперативное питание', ['Питание терминала', 'Цепь команды', 'Исполнительный орган'], 'Работа экрана не подтверждает исправность всей цепочки.'),
    ('Значение дискретного сигнала', ['Контакт', 'Вход 0 / 1', 'Принятый смысл'], 'Смысл нуля и единицы задаётся конкретной схемой.'),
    ('Восстановление последовательности', ['События', 'Общая шкала времени', 'Осциллограмма'], 'Для разных устройств важны синхронизация и точность.'),
    ('Как читать параметр', ['Название', 'Единицы и база', 'Документация'], 'Одного числового значения недостаточно.'),
    ('Границы учебной модели', ['Допущения', 'Расчёт', 'Область применимости'], 'Учебный ответ не заменяет расчёт конкретного объекта.'),
]
INTRO = [
    ('Что делает релейная защита', ['Измеряет', 'Выявляет условия', 'Выдаёт команду'], 'Силовую цепь размыкает выключатель.'),
    ('Селективность', ['Повреждённый участок', 'Его защита', 'Ограничение отключения'], 'Цель — по возможности сохранить исправные присоединения.'),
    ('Быстродействие', ['Время защиты', 'Передача команды', 'Выключатель'], 'Время защиты и полное время отключения различаются.'),
    ('Чувствительность', ['Зона действия', 'Режимы сети', 'Выявление повреждений'], 'Проверка одного режима не даёт полной картины.'),
    ('Надёжность', ['Нужное действие', 'Правильный момент', 'Отсутствие лишнего действия'], 'Рассматривают всю систему, а не только терминал.'),
    ('Защита и выключатель', ['Входные сигналы', 'Решение защиты', 'Отключение цепи'], 'Команда и её исполнение — разные этапы.'),
]


def decimal(value):
    return format(value, 'f').rstrip('0').rstrip('.').replace('.', ',') if '.' in format(value, 'f') else str(value)


def editorial_sources():
    references = (CONTENT_DIR / 'ADVANCED_SOURCES.md').read_text(encoding='utf-8')
    return dict(re.findall(r'^- ([A-Z]+\d+) — \[[^\n]+?\]\((https://[^\s)]+)\)', references, re.M))


def describe(name, source):
    number = int(re.match(r'\d+', Path(name).stem).group())
    data = {'number': number, 'source': source}
    if name.endswith('-advanced.txt'):
        catalog=json.loads((CONTENT_DIR/'advanced.json').read_text(encoding='utf-8'))
        lesson=next((p for p in catalog if p['file']==name),None)
        if lesson is None or source!=lesson['body']: raise ValueError('Editorial source differs from reviewed catalog')
        data.update(kind='editorial',title=lesson['title'],nodes=lesson['nodes'],note=lesson['note'],source_ids=lesson['source_ids'])
        if lesson.get('editorial_profile') == 'equipment':
            sources = editorial_sources()
            data['source_links'] = {key: sources[key] for key in lesson['source_ids']}
            data['illustration'] = lesson.get('illustration')
            data['illustration_asset'] = lesson.get('illustration_asset')
            data['voltage_class'] = lesson.get('voltage_class','6–10 кВ')
        return data
    if source.startswith('Учебная задача: первичный и вторичный ток'):
        match = re.search(r'коэффициент K = I₁/I₂ = (\d+).*?I₂ = (\d+),(\d+) А', source, re.S)
        if not match: raise ValueError('Unknown current-ratio task format')
        k = int(match[1]); secondary = Decimal(match[2]+'.'+match[3]); primary = secondary*k
        data.update(kind='ratio', title='Первичный и вторичный ток', k=k, secondary=decimal(secondary), primary=decimal(primary))
    elif source.startswith('Учебная задача: полное время отключения'):
        match = re.search(r'защиты — (\d+) мс.*?команды — (\d+) мс.*?выключателя — (\d+) мс', source, re.S)
        if not match: raise ValueError('Unknown timing task format')
        values = list(map(int, match.groups()))
        data.update(kind='timing', title='Из чего складывается время отключения', values=values, total=sum(values))
    elif source.startswith('Учебная задача: интервал между событиями'):
        values = list(map(int, re.findall(r'момент (\d+) мс', source)))
        if len(values) != 2 or values[1] < values[0]: raise ValueError('Unknown event task format')
        data.update(kind='events', title='Интервал между событиями', values=values, gap=values[1]-values[0])
    elif source.startswith('Учебная задача: баланс токов'):
        match = re.search(r'Iвх = (\d+) мА, Iвых = (\d+) мА', source)
        if not match: raise ValueError('Unknown current-balance task format')
        a,b=map(int,match.groups())
        data.update(kind='balance', title='Баланс токов в учебной модели', values=[a,b], difference=abs(a-b))
    elif source.startswith('Учебная задача: единицы времени'):
        match=re.search(r'интервал (\d+) мс',source)
        if not match: raise ValueError('Unknown units task format')
        ms=int(match[1]); data.update(kind='units',title='Миллисекунды и секунды',ms=ms,seconds=f'{ms//1000},{ms%1000:03d}')
    else:
        plan=INTRO[number-1] if number<=6 else PLANS[(number-7)%24]
        data.update(kind='concept',title=plan[0],nodes=plan[1],note=plan[2])
    return data


def caption(data):
    kind=data['kind']
    if kind=='ratio':
        text=f"{data['title']}\n\nДано: K = I₁/I₂ = {data['k']}; I₂ = {data['secondary']} А. Модель идеальная, без насыщения и погрешностей.\n\nНайти: первичный ток I₁.\n\nРешение: I₁ = K × I₂ = {data['k']} × {data['secondary']} = {data['primary']} А.\n\nВывод: перед сравнением токов приведите их к одной стороне."
    elif kind=='timing':
        a,b,c=data['values']; text=f"{data['title']}\n\nДано: защита — {a} мс; передача команды — {b} мс; выключатель — {c} мс. В учебной модели этапы идут последовательно и не перекрываются.\n\nРешение: t = {a} + {b} + {c} = {data['total']} мс.\n\nВывод: время действия защиты — только часть полного времени отключения."
    elif kind=='events':
        a,b=data['values']; text=f"{data['title']}\n\nДано: пуск — {a} мс; команда отключения — {b} мс. Обе отметки относятся к одной шкале времени.\n\nРешение: Δt = {b} − {a} = {data['gap']} мс.\n\nВывод: интервал вычислен, но причина задержки по двум отметкам не определяется. Для разных устройств дополнительно проверяют синхронизацию."
    elif kind=='balance':
        a,b=data['values']; text=f"{data['title']}\n\nДано: Iвх = {a} мА; Iвых = {b} мА. Токи синфазны, приведены к одной стороне и базе; направления учтены для вычитания.\n\nРешение: |Iвх − Iвых| = |{a} − {b}| = {data['difference']} мА.\n\nВывод: это арифметический небаланс. Он сам по себе не доказывает наличие повреждения; реальный алгоритм учитывает дополнительные условия."
    elif kind=='units':
        text=f"{data['title']}\n\nДано: интервал {data['ms']} мс. Представьте его в секундах.\n\nРешение: 1 с = 1000 мс; {data['ms']} ÷ 1000 = {data['seconds']} с.\n\nВывод: перед сравнением записей и расчётов приведите значения к одинаковым единицам."
    else:
        paragraphs=data['source'].split('\n\n')
        paragraphs=[p.strip() for p in paragraphs if p.strip() and not p.startswith('#') and not p.startswith('Учебный материал') and not p.startswith('Материал для изучения')]
        text='\n\n'.join(paragraphs).replace('Проверьте себя:', 'Вопрос:').replace('Ответ и пояснение:', 'Разбор:')
    if kind=='editorial': text+='\n\nИсточники: '+', '.join(data['source_ids'])
    text+='\n\nУчебная модель, не готовые уставки оборудования.\n#РЗА #ШколаРЗА'
    if len(text.encode('utf-16-le'))//2>1024: raise ValueError('Caption exceeds Telegram limit; content was not truncated')
    parts=text.split('\n\n')
    formatted=['<b>'+html.escape(parts[0])+'</b>']
    for part in parts[1:]:
        escaped=html.escape(part)
        escaped=re.sub(r'^(Дано|Найти|Решение|Вывод|Вопрос|Ответ|Разбор|Проверка на объекте):',r'<b>\1:</b>',escaped)
        escaped=re.sub(r'^(Проектирование|Эксплуатация|Наладка)\.',r'<b>\1.</b>',escaped)
        if part.startswith('Источники: ') and data.get('source_links'):
            links = [f'<a href="{html.escape(url, quote=True)}">{html.escape(key)}</a>'
                     for key, url in data['source_links'].items()]
            escaped = 'Источники: ' + ', '.join(links)
        formatted.append(escaped)
    formatted_text='\n\n'.join(formatted)
    if kind=='editorial' and not data.get('source_links'):
        formatted_text=formatted_text.replace('Источники:', '<a href="https://github.com/make-smart-products/rza_school/blob/main/content/ADVANCED_SOURCES.md">Источники:</a>')
    return text,formatted_text


def frame(data,progress=1):
    return draw_frame(data,progress)


def render(path,output):
    path=Path(path); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    source=path.read_text(encoding='utf-8-sig').strip(); data=describe(path.name,source)
    plain,formatted=caption(data)
    animation=is_animated(data)
    asset=output/(path.stem+('.mp4' if animation else '.png'))
    pipeline=Path(__file__).read_bytes()+(Path(__file__).parent/'drawing_v3.py').read_bytes()
    if data['kind']=='editorial':
        pipeline += (CONTENT_DIR/'advanced.json').read_bytes()
        if data.get('source_links'):
            pipeline += (CONTENT_DIR/'ADVANCED_SOURCES.md').read_bytes()
        if data.get('illustration') in ['helmet-technician','cartoon-electrician']:
            pipeline += illustration_path(data).read_bytes()
    pipeline_hash=hashlib.sha256(pipeline).hexdigest()
    metadata_path=output/(path.stem+'.json')
    source_hash=hashlib.sha256(source.encode()).hexdigest()
    if metadata_path.exists() and asset.exists():
        try:
            cached=json.loads(metadata_path.read_text(encoding='utf-8'))
            if cached.get('version')==VERSION and cached.get('source_sha256')==source_hash and cached.get('pipeline_sha256')==pipeline_hash and cached.get('render_sha256')==hashlib.sha256(asset.read_bytes()).hexdigest():
                return cached
        except (ValueError,OSError):
            pass
    duration=encode_animation(data,asset) if animation else 0
    if not animation:
        frame(data).save(asset,optimize=True)
    if not asset.exists() or asset.stat().st_size<100:
        raise RuntimeError('Media encoder did not create a valid asset')
    result={'path':str(asset.resolve()),'kind':'animation' if animation else 'photo','caption':plain,'caption_html':formatted,'caption_sha256':hashlib.sha256(plain.encode()).hexdigest(),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'version':VERSION,'render_sha256':hashlib.sha256(asset.read_bytes()).hexdigest()}
    result.update(pipeline_sha256=pipeline_hash,width=W,height=H,duration=duration,format='mp4' if animation else 'png')
    (output/(path.stem+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--file',required=True);parser.add_argument('--output-dir',default='media/generated')
    args=parser.parse_args();print(json.dumps(render(args.file,args.output_dir),ensure_ascii=True))
