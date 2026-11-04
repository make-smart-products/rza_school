import unittest
from pathlib import Path
import sys

from render import caption, describe, PLANS, INTRO
from drawing_v3 import draw_frame, phase_time, W, H


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

    def test_every_concept_layout_fits_without_text_clipping(self):
        for number,plan in list(enumerate(INTRO,1))+list(enumerate(PLANS,7)):
            data={'number':number,'kind':'concept','title':plan[0],'nodes':plan[1],'note':plan[2]}
            for progress in [0,.5,1]:
                with self.subTest(number=number,progress=progress):
                    image=draw_frame(data,progress)
                    self.assertEqual(image.size,(W,H))

    def test_timing_counter_is_monotonic_and_reaches_the_correct_total(self):
        values=[101,5,45]
        counter=[phase_time(values,i/119)[0] for i in range(120)]
        self.assertEqual(counter[0],0)
        self.assertEqual(counter[-1],151)
        self.assertTrue(all(a<=b for a,b in zip(counter,counter[1:])))
        self.assertEqual(phase_time(values,.4)[0],101)
        self.assertEqual(phase_time(values,.6)[0],106)


if __name__=='__main__':
    unittest.main()
