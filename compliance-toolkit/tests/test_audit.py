import json
import tempfile
import unittest
from pathlib import Path

from llm_governance.audit import AuditLog, redact, verify_chain


class TestRedaction(unittest.TestCase):
    def test_email_is_redacted(self):
        self.assertEqual(redact("write to ada@example.com now"), "write to [EMAIL] now")

    def test_card_number_is_redacted(self):
        self.assertIn("[CARD]", redact("card 4111 1111 1111 1111 expires soon"))

    def test_api_key_is_redacted(self):
        self.assertIn("[API_KEY]", redact("use sk-abcdefghijklmnopqrstuvwx for auth"))

    def test_ip_address_is_redacted(self):
        self.assertIn("[IP]", redact("client at 192.168.10.24 failed"))

    def test_plain_text_is_untouched(self):
        text = "The quarterly review is scheduled for next Tuesday."
        self.assertEqual(redact(text), text)

    def test_empty_input(self):
        self.assertEqual(redact(""), "")


class TestAuditLog(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "audit.jsonl"
        self.log = AuditLog(self.path)

    def tearDown(self):
        self.tmp.cleanup()

    def _write_three(self):
        for i in range(3):
            self.log.append(
                use_case_id="UC-0001",
                actor=f"user{i}@example.com",
                model="example-large-2",
                prompt=f"question {i} from ada@example.com",
                completion=f"answer {i}",
            )

    def test_raw_text_is_not_stored(self):
        record = self.log.append(
            use_case_id="UC-0001", actor="a", model="m",
            prompt="my card is 4111 1111 1111 1111", completion="noted",
        )
        raw = self.path.read_text(encoding="utf-8")
        self.assertNotIn("4111 1111 1111 1111", raw)
        self.assertIn("[CARD]", record.prompt_preview)
        self.assertEqual(len(record.prompt_sha256), 64)

    def test_chain_is_linked(self):
        self._write_three()
        records = list(self.log.read())
        self.assertEqual(len(records), 3)
        self.assertEqual(records[0].prev_hash, "0" * 64)
        self.assertEqual(records[1].prev_hash, records[0].hash)
        self.assertEqual(records[2].prev_hash, records[1].hash)

    def test_verify_passes_on_untouched_log(self):
        self._write_three()
        result = verify_chain(self.path)
        self.assertTrue(result.ok)
        self.assertEqual(result.records, 3)

    def test_verify_detects_edited_record(self):
        self._write_three()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        tampered = json.loads(lines[1])
        tampered["completion_preview"] = "something else entirely"
        lines[1] = json.dumps(tampered, sort_keys=True, separators=(",", ":"))
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_chain(self.path)
        self.assertFalse(result.ok)
        self.assertEqual(result.broken_at, 1)

    def test_verify_detects_deleted_record(self):
        self._write_three()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        del lines[1]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")

        result = verify_chain(self.path)
        self.assertFalse(result.ok)
        self.assertEqual(result.broken_at, 1)

    def test_verify_detects_reordered_records(self):
        self._write_three()
        lines = self.path.read_text(encoding="utf-8").splitlines()
        lines[0], lines[1] = lines[1], lines[0]
        self.path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.assertFalse(verify_chain(self.path).ok)

    def test_empty_log_verifies(self):
        result = verify_chain(self.path)
        self.assertTrue(result.ok)
        self.assertEqual(result.records, 0)

    def test_append_survives_reopening(self):
        self._write_three()
        reopened = AuditLog(self.path)
        reopened.append(use_case_id="UC-0001", actor="a", model="m",
                        prompt="p", completion="c")
        self.assertTrue(verify_chain(self.path).ok)
        self.assertEqual(len(reopened), 4)


if __name__ == "__main__":
    unittest.main()
