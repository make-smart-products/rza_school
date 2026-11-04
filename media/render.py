"""Deterministic educational cards. No AI service or network is used."""
import argparse
import hashlib
import html
import json
import math
import re
from decimal import Decimal
from pathlib import Path
from functools import lru_cache

from PIL import Image, ImageDraw, ImageFont

VERSION = 2
W, H = 1200, 900
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


@lru_cache(maxsize=32)
def font(size, bold=False):
    names = (['C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else
             ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for name in names:
        if Path(name).exists():
            return ImageFont.truetype(name, size)
    raise RuntimeError('A Cyrillic-capable Arial or DejaVu Sans font is required')


def wrap(draw, text, face, width):
    lines, line = [], ''
    for word in text.split():
        trial = (line + ' ' + word).strip()
        if line and draw.textlength(trial, font=face) > width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + ([line] if line else [])


def block(draw, text, xy, width, size=28, color=INK, bold=False, center=False):
    text=text.translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789'))
    face = font(size, bold)
    x, y = xy
    for line in wrap(draw, text, face, width):
        dx = (width - draw.textlength(line, font=face)) / 2 if center else 0
        draw.text((x + dx, y), line, font=face, fill=color)
        y += int(size * 1.35)
    return y


def decimal(value):
    return format(value, 'f').rstrip('0').rstrip('.').replace('.', ',') if '.' in format(value, 'f') else str(value)


def describe(name, source):
    number = int(re.match(r'\d+', Path(name).stem).group())
    data = {'number': number, 'source': source}
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
    text+='\n\nУчебная модель, не готовые уставки оборудования.\n#РЗА #ШколаРЗА'
    if len(text.encode('utf-16-le'))//2>1024: raise ValueError('Caption exceeds Telegram limit; content was not truncated')
    parts=text.split('\n\n')
    formatted=['<b>'+html.escape(parts[0])+'</b>']
    for part in parts[1:]:
        escaped=html.escape(part)
        escaped=re.sub(r'^(Дано|Найти|Решение|Вывод|Вопрос|Ответ|Разбор):',r'<b>\1:</b>',escaped)
        formatted.append(escaped)
    return text,'\n\n'.join(formatted)


def base(data):
    im=Image.new('RGB',(W,H),BG); draw=ImageDraw.Draw(im)
    block(draw,'РЗА  /  ШКОЛА РЕЛЕЙНОЙ ЗАЩИТЫ',(64,35),1070,20,MUTED)
    block(draw,data['title'],(64,100),1070,44,INK,True)
    draw.rounded_rectangle((64,240,1136,247),radius=3,fill=ACCENT)
    draw.rounded_rectangle((45,285,1155,720),radius=24,fill=PANEL)
    if data['kind'] in ['timing','events']:
        block(draw,'Темп анимации условный; показана последовательность',(64,753),1070,21,MUTED)
    block(draw,'Учебная схема • реальные алгоритмы зависят от проекта',(64,817),1070,20,MUTED)
    return im,draw


def arrow(draw,x1,y,x2,color=ACCENT):
    draw.line((x1,y,x2,y),fill=color,width=5)
    draw.polygon([(x2,y),(x2-13,y-8),(x2-13,y+8)],fill=color)


def nodes(draw,labels,active=-1):
    count=len(labels); gap=38; width=(1032-gap*(count-1))/count; x=84
    for i,label in enumerate(labels):
        rect=(x,385,x+width,580)
        draw.rounded_rectangle(rect,radius=18,fill=BG,outline=AMBER if i==active else ACCENT,width=3)
        block(draw,label,(x+15,432),width-30,27,AMBER if i==active else INK,True,True)
        if i<count-1: arrow(draw,x+width+5,480,x+width+gap-5)
        x+=width+gap


def frame(data,progress=1):
    im,draw=base(data); kind=data['kind']
    if kind=='concept':
        nodes(draw,data['nodes'])
        block(draw,data['note'],(85,635),1030,24,MUTED,False,True)
    elif kind=='ratio':
        nodes(draw,[f"I₁ = {data['primary']} А",f"K = {data['k']}",f"I₂ = {data['secondary']} А"])
        block(draw,'I₁ = K × I₂',(85,635),1030,31,AMBER,True,True)
    elif kind=='timing':
        values=data['values']; labels=['Защита','Команда','Выключатель']; total=data['total']; x=95
        for value,label,color in zip(values,labels,[ACCENT,AMBER,'#94bafa']):
            width=1010*value/total
            draw.rectangle((x,465,x+width,520),fill=color)
            x+=width
        x=95+1010*progress
        draw.line((x,435,x,550),fill=INK,width=4)
        draw.ellipse((x-9,421,x+9,439),fill=INK)
        for i,(value,label) in enumerate(zip(values,labels)):
            block(draw,f'{label}: {value} мс',(95+i*345,350),325,25,INK,True)
        block(draw,f"t = {' + '.join(map(str,values))} = {total} мс",(95,605),1010,34,INK,True,True)
        block(draw,'Последовательная модель: этапы не перекрываются',(95,660),1010,22,MUTED,False,True)
    elif kind=='events':
        a,b=data['values']; arrow(draw,115,480,1085)
        for x,label in [(190,f'Пуск: {a} мс'),(1000,f'Команда: {b} мс')]:
            draw.line((x,450,x,510),fill=INK,width=4)
            block(draw,label,(x-145,370),290,26,INK,True,True)
        x=190+810*progress; draw.ellipse((x-14,466,x+14,494),fill=AMBER)
        block(draw,f"Δt = {b} − {a} = {data['gap']} мс",(100,600),1000,36,INK,True,True)
        block(draw,'Одна шкала времени; сравниваем отметки',(100,665),1000,23,MUTED,False,True)
    elif kind=='balance':
        a,b=data['values']; nodes(draw,[f'Iвх = {a} мА','Одна база и фаза',f'Iвых = {b} мА'])
        block(draw,f"|Iвх − Iвых| = {data['difference']} мА",(85,635),1030,32,AMBER,True,True)
    else:
        nodes(draw,[f"{data['ms']} мс",'÷ 1000',f"{data['seconds']} с"])
        block(draw,'1 с = 1000 мс',(85,635),1030,32,AMBER,True,True)
    return im


def render(path,output):
    path=Path(path); output=Path(output); output.mkdir(parents=True,exist_ok=True)
    source=path.read_text(encoding='utf-8-sig').strip(); data=describe(path.name,source)
    plain,formatted=caption(data)
    animation=data['kind'] in ['timing','events']
    asset=output/(path.stem+('.gif' if animation else '.png'))
    if animation:
        frames=[frame(data,i/23).convert('P',palette=Image.Palette.ADAPTIVE,colors=96) for i in range(24)]
        frames[0].save(asset,save_all=True,append_images=frames[1:],duration=[110]*23+[1500],loop=0,optimize=True,disposal=2)
    else:
        frame(data).save(asset,optimize=True)
    result={'path':str(asset.resolve()),'kind':'animation' if animation else 'photo','caption':plain,'caption_html':formatted,'caption_sha256':hashlib.sha256(plain.encode()).hexdigest(),'source_sha256':hashlib.sha256(source.encode()).hexdigest(),'version':VERSION,'render_sha256':hashlib.sha256(asset.read_bytes()).hexdigest()}
    (output/(path.stem+'.json')).write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    return result


if __name__=='__main__':
    parser=argparse.ArgumentParser(); parser.add_argument('--file',required=True);parser.add_argument('--output-dir',default='media/generated')
    args=parser.parse_args();print(json.dumps(render(args.file,args.output_dir),ensure_ascii=True))
