"""Rainbow value-attenuation: a rainbow (friendship training) bonus should scale
down as the trained stat fills toward its cap, so the bot stops chasing rainbows
on already-finished stats. Exercises the pure _rainbow_attenuation curve."""
import unittest


class RainbowAttenuationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from career_bot.scenarios import mant_trackblazer as mt
        cls.mt = mt

    def test_below_threshold_is_full_bonus(self):
        # fill < 0.7 -> atten 1.0 (the rainbow mult stays at its full 2.0x / 1.5x)
        self.assertEqual(self.mt._rainbow_attenuation(0.0), 1.0)
        self.assertEqual(self.mt._rainbow_attenuation(0.69), 1.0)
        self.assertEqual(self.mt._rainbow_attenuation(0.7), 1.0)

    def test_mid_band_ramps_down(self):
        self.assertAlmostEqual(self.mt._rainbow_attenuation(0.7), 1.0)
        self.assertAlmostEqual(self.mt._rainbow_attenuation(0.8), 0.75)
        self.assertAlmostEqual(self.mt._rainbow_attenuation(0.9), 0.5)

    def test_near_cap_band_ramps_to_zero(self):
        # with floor 0.0 the raw curve reaches 0 at the cap
        self.assertAlmostEqual(self.mt._rainbow_attenuation(0.9, 0.0), 0.5)
        self.assertAlmostEqual(self.mt._rainbow_attenuation(0.95, 0.0), 0.25)
        self.assertAlmostEqual(self.mt._rainbow_attenuation(1.0, 0.0), 0.0)

    def test_at_or_over_cap_floored(self):
        # default floor 0.25 keeps a near-capped rainbow worth something
        self.assertAlmostEqual(self.mt._rainbow_attenuation(1.0), 0.25)
        self.assertAlmostEqual(self.mt._rainbow_attenuation(1.5), 0.25)

    def test_floor_clamps(self):
        self.assertAlmostEqual(self.mt._rainbow_attenuation(1.0, 0.5), 0.5)

    def test_continuous_at_band_boundaries(self):
        # no jump at 0.7, 0.9, or 1.0
        for f in (0.7, 0.9, 1.0):
            below = self.mt._rainbow_attenuation(f - 1e-9, 0.0)
            at = self.mt._rainbow_attenuation(f, 0.0)
            self.assertAlmostEqual(below, at, places=6, msg=f"discontinuity at fill={f}")


if __name__ == "__main__":
    unittest.main()
