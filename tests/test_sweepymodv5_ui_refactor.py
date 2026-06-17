import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INDEX = (ROOT / "public" / "index.html").read_text(encoding="utf-8")
APP = (ROOT / "public" / "app.js").read_text(encoding="utf-8")


class SweepyModV5UiRefactorTests(unittest.TestCase):
    def test_bot_settings_buttons_are_above_configure_skills_and_settings_presets(self):
        self.assertIn('id="bot-settings-section"', INDEX)
        self.assertIn('id="skill-config-launch-section"', INDEX)
        self.assertIn('id="settings-preset-section"', INDEX)
        self.assertLess(INDEX.index('id="bot-settings-section"'), INDEX.index('id="skill-config-launch-section"'))
        self.assertLess(INDEX.index('id="skill-config-launch-section"'), INDEX.index('id="settings-preset-section"'))
        bot_block = INDEX[INDEX.index('id="bot-settings-section"'):INDEX.index('id="skill-config-launch-section"')]
        self.assertNotIn("BOT SETTINGS", bot_block)
        self.assertIn('id="training-settings-open"', bot_block)
        self.assertIn('id="racing-settings-open"', bot_block)
        self.assertIn('id="scenario-settings-open"', bot_block)

    def test_settings_preset_save_button_exists_and_old_skill_threshold_removed(self):
        self.assertIn('id="settings-preset-save-btn"', INDEX)
        self.assertIn('id="settings-preset-section"', INDEX)
        self.assertNotIn('id="preset-skill-threshold"', INDEX)
        self.assertNotIn('id="preset-running-style"', INDEX)
        self.assertNotIn('for="preset-running-style"', INDEX)

    def test_training_priorities_use_draggable_modal_launcher(self):
        self.assertIn('id="priority-settings-modal"', INDEX)
        self.assertIn('function prioritySetting', APP)
        self.assertIn('draggable="true"', APP)
        self.assertIn("training_stat_priority", APP)
        self.assertIn("event_choice_stat_priority", APP)
        self.assertIn("summer_stat_priority", APP)
        self.assertIn('data-control="priority-open"', APP)

    def test_skill_configuration_running_style_dropdown_removed(self):
        self.assertNotIn('weighted-running-style', APP)
        self.assertNotIn('<span>Running Style</span>', APP)


if __name__ == '__main__':
    unittest.main()
