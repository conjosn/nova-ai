import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from core.reminders import ReminderStore


class ReminderStoreTests(unittest.TestCase):
    def test_reminders_are_persisted_and_popped_when_due(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "reminders.json"
            store = ReminderStore(path)
            reminder = store.add_after(60, "stretch")
            self.assertEqual(ReminderStore(path).pending()[0].id, reminder.id)
            due = store.pop_due(datetime.now(timezone.utc) + timedelta(minutes=2))
            self.assertEqual([item.text for item in due], ["stretch"])
            self.assertEqual(store.pending(), [])

    def test_unknown_reminder_cannot_be_cancelled(self):
        with tempfile.TemporaryDirectory() as directory:
            store = ReminderStore(Path(directory) / "reminders.json")
            self.assertFalse(store.cancel("missing"))


if __name__ == "__main__":
    unittest.main()
