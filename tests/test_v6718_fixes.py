"""Regression tests for v6.7.18: Steam headless-bypass auth did not
survive version upgrades because it was never persisted to userdata.

The bug had two halves:
  1. check_saved_auth() read ``auth_config.json`` ONLY from RUNTIME_DIR
     (the build folder, wiped on every upgrade).
  2. The v6.7.6 work persisted only ``steam_token.txt`` to userdata --
     NOT ``auth_config.json``, which is the file the read side needs.

So after an upgrade the new build folder was empty, the read found
nothing, and the userdata copy couldn't help because the needed file
was never saved there. Headless bypass fell back to a manual Steam
launch every upgrade.

The fix:
  * full ``auth_config.json`` is written to BOTH runtime and userdata
  * check_saved_auth() reads userdata first, falls back to RUNTIME_DIR,
    and migrates the runtime copy into userdata for future upgrades

NOTE: main.py cannot be imported in this sandbox (it requires fastapi /
frida / curl_cffi / etc.), so these tests mirror the path-resolution
and read-preference logic from main.py exactly and validate the
upgrade/migration behavior contract. If the main.py logic changes,
these mirrors must be updated to match.
"""
import json
import tempfile
import unittest
from pathlib import Path


# --- Faithful mirrors of the main.py v6.7.18 helpers -------------------

def _user_auth_config_path(userdata_dir, profile_name):
    p = Path(userdata_dir) / "auth" / (profile_name or "default")
    p.mkdir(parents=True, exist_ok=True)
    return p / "auth_config.json"


def _save_auth_config_both(save_cfg, userdata_dir, runtime_dir, profile_name):
    payload = json.dumps(save_cfg, indent=4)
    (Path(runtime_dir) / "auth_config.json").write_text(payload)
    _user_auth_config_path(userdata_dir, profile_name).write_text(payload)


def _resolve_auth_config_path(userdata_dir, runtime_dir, profile_name):
    """Mirror of check_saved_auth's userdata-first selection + migration."""
    runtime_auth = Path(runtime_dir) / "auth_config.json"
    user_auth = _user_auth_config_path(userdata_dir, profile_name)
    if user_auth.exists():
        return ("userdata", str(user_auth))
    if runtime_auth.exists():
        # migrate into userdata for the next upgrade
        user_auth.write_text(runtime_auth.read_text())
        return ("runtime", str(runtime_auth))
    return (None, None)


# --- Tests -------------------------------------------------------------

class SteamAuthUserdataTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.userdata = self.tmp / "SweepyClaude_userdata"
        self.userdata.mkdir(parents=True, exist_ok=True)
        self.profile = "MyProfile"
        self.cfg = {"steam_id": "123", "steam_session_ticket": "abc",
                    "steam_username": "obf_u", "steam_password_seed": "obf_p"}

    def _runtime(self, name):
        d = self.tmp / name
        d.mkdir(parents=True, exist_ok=True)
        return d

    def test_save_writes_both_locations(self):
        rt = self._runtime("build_v1")
        _save_auth_config_both(self.cfg, self.userdata, rt, self.profile)
        self.assertTrue((rt / "auth_config.json").exists())
        self.assertTrue(_user_auth_config_path(self.userdata, self.profile).exists())

    def test_upgrade_reads_from_userdata(self):
        """The reported bug: after upgrading to a fresh build folder,
        auth must still be found (in userdata)."""
        rt_old = self._runtime("build_v6717")
        _save_auth_config_both(self.cfg, self.userdata, rt_old, self.profile)
        rt_new = self._runtime("build_v6718")  # fresh, empty
        src, path = _resolve_auth_config_path(self.userdata, rt_new, self.profile)
        self.assertEqual(src, "userdata")
        loaded = json.loads(Path(path).read_text())
        self.assertEqual(loaded["steam_id"], "123")

    def test_userdata_preferred_over_runtime(self):
        """When both exist, userdata wins (it's authoritative)."""
        rt = self._runtime("build_both")
        # userdata has the fresh value, runtime has a stale one
        _user_auth_config_path(self.userdata, self.profile).write_text(
            json.dumps({"steam_id": "FRESH"}))
        (rt / "auth_config.json").write_text(json.dumps({"steam_id": "STALE"}))
        src, path = _resolve_auth_config_path(self.userdata, rt, self.profile)
        self.assertEqual(src, "userdata")
        self.assertEqual(json.loads(Path(path).read_text())["steam_id"], "FRESH")

    def test_runtime_fallback_and_migration(self):
        """First run after installing the fix: only runtime has the
        config -> use it AND copy it into userdata for next time."""
        rt = self._runtime("build_first")
        (rt / "auth_config.json").write_text(json.dumps({"steam_id": "MIGRATE"}))
        # userdata empty
        self.assertFalse(_user_auth_config_path(self.userdata, self.profile).exists()
                         and _user_auth_config_path(self.userdata, self.profile).read_text())
        src, path = _resolve_auth_config_path(self.userdata, rt, self.profile)
        self.assertEqual(src, "runtime")
        # migration happened
        migrated = _user_auth_config_path(self.userdata, self.profile)
        self.assertTrue(migrated.exists())
        self.assertEqual(json.loads(migrated.read_text())["steam_id"], "MIGRATE")

    def test_no_auth_anywhere_returns_none(self):
        rt = self._runtime("build_empty")
        src, path = _resolve_auth_config_path(self.userdata, rt, self.profile)
        self.assertIsNone(src)
        self.assertIsNone(path)

    def test_per_profile_isolation(self):
        """Different profiles keep separate auth configs."""
        rt = self._runtime("build_iso")
        _save_auth_config_both(self.cfg, self.userdata, rt, "ProfileA")
        _save_auth_config_both({"steam_id": "B"}, self.userdata, rt, "ProfileB")
        a = _user_auth_config_path(self.userdata, "ProfileA")
        b = _user_auth_config_path(self.userdata, "ProfileB")
        self.assertEqual(json.loads(a.read_text())["steam_id"], "123")
        self.assertEqual(json.loads(b.read_text())["steam_id"], "B")


if __name__ == "__main__":
    unittest.main()
