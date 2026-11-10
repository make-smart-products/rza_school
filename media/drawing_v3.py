"""Mobile-readable technical illustrations and high-quality H.264 animations."""
from functools import lru_cache
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W = H = 1080
PAPER, INK, NAVY = '#f5f8fc', '#193349', '#0b2438'
TEAL, BLUE, AMBER, RED = '#008b86', '#426adb', '#c47a12', '#c54848'
MUTED, LINE, PALE = '#52697c', '#cbd9e4', '#e4f3f2'
FPS, FRAME_COUNT = 20, 120


@lru_cache(maxsize=64)
def font(size, bold=False):
    paths = (['C:/Windows/Fonts/arialbd.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'] if bold else
             ['C:/Windows/Fonts/arial.ttf', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'])
    for path in paths:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    raise RuntimeError('A Cyrillic-capable font is required')


def lines(draw, value, face, width):
    result, line = [], ''
    for word in value.split():
        trial = (line+' '+word).strip()
        if line and draw.textlength(trial, font=face)>width:
            result.append(line); line=word
        else:
            line=trial
    return result+([line] if line else [])


def text(draw, value, box, size=42, color=INK, bold=False, align='left', minimum=34):
    value=str(value).translate(str.maketrans('₀₁₂₃₄₅₆₇₈₉','0123456789'))
    x,y,width,height=box
    for actual in range(size, minimum-1, -1):
        face=font(actual,bold); wrapped=lines(draw,value,face,width); step=int(actual*1.18)
        if len(wrapped)*step<=height and all(draw.textlength(s,font=face)<=width for s in wrapped):
            break
    else:
        raise ValueError('Text does not fit diagram: '+value)
    for line in wrapped:
        dx=(width-draw.textlength(line,font=face))/2 if align=='center' else 0
        if align=='right': dx=width-draw.textlength(line,font=face)
        draw.text((x+dx,y),line,font=face,fill=color)
        y+=step


def arrow(draw, start, end, color=TEAL, width=7, head=21):
    draw.line([start,end],fill=color,width=width)
    angle=math.atan2(end[1]-start[1],end[0]-start[0])
    draw.polygon([end,(end[0]-head*math.cos(angle-.48),end[1]-head*math.sin(angle-.48)),
                  (end[0]-head*math.cos(angle+.48),end[1]-head*math.sin(angle+.48))],fill=color)


def dashed(draw, start, end, color=MUTED, width=5):
    distance=math.dist(start,end)
    for offset in range(0,int(distance),20):
        a=offset/distance; b=min((offset+10)/distance,1)
        draw.line([(start[0]+a*(end[0]-start[0]),start[1]+a*(end[1]-start[1])),
                   (start[0]+b*(end[0]-start[0]),start[1]+b*(end[1]-start[1]))],fill=color,width=width)


def title_for(data):
    if data['kind']=='timing': return 'Время отключения'
    if data['kind']=='balance': return 'Баланс токов'
    return data['title']


def base(data):
    image=Image.new('RGB',(W,H),PAPER); draw=ImageDraw.Draw(image)
    draw.rectangle((0,0,W,225),fill=NAVY)
    text(draw,'РЗА / ШКОЛА РЕЛЕЙНОЙ ЗАЩИТЫ',(52,28,976,40),27,'#b9d8e5',minimum=27)
    text(draw,title_for(data),(52,88,976,132),55,'#ffffff',True,minimum=44)
    draw.rectangle((52,220,210,227),fill='#2bd3c7')
    return image,draw


def takeaway(draw, value, animated=False):
    draw.rounded_rectangle((48,890,1032,1008),radius=17,fill=PALE)
    draw.rectangle((48,907,54,990),fill=TEAL)
    text(draw,value,(80,909,920,86),35,INK,True,minimum=32)
    footer='Темп анимации условный • учебная модель' if animated else 'Упрощённая учебная схема'
    text(draw,footer,(52,1030,976,34),25,MUTED,minimum=25)


def family(data):
    if data['kind']=='editorial': return 'steps'
    if data['kind']!='concept': return data['kind']
    n=data['number']
    if n<=6:
        return {1:'relay',2:'selectivity',3:'steps',4:'steps',5:'steps',6:'relay'}[n]
    topic=(n-7)%24
    return {0:'relay',1:'ct',2:'polarity',3:'wave',4:'wave',5:'wave',7:'characteristic',
            9:'phasor',10:'differential',11:'differential',12:'wave',14:'phasor_zero'}.get(topic,'steps')


def is_animated(data):
    if data['kind']=='editorial': return False
    f=family(data)
    if f in ['timing','events','relay','phasor_zero']: return True
    return f=='steps' and data['number']>6 and (data['number']-7)%24 in [6,16,17,18,20,21]


def phase_time(values, progress):
    a,b,c=values
    if progress<.1: return 0,0
    if progress<.35: return a*(progress-.1)/.25,0
    if progress<.45: return a,0
    if progress<.55: return a+b*(progress-.45)/.1,1
    if progress<.65: return a+b,1
    if progress<.9: return a+b+c*(progress-.65)/.25,2
    return a+b+c,2


def timing(draw,data,p):
    values=data['values']; current,active=phase_time(values,p)
    text(draw,'Сейчас',(56,260,400,45),34,MUTED)
    text(draw,f't = {round(current)} мс',(56,309,968,100),88,INK,True,minimum=60)
    cumulative=0
    for i,(label,value,color) in enumerate(zip(['Защита','Передача команды','Выключатель'],values,[TEAL,AMBER,BLUE])):
        y=433+i*131; portion=max(0,min(1,(current-cumulative)/value)); cumulative+=value
        draw.ellipse((56,y,128,y+72),fill=color if i<=active else LINE)
        text(draw,str(i+1),(56,y+10,72,55),40,'#ffffff',True,'center')
        text(draw,label,(157,y+5,540,63),40,INK,True)
        text(draw,f'{value} мс',(728,y+5,300,63),43,color,True,'right')
        draw.rounded_rectangle((157,y+76,1028,y+91),radius=7,fill=LINE)
        if portion>0:
            draw.rounded_rectangle((157,y+76,157+871*portion,y+91),radius=7,fill=color)
    takeaway(draw,f"Полное время: {' + '.join(map(str,values))} = {sum(values)} мс",True)


def events(draw,data,p):
    a,b=data['values']; start,end=455,743
    text(draw,f"Δt = {data['gap']} мс",(56,279,968,114),90,INK,True,minimum=64)
    draw.line((112,start,112,end),fill=LINE,width=8)
    draw.line((112,start,112,start+(end-start)*p),fill=TEAL,width=8)
    for y,label,value,color in [(start,'Пуск',a,TEAL),(end,'Команда',b,BLUE)]:
        draw.ellipse((91,y-21,133,y+21),fill=color)
        text(draw,label,(178,y-39,750,60),43,color,True)
        text(draw,f'{value} мс',(178,y+25,750,85),64,INK,True,minimum=48)
    y=start+(end-start)*p
    draw.ellipse((98,y-14,126,y+14),fill=AMBER)
    takeaway(draw,f'{b} − {a} = {data["gap"]} мс. Одна шкала времени.',True)


def ct(draw,data):
    primary=data.get('primary','I1');secondary=data.get('secondary','I2'); k=data.get('k','K')
    text(draw,'Первичный ток',(56,296,430,68),39,TEAL,True)
    text(draw,'Вторичный ток',(594,296,430,68),39,BLUE,True,'right')
    text(draw,str(primary)+(' А' if 'primary' in data else ''),(56,371,430,103),76,INK,True,minimum=52)
    text(draw,str(secondary)+(' А' if 'secondary' in data else ''),(594,371,430,103),76,INK,True,'right',52)
    center=(540,616)
    draw.ellipse((423,499,657,733),fill='#d7e9ed',outline=NAVY,width=8)
    draw.ellipse((463,539,617,693),fill=PAPER,outline=NAVY,width=5)
    for angle in range(0,360,30):
        theta=math.radians(angle)
        x1,y1=center[0]+85*math.cos(theta),center[1]+85*math.sin(theta)
        x2,y2=center[0]+112*math.cos(theta),center[1]+112*math.sin(theta)
        draw.line((x1,y1,x2,y2),fill=NAVY,width=5)
    text(draw,f'K={k}' if isinstance(k,int) else 'K',(477,584,126,86),42,INK,True,'center',34)
    arrow(draw,(105,616),(395,616),TEAL)
    arrow(draw,(685,616),(975,616),BLUE)
    text(draw,'Трансформатор тока',(250,773,580,60),40,INK,True,'center')
    formula=f"I1 = {k} × {secondary} = {primary} А" if 'primary' in data else 'Идеальная модель: I1 = K × I2'
    takeaway(draw,formula)


def balance(draw,data):
    a,b=data.get('values',['I1','I2']); numeric='values' in data
    text(draw,'Вход',(56,290,430,58),38,TEAL,True)
    text(draw,'Выход',(594,290,430,58),38,BLUE,True,'right')
    text(draw,f'{a}'+(' мА' if numeric else ''),(56,355,430,93),63,INK,True,minimum=44)
    text(draw,f'{b}'+(' мА' if numeric else ''),(594,355,430,93),63,INK,True,'right',44)
    for start,end in [((395,493),(685,493)),((685,493),(685,760)),((685,760),(395,760)),((395,760),(395,493))]:
        dashed(draw,start,end,NAVY,4)
    text(draw,'Объект',(417,548,246,70),42,INK,True,'center')
    text(draw,'Одна база и фаза',(417,635,246,100),34,MUTED,False,'center')
    arrow(draw,(80,625),(370,625),TEAL)
    arrow(draw,(710,625),(1000,625),BLUE)
    takeaway(draw,f"Модуль разности: {data['difference']} мА" if numeric else data['note'])


def units(draw,data):
    text(draw,'Миллисекунды',(56,280,968,65),42,MUTED,False,'center')
    text(draw,f"{data['ms']} мс",(56,354,968,119),102,INK,True,'center',72)
    arrow(draw,(540,509),(540,649),TEAL,8,24)
    draw.rounded_rectangle((354,532,726,621),radius=20,fill=PALE)
    text(draw,'÷ 1000',(354,544,372,73),55,TEAL,True,'center')
    text(draw,f"{data['seconds']} с",(56,687,968,119),102,INK,True,'center',72)
    takeaway(draw,'1 с = 1000 мс. Сначала приведите единицы.')


def relay(draw,data,p):
    opened=p>=.67; active=p>=.32
    draw.line((80,450,720,450),fill=LINE if opened else TEAL,width=9)
    draw.line((834,450,1000,450),fill=LINE if opened else TEAL,width=9)
    draw.ellipse((280,381,420,521),outline=NAVY,width=8)
    text(draw,'ТТ',(255,301,190,63),44,INK,True,'center')
    if not opened: arrow(draw,(132,450),(214,450),TEAL)
    draw.ellipse((715,443,729,457),fill=NAVY);draw.ellipse((827,443,841,457),fill=NAVY)
    draw.line((722,450,834,389 if opened else 450),fill=AMBER if opened else NAVY,width=9)
    text(draw,'Выключатель',(676,301,350,63),38,INK,True,'center')
    dashed(draw,(350,535),(350,665),TEAL)
    dashed(draw,(350,665),(505,665),TEAL)
    draw.rounded_rectangle((505,578,762,754),radius=20,fill=NAVY)
    text(draw,'Релейная защита',(530,616,207,115),38,'#ffffff',True,'center')
    dashed(draw,(777,665),(897,665),AMBER if active else MUTED)
    dashed(draw,(897,665),(897,489),AMBER if active else MUTED)
    if active: draw.ellipse((872,640,922,690),fill=AMBER)
    labels=['1. Измерение','2. Условия выполнены','3. Команда отключения']
    phase=min(2,int(p*3))
    text(draw,labels[phase],(56,802,968,64),42,INK,True,'center')
    takeaway(draw,'Пример действия защиты при выполнении условий.',True)


def selectivity(draw,data):
    text(draw,'Цель: отключить повреждённый участок',(56,276,968,112),46,INK,True)
    draw.line((540,399,540,470),fill=NAVY,width=8)
    draw.line((240,470,840,470),fill=NAVY,width=8)
    for x in [240,840]:
        draw.line((x,470,x,560),fill=NAVY,width=8)
        draw.ellipse((x-8,553,x+8,569),fill=NAVY)
        draw.ellipse((x-8,638,x+8,654),fill=NAVY)
        draw.line((x,560,x+52 if x==240 else x,646),fill=RED if x==240 else TEAL,width=8)
        draw.line((x,654,x,788),fill=LINE if x==240 else TEAL,width=8)
    draw.line((209,756,271,818),fill=RED,width=8);draw.line((271,756,209,818),fill=RED,width=8)
    text(draw,'Повреждение',(68,828,380,60),38,RED,True,'center')
    text(draw,'Питание сохранено',(640,778,370,98),38,TEAL,True,'center')
    takeaway(draw,'Исправные присоединения по возможности остаются в работе.')


def phasors(draw,data,p,zero=False,polarity=False):
    center=(540,561); radius=199
    draw.ellipse((341,362,739,760),outline=LINE,width=3)
    draw.line((269,561,811,561),fill=LINE,width=3);draw.line((540,315,540,807),fill=LINE,width=3)
    angles=[0,math.pi] if polarity else ([p*2*math.pi,p*2*math.pi+2*math.pi/3,p*2*math.pi+4*math.pi/3] if zero else [0,-.7])
    names=['I','−I'] if polarity else (['IA','IB','IC'] if zero else ['U','I'])
    for angle,label,color in zip(angles,names,[TEAL,BLUE,AMBER]):
        end=(center[0]+radius*math.cos(angle),center[1]-radius*math.sin(angle))
        arrow(draw,center,end,color,7,23)
        lx=center[0]+(radius+61)*math.cos(angle)-60;ly=center[1]-(radius+49)*math.sin(angle)-25
        text(draw,label,(lx,ly,120,60),43,color,True,'center')
    if zero:
        takeaway(draw,'Симметричный пример: IA + IB + IC = 0.',True)
    elif polarity:
        takeaway(draw,'Модуль одинаковый, направления противоположны.')
    else:
        takeaway(draw,'Для направления важны фазовые соотношения.')


def waveform(draw,data):
    topic=(data['number']-7)%24
    clipped=topic==3
    text(draw,'Нормированные сигналы',(56,287,968,67),42,INK,True)
    text(draw,'Идеально' if clipped else 'Сигнал A',(145,355,390,58),34,TEAL,True)
    text(draw,'Искажено' if clipped else 'Сигнал B',(590,355,390,58),34,BLUE,True,'right')
    arrow(draw,(95,785),(985,785),MUTED,4,16)
    draw.line((95,385,95,785),fill=MUTED,width=4)
    draw.line((95,585,985,585),fill=LINE,width=3)
    for index,color in [(0,TEAL),(1,BLUE)]:
        points=[]
        for j in range(301):
            angle=j/300*4*math.pi
            value=math.sin(angle)
            if index==1:
                value=max(-.48,min(.48,value)) if clipped else .72*math.sin(angle-.7)
            points.append((100+j/300*875,585-value*155))
        draw.line(points,fill=color,width=6)
    text(draw,'Условная форма, не осциллограмма измерения',(100,806,890,65),32,MUTED,minimum=30)
    takeaway(draw,data['note'])


def characteristic(draw,data):
    text(draw,'Качественное сравнение',(56,279,968,64),42,INK,True)
    arrow(draw,(113,804),(984,804),MUTED,4,18);arrow(draw,(113,804),(113,374),MUTED,4,18)
    text(draw,'t',(57,357,55,58),43,INK,True);text(draw,'I',(990,786,50,58),43,INK,True)
    draw.line((153,527,963,527),fill=TEAL,width=7)
    points=[(153+i/200*810,421+335*(1-math.exp(-i/200*3))) for i in range(201)]
    draw.line(points,fill=BLUE,width=7)
    text(draw,'Независимая',(405,439,550,65),40,TEAL,True)
    text(draw,'Зависимая',(515,625,430,65),40,BLUE,True)
    takeaway(draw,'Характеристики сравнивают во всём нужном диапазоне.')


def steps(draw,data,p):
    labels=data['nodes']; animated=is_animated(data); active=min(len(labels)-1,int(p*len(labels)))
    draw.line((97,384,97,772),fill=LINE,width=6)
    for i,label in enumerate(labels):
        y=321+i*178; color=TEAL if not animated or i<=active else MUTED
        draw.rounded_rectangle((146,y,1028,y+133),radius=20,fill=PALE if i==active and animated else '#eaf0f6')
        draw.ellipse((57,y+35,137,y+115),fill=color)
        text(draw,str(i+1),(57,y+48,80,65),43,'#ffffff',True,'center')
        text(draw,label,(176,y+30,815,103),44,INK,True,minimum=36)
    takeaway(draw,data['note'],animated)


def draw_frame(data, progress=1):
    if data.get('illustration') in ['helmet-technician','cartoon-electrician']:
        return operation_card(data)
    image,draw=base(data); f=family(data)
    if f=='timing': timing(draw,data,progress)
    elif f=='events': events(draw,data,progress)
    elif f in ['ratio','ct']: ct(draw,data)
    elif f in ['balance','differential']: balance(draw,data)
    elif f=='units': units(draw,data)
    elif f=='relay': relay(draw,data,progress)
    elif f=='selectivity': selectivity(draw,data)
    elif f=='phasor_zero': phasors(draw,data,progress,zero=True)
    elif f=='phasor': phasors(draw,data,progress)
    elif f=='polarity': phasors(draw,data,progress,polarity=True)
    elif f=='wave': waveform(draw,data)
    elif f=='characteristic': characteristic(draw,data)
    else: steps(draw,data,progress)
    return image


def illustration_path(data):
    root = Path(__file__).resolve().parents[1]
    if data.get('illustration') == 'helmet-technician':
        return root / 'assets/relay-technician-helmet.jpg'
    relative = Path(data['illustration_asset'])
    asset = (root / relative).resolve()
    if not asset.is_relative_to(root/'assets/illustrations') or asset.suffix.lower() != '.jpg':
        raise ValueError('Illustration must be a project JPG in assets/illustrations')
    return asset


def operation_card(data):
    image, draw = base(data)
    asset = illustration_path(data)
    # Fit the illustration without cropping the hard hat or equipment.
    with Image.open(asset) as original:
        width = 820
        height = round(original.height * width / original.width)
        illustration = original.convert('RGB').resize((width, height), Image.Resampling.LANCZOS)
    image.paste(illustration, ((W-width)//2, 248))
    top = 248 + height + 20
    for i, label in enumerate(data['nodes']):
        y = top + i*76
        draw.ellipse((52, y+3, 101, y+52), fill=TEAL)
        text(draw, str(i+1), (52,y+7,49,43), 29, '#ffffff', True, 'center', minimum=29)
        text(draw, label, (123,y,905,69), 33, INK, True, minimum=29)
    text(draw, 'ЭКСПЛУАТАЦИЯ РЗА • ' + data.get('voltage_class','6–10 кВ'), (52,1052,976,28), 23, MUTED, minimum=23)
    return image


def encode_animation(data,path):
    import imageio_ffmpeg
    encoder=imageio_ffmpeg.write_frames(str(path),(W,H),fps=FPS,codec='libx264',pix_fmt_in='rgb24',pix_fmt_out='yuv420p',
        quality=None,macro_block_size=2,ffmpeg_log_level='error',output_params=['-crf','17','-preset','fast','-movflags','+faststart'])
    encoder.send(None)
    try:
        for i in range(FRAME_COUNT):
            # Initial and final holds help readers identify the states before the loop restarts.
            progress=max(0,min(1,(i-10)/(FRAME_COUNT-31)))
            encoder.send(draw_frame(data,progress).tobytes())
    finally:
        encoder.close()
    return FRAME_COUNT/FPS
