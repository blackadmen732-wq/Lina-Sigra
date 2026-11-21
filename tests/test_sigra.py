# Copyright (c) 2026 Jahf Mark Aldonza
# SPDX-License-Identifier: AGPL-3.0-only
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


class WireToolTests(unittest.TestCase):
    def test_gloss_binary_and_commas(self):
        import lina_sigra
        rows = lina_sigra.gloss("Mi ama crème, 12 dia.").splitlines()
        self.assertIn("NEW WORD", " ".join(rows))
        self.assertTrue(any("number" in r for r in rows))
        bits = lina_sigra.binary("Mi ama crème.").split()
        self.assertEqual(len(bits[0]), 14)
        self.assertEqual(lina_sigra.decode(lina_sigra.encode("Mi ama, vi ama.")), "Mi ama, vi ama.")
        self.assertEqual(decode(encode("Ke vi sava Eldorian?")), "Ke vi sava Lina Eldoria?")
        with self.assertRaises(WireError):
            decode([1001, "0099"])

    def test_command_line_in_process(self):
        import contextlib, io, runpy, sys
        for argv, expect in ((["lina_sigra.py", "encode", "Mi ama."], "1001 2030 0098 0099"),
                             (["lina_sigra.py", "decode", "1001 2030 0098 0099"], "Mi ama.")):
            out = io.StringIO(); old = sys.argv; sys.argv = argv
            try:
                with contextlib.redirect_stdout(out):
                    runpy.run_path(str(ROOT / "lina_sigra.py"), run_name="__main__")
            finally:
                sys.argv = old
            self.assertEqual(out.getvalue().strip(), expect)
        out = io.StringIO(); old = sys.argv; sys.argv = ["lina_sigra.py"]
        try:
            with contextlib.redirect_stdout(out), self.assertRaises(SystemExit):
                runpy.run_path(str(ROOT / "lina_sigra.py"), run_name="__main__")
        finally:
            sys.argv = old


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

    def test_desk_week_example(self):
        output = self.output((ROOT / "examples" / "desk_week.sg").read_text(encoding="utf-8"))
        self.assertEqual(output[:5], ["mon: RUN", "tue: WATCH", "wed: PAUSE", "thu: RUN", "fri: WATCH"])
        self.assertEqual(output[5:7], ["days paused: 1 of 5", "average risk: 62.6"])
        self.assertTrue(output[7].endswith("'reads_as': 'Na sinta risk.'}"))

    def test_letra_and_lorga(self):
        self.assertEqual(self.output('sava "risk " + letra(91)\nsava letra(2.5) + letra(vora) + letra(nul)\nsava lorga([1, 2, 3])\nsava lorga("fox")'),
                         ["risk 91", "2.5voranul", "3", "3"])
        with self.assertRaisesRegex(SigraError, r"line 1: .*letra\(\.\.\.\)"):
            self.output('sava "risk " + 91')
        with self.assertRaisesRegex(SigraError, "not a list"):
            self.output("sava letra([1])")
        with self.assertRaisesRegex(SigraError, "length of a list or a text"):
            self.output("sava lorga(5)")
        with self.assertRaisesRegex(SigraError, "expects 1 argument"):
            self.output("sava lorga([1], [2])")

    def test_lists_join_within_limits(self):
        self.assertEqual(self.output("x es [1, 2] + [3]\nsava lorga(x)\nsava x[2]"), ["3", "3"])
        with self.assertRaisesRegex(SigraError, "at most 1000 values"):
            self.output("x es [1]\nnorae i de 1 a 11:\n    x es x + x")
        with self.assertRaisesRegex(SigraError, "requires numbers"):
            self.output("x es [1] + 2")

    def test_built_in_names_cannot_be_redefined(self):
        for name in ("letra", "lorga"):
            with self.assertRaisesRegex(SigraError, "built-in function"):
                self.output(f"fora {name} toma x:\n    dela x")

    def test_host_sets_the_limits(self):
        loop = "n es 0\ndenova kana n < 3000:\n    n es n + 1\nsava n"
        with self.assertRaisesRegex(SigraError, "step budget"):
            self.output(loop)
        out = []
        run(loop, write=out.append, steps=100_000)
        self.assertEqual(out, ["3000"])
        with self.assertRaisesRegex(SigraError, "call depth"):
            run("fora f toma x:\n    dela f(x)\nsava f(1)", write=lambda s: None, depth=5)

    def test_random_broken_programs_never_crash_python(self):
        import random
        rng = random.Random(7)
        words = ["se", "o", "e", "no", "es", "sava", "norae", "de", "a", "en", "denova", "kana", "fora", "toma", "dela",
                 "letra", "lorga", "x", "y", "f", "1", "0", "-3", "2.5", '"hi"', "vora", "nul", "(", ")", "[", "]", ":",
                 ",", "+", "-", "*", "/", "//", "%", "=", "!=", "<", ">=", "--"]
        for _ in range(3000):
            src = "\n".join(("    " * rng.randint(0, 2) if rng.random() < 0.4 else "") +
                            " ".join(rng.choice(words) for _ in range(rng.randint(1, 8))) for _ in range(rng.randint(1, 6)))
            try:
                run(src, read=lambda: "5", write=lambda s: None)
            except SigraError:
                pass

    def test_random_broken_frames_never_crash_python(self):
        import random
        rng = random.Random(11)
        pool = ["0090", "0091", "0092", "0097", "0098", "0099", "1001", "2030", "9002", "9999", "-1", "x", "12.5", ""]
        for _ in range(3000):
            try:
                decode([rng.choice(pool) for _ in range(rng.randint(0, 7))])
            except WireError:
                pass

    def test_size_limits_and_type_errors_point_at_the_line(self):
        cases = [("x es 2\nnorae i de 1 a 9:\n    x es x * x", "integer exceeds"),
                 ('t es "ab"\nnorae i de 1 a 12:\n    t es t + t', "text exceeds"),
                 ("sava 1 en 5", "expects a list or text"), ('sava -"a"', "requires a number"),
                 ("sava [1, 2][5]", "out of range"), ('sava "ab"["x"]', "whole number"), ("sava 1 / 0", "division"),
                 ("sava 1 * [2]", "requires numbers"), ("norae i de 1 a 2.5:\n    sava i", "whole numbers"),
                 ("norae i en 5:\n    sava i", "expects a list or text"), ("sava [[1]]", "scalar"),
                 ("sava nope(1)", "unknown function"), ("sava nope", "unknown name")]
        for program, message in cases:
            with self.subTest(program=program), self.assertRaisesRegex(SigraError, message):
                self.output(program)
        self.assertEqual(self.output('sava 2 en [1, 2]\nsava "o" en "fox"\nsava -(3)\nsava 7 // 2\nsava 7 % 2'), ["True", "True", "-3", "3", "1"])

    def test_command_line(self):
        import subprocess, sys
        def cli(*args):
            return subprocess.run([sys.executable, *args], cwd=ROOT, capture_output=True, text=True)
        self.assertIn("Sigra Code 0.2.0", cli("sigra.py", "--version").stdout)
        self.assertEqual(cli("sigra.py", "examples/fibonacci.sg").returncode, 0)
        bad = cli("sigra.py", "missing.sg")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("Sigra error", bad.stderr)
        self.assertNotEqual(cli("sigra.py", "--steps", "0", "examples/sela.sg").returncode, 0)
        self.assertEqual(cli("lina_sigra.py", "encode", "Mi ama Eldoria.").stdout.strip(), "1001 2030 0091 9002 0098 0099")
        self.assertEqual(cli("lina_sigra.py", "decode", "1001 2030 0091 9002 0098 0099").stdout.strip(), "Mi ama Eldoria.")
        self.assertIn("NEW WORD", cli("lina_sigra.py", "gloss", "Mi ama crème.").stdout)
        self.assertTrue(set(cli("lina_sigra.py", "binary", "Mi ama.").stdout.split()[0]) <= {"0", "1"})
        self.assertNotEqual(cli("lina_sigra.py").returncode, 0)

    def test_sela_example(self):
        source = (ROOT / "examples" / "sela.sg").read_text(encoding="utf-8")
        output = self.output(source)
        self.assertEqual(output[0], "Sela, Orion!")
        self.assertIn("42", output)
        self.assertIn("wire_version", output[-1])


if __name__ == "__main__":
    unittest.main()
