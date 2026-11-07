import unittest
from unittest.mock import patch
import publish_hourly
from publish_hourly import wait_seconds


class HourlyTests(unittest.TestCase):
    def test_two_batches_are_one_hour_apart_and_exhaustion_stops(self):
        clock = {}
        now = [10000]
        available = [12]
        deliveries = []

        def execute(*args,env=None):
            if args[0]=='bash':
                count=int(env['POSTS_PER_RUN'])
                deliveries.append((now[0],count))
                available[0]-=count

        def persist(value,message):
            clock.clear()
            clock.update(value)

        with patch.object(publish_hourly,'run',side_effect=execute), \
             patch.object(publish_hourly,'read_clock',side_effect=lambda:dict(clock)), \
             patch.object(publish_hourly,'save_clock',side_effect=persist), \
             patch.object(publish_hourly,'remaining',side_effect=lambda:[None]*available[0]), \
             patch.object(publish_hourly,'report'), \
             patch.object(publish_hourly.time,'time',side_effect=lambda:now[0]), \
             patch.object(publish_hourly.time,'monotonic',side_effect=lambda:now[0]), \
             patch.object(publish_hourly.time,'sleep',side_effect=lambda seconds:now.__setitem__(0,now[0]+seconds)), \
             patch.dict(publish_hourly.os.environ,{'DEFAULT_BRANCH':'main','TARGET_TOTAL':'0'}):
            publish_hourly.main()
        self.assertEqual(deliveries,[(10000,10),(13600,2)])
        self.assertTrue(clock['exhausted'])

    def test_first_batch_and_restarted_runner(self):
        self.assertEqual(wait_seconds({},10000),0)
        clock={'last_batch_started_at':10000}
        self.assertEqual(wait_seconds(clock,10000),3600)
        self.assertEqual(wait_seconds(clock,11800),1800)
        self.assertEqual(wait_seconds(clock,13600),0)
        self.assertEqual(wait_seconds(clock,15000),0)


if __name__=='__main__':
    unittest.main()
