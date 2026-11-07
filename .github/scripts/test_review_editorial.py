import copy
import json
from pathlib import Path
import tempfile
import unittest

from review_editorial import ROOT, review


class EditorialReviewTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT/'content/advanced.json').read_text(encoding='utf-8'))
        self.lesson = copy.deepcopy(next(p for p in self.catalog if p.get('editorial_profile')=='equipment'))
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.queue = Path(self.directory.name)
        (self.queue/self.lesson['file']).write_text(self.lesson['body'],encoding='utf-8')

    def test_ready_card_and_empty_queue(self):
        self.assertEqual(review(self.queue,[],[self.lesson]),1)
        self.assertEqual(review(self.queue,[{'file':self.lesson['file']}],[self.lesson]),0)

    def test_repeated_numbers_do_not_create_a_new_topic(self):
        archive = '001-archive.txt'
        body = self.lesson['body'].replace('0,40','0,50').replace('11 В','12 В')
        (self.queue/archive).write_text(body,encoding='utf-8')
        with self.assertRaisesRegex(ValueError,'повтор'):
            review(self.queue,[{'file':archive}],[self.lesson])

    def test_one_picture_cannot_be_reused_for_another_post(self):
        other={**self.lesson,'file':'999-advanced.txt','title':'Another topic'}
        with self.assertRaisesRegex(ValueError,'изображение повторяет'):
            review(self.queue,[],[self.lesson,other])

    def test_unknown_source_missing_check_or_picture_block_delivery(self):
        cases = []
        unknown = copy.deepcopy(self.lesson)
        unknown['source_ids'] = ['UNREGISTERED99']
        cases.append(unknown)
        cases.append({**self.lesson,'illustration':None})
        missing_check = copy.deepcopy(self.lesson)
        missing_check['body'] = missing_check['body'].split('\n\nПроверка на объекте:')[0]
        cases.append(missing_check)
        for lesson in cases:
            with self.subTest(lesson=lesson['title']):
                (self.queue/lesson['file']).write_text(lesson['body'],encoding='utf-8')
                with self.assertRaises(ValueError):
                    review(self.queue,[],[lesson])


if __name__=='__main__':
    unittest.main()
