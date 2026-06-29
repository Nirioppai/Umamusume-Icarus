"""Tests for career_bot/event_bus.py — a process-global pub/sub for live API-call
events that backs the SSE /api/stream feed. It's decoupled from the single
on_api_log hook slot (which the runner owns), so the live stream coexists with a
running career without clobbering the runner's logging.
"""
import queue
import unittest

from career_bot import event_bus


class TestEventBus(unittest.TestCase):
    def setUp(self):
        with event_bus._lock:
            event_bus._subscribers.clear()

    def test_publish_reaches_subscriber(self):
        q = event_bus.subscribe()
        event_bus.publish({"ep": "home/index"})
        self.assertEqual(q.get_nowait()["ep"], "home/index")

    def test_unsubscribe_stops_delivery(self):
        q = event_bus.subscribe()
        event_bus.unsubscribe(q)
        event_bus.publish({"ep": "x"})
        with self.assertRaises(queue.Empty):
            q.get_nowait()

    def test_multiple_subscribers_all_get_event(self):
        q1, q2 = event_bus.subscribe(), event_bus.subscribe()
        event_bus.publish({"ep": "y"})
        self.assertEqual(q1.get_nowait()["ep"], "y")
        self.assertEqual(q2.get_nowait()["ep"], "y")

    def test_full_queue_drops_without_raising(self):
        q = event_bus.subscribe(maxsize=2)
        for i in range(10):
            event_bus.publish({"i": i})  # must never raise even when full
        got = []
        try:
            while True:
                got.append(q.get_nowait())
        except queue.Empty:
            pass
        self.assertLessEqual(len(got), 2)

    def test_publish_with_no_subscribers_is_safe(self):
        event_bus.publish({"ep": "nobody-home"})  # must not raise


if __name__ == "__main__":
    unittest.main()
