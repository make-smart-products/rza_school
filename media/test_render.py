import unittest
from pathlib import Path
import sys

from render import caption, describe


class RenderTests(unittest.TestCase):
    def test_all_prepared_posts_fit_captions_and_have_a_visual_spec(self):
        root=Path(sys.argv[0]).resolve().parents[1]
        files=list((root/'posts/lessons').glob('*.txt'))
        files+=list((root/'output/stock/posts').glob('*.txt'))
        self.assertTrue(files)
        for path in files:
            plain,formatted=caption(describe(path.name,path.read_text(encoding='utf-8-sig').strip()))
            self.assertLessEqual(len(plain.encode('utf-16-le'))//2,1024,path.name)
            self.assertIn('<b>',formatted)

    def test_numeric_values_come_from_the_text(self):
        text='Учебная задача: баланс токов\nIвх = 1400 мА, Iвых = 900 мА'
        spec=describe('082-auto.txt',text)
        self.assertEqual(spec['difference'],500)
        plain,_=caption(spec)
        self.assertIn('500 мА',plain)


if __name__=='__main__':
    unittest.main()
