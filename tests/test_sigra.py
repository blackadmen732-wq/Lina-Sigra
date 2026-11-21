import json
from pathlib import Path
import unittest

from lina_sigra import WireError, check, decode, encode
from sigra import run
from sigra_parser import SigraError
from sigra_runtime import pesa, verify_packet

ROOT = Path(__file__).resolve().parents[1]


class WireTests(unittest.TestCase):
    def test_packet_round_trips_across_json(self):
        packet = pesa("starline", "Ke vi sava Eldorian?")
        self.assertEqual(packet["wire_version"], "crc16-ccitt-v1")
        self.assertEqual(packet["check"], 55249)
        self.assertTrue(verify_packet(json.loads(json.dumps(packet))))

    def test_reordered_words_and_changed_data_change_crc(self):
        first = pesa("starline", "Mi ama Eldoria.")
        second = pesa("starline", "Eldoria ama Mi.")
        self.assertNotEqual(first["check"], second["check"])
        self.assertFalse(verify_packet({**first, "codes": second["codes"]}))
        self.assertNotEqual(check(encode("Crème.")), check(encode("Brûlée.")))

    def test_accented_words_and_negative_decimals_stay_whole(self):
        packet = pesa("starline", "Cre\u0300me br\u00fbl\u00e9e -12.5")
        self.assertEqual(packet["unknown_words"], ["crème", "brûlée"])
        self.assertEqual(packet["reads_as"], "Crème brûlée -12.5.")
        self.assertNotIn("1015", packet["codes"].split())
        self.assertTrue(verify_packet(packet))

    def test_numeric_value_that_looks_like_a_marker_is_still_a_number(self):
        packet = pesa("starline", "Mi 0092.")
        self.assertEqual(packet["unknown_words"], [])
        self.assertTrue(verify_packet(packet))

    def test_bad_frames_are_rejected(self):
        for frame in (
            "1001 0098", "0092 0099", "9999 0098 0099", "0091 1001 0098 0099",
            "0090 word 0098 0099", "1001 0099", "0090 0098 0099", "9002 0098 0099",
        ):
            with self.subTest(frame=frame):
                with self.assertRaises(WireError):
                    decode(frame)

    def test_valid_crc_does_not_make_malformed_tokens_valid(self):
        packet = pesa("starline", "Mi ama Eldoria.")
        malformed = "1001 0099"
        self.assertFalse(verify_packet({**packet, "codes": malformed, "check": check(malformed)}))
        self.assertFalse(verify_packet({**packet, "wire_version": "crc32-v1"}))


class CodeTests(unittest.TestCase):
    def output(self, program):
        output = []
        run(program, write=output.append)
        return output

    def test_assignment_equality_and_chained_comparisons(self):
        source = "result es 2 = 2\nsava result\nsava 1 < 2 < 3\nsava no 1 = 1"
        self.assertEqual(self.output(source), ["True", "True", "False"])

    def test_comments_and_negative_values(self):
        source = 'sava 1 -- a comment with "quotes"\nsava 5--2\nsava "-- inside text"'
        self.assertEqual(self.output(source), ["1", "7", "-- inside text"])

    def test_or_and_else_work_in_their_own_contexts(self):
        source = 'se falsa o falsa:\n    sava "if"\no:\n    sava "else"'
        self.assertEqual(self.output(source), ["else"])

    def test_bad_program_points_at_the_original_source_line(self):
        with self.assertRaisesRegex(SigraError, "line 4: expected an expression"):
            run("-- first\n\nn es 1\nsava")
        with self.assertRaisesRegex(SigraError, "line 4: unknown name"):
            run("-- first\n\nn es 1\nsava missing")

    def test_python_expressions_are_outside_the_language(self):
        with self.assertRaisesRegex(SigraError, "line 1: unknown function 'sum'"):
            run("sava sum([1, 2])")
        with self.assertRaisesRegex(SigraError, "line 1: unexpected character"):
            run("sava score.value")

    def test_loop_ends_at_step_limit(self):
        with self.assertRaisesRegex(SigraError, "exhausted its step budget"):
            run("denova kana vora:\n    pasa")

    def test_recursion_ends_at_depth_limit(self):
        with self.assertRaisesRegex(SigraError, "exceeded the function call depth"):
            run("fora spin:\n    dela spin()\nsava spin()")

    def test_fibonacci_example(self):
        source = (ROOT / "examples" / "fibonacci.sg").read_text(encoding="utf-8")
        self.assertEqual(self.output(source), "0 1 1 2 3 5 8 13 21 34 55".split())

    def test_sela_example(self):
        source = (ROOT / "examples" / "sela.sg").read_text(encoding="utf-8")
        output = self.output(source)
        self.assertEqual(output[0], "Sela, Orion!")
        self.assertIn("42", output)
        self.assertIn("wire_version", output[-1])


if __name__ == "__main__":
    unittest.main()
