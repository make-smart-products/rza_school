"""Deliver up to ten unique queue entries per hour while the runner is active."""
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[2]
CLOCK = ROOT / '.publication-clock.json'
INTERVAL = 3600
RUN_BUDGET = 330 * 60


def run(*args, env=None):
    subprocess.run(args, cwd=ROOT, env=env, check=True)


def remaining():
    state = json.loads((ROOT/'.publisher-state.json').read_text(encoding='utf-8'))
    if any(p['status'] != 'sent' for p in state):
        raise ValueError('Unresolved Telegram delivery requires reconciliation')
    sent = {p['file'] for p in state}
    return [p for p in (ROOT/'posts/lessons').glob('*.txt') if p.name not in sent]


def read_clock():
    if not CLOCK.exists():
        return {}
    clock = json.loads(CLOCK.read_text(encoding='utf-8'))
    started = clock.get('last_batch_started_at', 0)
    if not isinstance(started, (int, float)) or started < 0 or started > time.time()+60:
        raise ValueError('Invalid persisted batch time')
    return clock


def wait_seconds(clock, now):
    return max(0, clock.get('last_batch_started_at', 0)+INTERVAL-now)


def save_clock(clock, message):
    CLOCK.write_text(json.dumps(clock, indent=2)+'\n', encoding='utf-8', newline='\n')
    run('git', 'add', '.publication-clock.json')
    result = subprocess.run(['git','diff','--cached','--quiet'],cwd=ROOT)
    if result.returncode == 0:
        return
    if result.returncode != 1:
        raise RuntimeError('Could not inspect staged clock')
    run('git','commit','-m',message)
    # Persist the clock before the batch. Failure stops delivery instead of
    # allowing another workflow to send a second batch inside the same hour.
    run('git','push','origin','HEAD:'+os.environ['DEFAULT_BRANCH'])


def report(message):
    print(message,flush=True)
    if path := os.environ.get('GITHUB_STEP_SUMMARY'):
        with open(path,'a',encoding='utf-8') as output:
            output.write(message+'\n\n')


def main():
    deadline = time.monotonic()+RUN_BUDGET
    target = int(os.environ.get('TARGET_TOTAL','0'))
    if target < 0 or target > 1_000_000:
        raise ValueError('Invalid catch-up target')
    run('git','config','user.name','rza-publisher[bot]')
    run('git','config','user.email','rza-publisher@users.noreply.github.com')
    while True:
        run('git','pull','--ff-only','origin',os.environ['DEFAULT_BRANCH'])
        clock = read_clock()
        available = remaining()
        if not available:
            if not clock.get('exhausted'):
                clock.update(exhausted=True,exhausted_at=datetime.now(timezone.utc).isoformat())
                save_clock(clock,'Record exhausted RZA publication queue')
            report('Подготовленные темы закончились. Очередь пуста, публикация остановлена.')
            return
        delay = wait_seconds(clock,time.time())
        if time.monotonic()+delay+180 > deadline:
            report('Окно облачного задания завершено. Очередь продолжит следующий запуск.')
            return
        if delay:
            due = datetime.fromtimestamp(time.time()+delay,timezone.utc).isoformat()
            report(f'Следующая партия запланирована на {due}. В очереди {len(available)} постов.')
            while delay > 0:
                time.sleep(min(delay,60))
                delay = wait_seconds(clock,time.time())
            # Refresh the queue and the branch after waiting.
            continue
        run('go','build','-o','publisher','.')
        run('./publisher','-prepare')
        run('python3','.github/scripts/review_editorial.py')
        count = min(10,len(remaining()))
        if target:
            state = json.loads((ROOT/'.publisher-state.json').read_text(encoding='utf-8'))
            count = min(count,max(0,target-len(state)))
        if not count:
            report('Заданный объём публикаций выполнен.')
            return
        clock.update(last_batch_started_at=time.time(),last_batch_size=count,exhausted=False)
        clock.pop('exhausted_at',None)
        save_clock(clock,'Reserve hourly RZA batch window')
        env = dict(os.environ,POSTS_PER_RUN=str(count))
        run('bash','.github/scripts/publish-batch.sh',env=env)
        report(f'Партия завершена. Опубликовано {count} новых постов.')


if __name__=='__main__':
    main()
