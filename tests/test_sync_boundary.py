"""A dirty canonical skill must never be pinned or mutate a derived package."""
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
import sync_skill
sys.path.pop(0)

class SyncBoundaryTests(unittest.TestCase):
    def test_dirty_canonical_stops_before_any_derived_or_lock_write(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            target=root/'skills/thegram-cloud/SKILL.md'
            target.parent.mkdir(parents=True)
            target.write_bytes(b'original derived skill')
            lock=root/'skill-source.lock.json'
            lock.write_bytes(b'original lock, must remain byte identical')
            before={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            # Mock only read-only Git inspection; the rejection runs real sync code
            # and must happen before content import or any lock construction/write.
            with patch.object(sync_skill,'git',side_effect=['bc0e2dd6c939dba8c99259d303a535452d877aed',' M skills/thegram-memory/SKILL.md']):
                with self.assertRaisesRegex(sync_skill.PackageError,'Commit the canonical skill'):
                    sync_skill.sync(Path('/unused-canonical'),root)
            after={str(p.relative_to(root)):p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(before,after)

    def test_existing_derived_pin_still_valid_without_sync(self):
        sync_skill.verify_shared_skill(ROOT)

if __name__=='__main__': unittest.main()
