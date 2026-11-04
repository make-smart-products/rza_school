"""Update existing messages in place; every confirmed edit has a durable receipt."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys
import time
import urllib.error
import urllib.request
import uuid

from render import render, VERSION


def load_token(root):
    if os.environ.get('TELEGRAM_BOT_TOKEN'):
        return os.environ['TELEGRAM_BOT_TOKEN'].strip()
    for line in (root/'.env').read_text(encoding='utf-8-sig').splitlines():
        key,sep,value=line.partition('=')
        if sep and key.strip()=='TELEGRAM_BOT_TOKEN':
            return value.strip().strip('"').strip("'")
    raise ValueError('Missing local bot token')


def save(path,value):
    temp=path.with_suffix('.tmp')
    temp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    os.replace(temp,path)


def edit(token,message_id,draft):
    asset=Path(draft['path']); boundary=uuid.uuid4().hex
    media={'type':draft['kind'],'media':'attach://asset','caption':draft['caption_html'],'parse_mode':'HTML'}
    fields={'chat_id':'@rza_school','message_id':str(message_id),'media':json.dumps(media,ensure_ascii=False)}
    chunks=[]
    for key,value in fields.items():
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n').encode())
    mime='image/gif' if draft['kind']=='animation' else 'image/png'
    if draft['kind']=='animation' and asset.suffix.lower()=='.mp4': mime='video/mp4'
    chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="asset"; filename="{asset.name}"\r\nContent-Type: {mime}\r\n\r\n').encode()+asset.read_bytes()+b'\r\n')
    chunks.append((f'--{boundary}--\r\n').encode())
    payload=b''.join(chunks)
    for attempt in range(6):
        request=urllib.request.Request('https://api.telegram.org/bot'+token+'/editMessageMedia',data=payload,headers={'Content-Type':'multipart/form-data; boundary='+boundary})
        try:
            with urllib.request.urlopen(request,timeout=90) as response:
                result=json.load(response)
            break
        except urllib.error.HTTPError as error:
            result=json.load(error)
            if error.code==429 and result.get('ok') is False and attempt<5:
                seconds=result.get('parameters',{}).get('retry_after',15)
                if not isinstance(seconds,int) or not 1<=seconds<=300: raise RuntimeError('Invalid Telegram retry interval')
                print(json.dumps({'rate_limit_wait_seconds':seconds}),flush=True)
                time.sleep(seconds+1)
                continue
            description=str(result.get('description','')).replace(token,'[redacted]')
            raise RuntimeError(f'Telegram HTTP {error.code}: {description}') from None
        except (urllib.error.URLError,TimeoutError,OSError):
            # Repeating an identical edit of a fixed message ID cannot create a duplicate post.
            if attempt==5: raise RuntimeError('Network error; verify this message before resuming') from None
            time.sleep(3*(attempt+1))
    else:
        raise RuntimeError('Telegram did not confirm the edit')
    message=result.get('result',{})
    if not result.get('ok') or message.get('message_id')!=message_id: raise RuntimeError('Unexpected edit response')
    if message.get('caption')!=draft['caption']: raise RuntimeError('Telegram returned a different caption')
    if draft['kind']=='animation':
        media=message.get('animation',{})
    else:
        photos=message.get('photo',[]); media=photos[-1] if photos else {}
    if not media.get('file_id'): raise RuntimeError('Telegram did not confirm attached media')
    return {'message_id':message_id,'media_type':draft['kind'],'media_file_id':media['file_id'],'media_version':VERSION,'caption_sha256':draft['caption_sha256'],'render_sha256':draft['render_sha256'],'edit_date':message.get('edit_date')}


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--state',required=True);parser.add_argument('--receipts',default='output/media-edit-receipts.json');parser.add_argument('--only',default='');parser.add_argument('--welcome',action='store_true');parser.add_argument('--delay',type=float,default=3.2)
    args=parser.parse_args();root=Path(__file__).resolve().parents[1]
    state=json.loads((root/args.state).read_text(encoding='utf-8')); receipts_path=root/args.receipts
    receipts=json.loads(receipts_path.read_text(encoding='utf-8')) if receipts_path.exists() else []
    done={(r['file'],r['message_id'],r['media_version']) for r in receipts}
    selected=set(args.only.split(',')) if args.only else None
    items=[p for p in state if p['status']=='sent']
    if args.welcome: items.insert(0,{'file':'001-welcome.txt','message_id':2,'status':'sent','welcome':True})
    token=load_token(root)
    for item in items:
        name=item['file'];message_id=item['message_id']
        if selected and name not in selected: continue
        if (name,message_id,VERSION) in done: continue
        if item.get('welcome'): source=root/'posts/001-welcome.txt'
        else:
            source=root/'output/stock/posts'/name
            if not source.exists(): source=root/'posts/lessons'/name
        draft=render(source,root/'media/generated')
        if item.get('sha256') and item['sha256']!=draft['source_sha256']: raise RuntimeError('Source differs from published history: '+name)
        receipt=edit(token,message_id,draft)
        receipt.update(file=name,source_sha256=draft['source_sha256'])
        receipts.append(receipt);save(receipts_path,receipts)
        print(json.dumps({'updated':name,'message_id':message_id,'kind':receipt['media_type'],'confirmed_edits':len(receipts)}),flush=True)
        time.sleep(args.delay)
    print('MEDIA_UPGRADE_COMPLETE',flush=True)


if __name__=='__main__':
    try: main()
    except Exception as error:
        print('MEDIA_UPGRADE_STOPPED: '+str(error),file=sys.stderr)
        sys.exit(1)
