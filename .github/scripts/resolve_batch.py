import json
import os
from pathlib import Path


def decide_count(state, target):
    if target < 0 or target > 1_000_000:
        raise ValueError('Invalid catch-up target')
    if any(post.get('status') != 'sent' for post in state):
        raise ValueError('Unresolved delivery: check the channel before continuing')
    count = 10 if target == 0 else max(0, target - len(state))
    if count > 1000:
        raise ValueError('Catch-up is limited to 1000 posts per run')
    return count


if __name__ == '__main__':
    path = Path('.publisher-state.json')
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else []
    published = {post['file'] for post in state}
    available = sum(p.name not in published for p in Path('posts/lessons').glob('*.txt'))
    print(min(available, decide_count(state, int(os.environ.get('TARGET_TOTAL', '0')))))
