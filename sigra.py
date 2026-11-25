#!/usr/bin/env python3
# Copyright (c) 2026 Jahf Mark Aldonza
# SPDX-License-Identifier: AGPL-3.0-only
"""Run a local Sigra program: python3 sigra.py PROGRAM.sg.

Sigra Code preview. Review untrusted source before running it. This interpreter
is not a reviewed sandbox. Use EdgeBot's restricted rules for bot decisions.
"""
import argparse
import math
import operator
from pathlib import Path
import sys

from sigra_parser import BUILTINS, SigraError, parse

VERSION = "0.2.0"
MAX_LIST = 1_000
from sigra_runtime import pesa, sigra


OPERATIONS = {
    "+": operator.add, "-": operator.sub, "*": operator.mul, "/": operator.truediv,
    "//": operator.floordiv, "%": operator.mod, "=": operator.eq, "!=": operator.ne,
    "<": operator.lt, ">": operator.gt, "<=": operator.le, ">=": operator.ge,
}
ARITHMETIC = frozenset({"+", "-", "*", "/", "//", "%"})
NUMBERS = (int, float)
isfinite = math.isfinite


class ReturnValue(Exception):
    def __init__(self, value):
        self.value = value


class Interpreter:
    def __init__(self, read, write, steps=10_000, output=32_000, depth=24):
        self.read = read
        self.write = write
        self.globals = {}
        self.functions = {}
        self.steps = steps
        self.output_left = output
        self.max_depth = depth
        self.depth = 0

    def limit_value(self, line, value):
        if type(value) is int and value.bit_length() > 256:
            raise SigraError(line, "integer exceeds the preview size limit")
        if type(value) is float and not math.isfinite(value):
            raise SigraError(line, "number must be finite")
        if isinstance(value, str) and len(value) > 4_000:
            raise SigraError(line, "text exceeds the preview size limit")
        if isinstance(value, list) and len(value) > MAX_LIST:
            raise SigraError(line, f"a list holds at most {MAX_LIST} values")
        return value

    def emit(self, line, value):
        output = str(value)
        self.output_left -= len(output) + 1
        if self.output_left < 0:
            raise SigraError(line, "program exhausted its output budget")
        self.write(output)

    def binary(self, op, left, right, line):
        function = OPERATIONS.get(op)
        if function is not None and type(left) in NUMBERS and type(right) in NUMBERS:
            # fast path: number with number, same checks as limit_value for numeric results
            result = function(left, right)
            kind = type(result)
            if kind is int and result.bit_length() > 256:
                raise SigraError(line, "integer exceeds the preview size limit")
            if kind is float and not isfinite(result):
                raise SigraError(line, "number must be finite")
            return result
        if op == "en":
            if not isinstance(right, (str, list)):
                raise SigraError(line, "'en' expects a list or text on the right")
            return left in right
        if op in ARITHMETIC:
            if op == "+" and isinstance(left, str) and isinstance(right, str):
                return self.limit_value(line, left + right)
            if op == "+" and isinstance(left, list) and isinstance(right, list):
                return self.limit_value(line, left + right)
            if op == "+" and (isinstance(left, str) or isinstance(right, str)):
                raise SigraError(line, "'+' joins text only with text; turn the number into text first with letra(...)")
            if type(left) not in NUMBERS or type(right) not in NUMBERS:
                raise SigraError(line, f"{op!r} requires numbers, or two texts for '+'")
        return self.limit_value(line, function(left, right))

    def evaluate(self, node, scope, line):
        self.steps -= 1
        if self.steps < 0:
            raise SigraError(line, "program exhausted its step budget")
        kind = node[0]
        if kind == "name":
            name = node[1]
            if name in scope:
                return scope[name]
            if name in self.globals:
                return self.globals[name]
            raise SigraError(line, f"unknown name {name!r}")
        if kind == "binary":
            op = node[1]
            left = self.evaluate(node[2], scope, line)
            if op == "e":
                return left and self.evaluate(node[3], scope, line)
            if op == "o":
                return left or self.evaluate(node[3], scope, line)
            return self.binary(op, left, self.evaluate(node[3], scope, line), line)
        if kind == "literal":
            return self.limit_value(line, node[1])
        if kind == "compare":
            left = self.evaluate(node[1], scope, line)
            for op, right_node in node[2]:
                right = self.evaluate(right_node, scope, line)
                if not self.binary(op, left, right, line):
                    return False
                left = right
            return True
        if kind == "unary":
            op = node[1]
            value = self.evaluate(node[2], scope, line)
            if op == "no":
                return not value
            if type(value) not in NUMBERS:
                raise SigraError(line, f"{op!r} requires a number")
            return value if op == "+" else -value
        if kind == "list":
            values = [self.evaluate(item, scope, line) for item in node[1]]
            if any(isinstance(item, list) for item in values):
                raise SigraError(line, "the preview supports lists of scalar values")
            return values
        if kind == "index":
            value = self.evaluate(node[1], scope, line)
            index = self.evaluate(node[2], scope, line)
            if not isinstance(value, (str, list)) or type(index) is not int:
                raise SigraError(line, "index expects text or a list and a whole number")
            return value[index]
        values = [self.evaluate(arg, scope, line) for arg in node[2]]
        return self.call(node[1], values, line)

    def builtin(self, name, values, line):
        if len(values) != BUILTINS[name]:
            raise SigraError(line, f"{name!r} expects {BUILTINS[name]} argument")
        value = values[0]
        if name == "letra":
            if value is True or value is False or value is None:
                return {True: "vora", False: "falsa", None: "nul"}[value]
            if type(value) in (int, float, str):
                return self.limit_value(line, str(value))
            raise SigraError(line, "letra turns a number, true/false or nothing into text, not a list")
        if not isinstance(value, (str, list)):
            raise SigraError(line, "lorga gives the length of a list or a text")
        return len(value)

    def call(self, name, values, line):
        if name in BUILTINS:
            return self.builtin(name, values, line)
        if name not in self.functions:
            raise SigraError(line, f"unknown function {name!r}")
        parameters, body = self.functions[name]
        if len(values) != len(parameters):
            raise SigraError(line, f"{name!r} expects {len(parameters)} arguments")
        if self.depth >= self.max_depth:
            raise SigraError(line, "program exceeded the function call depth")
        self.depth += 1
        try:
            self.block(body, dict(zip(parameters, values)))
        except ReturnValue as result:
            return result.value
        finally:
            self.depth -= 1
        return None

    def execute(self, statement, scope):
        line, kind, args = statement.line, statement.kind, statement.args
        if kind == "es":
            name, expression = args
            scope[name] = self.evaluate(expression, scope, line)
        elif kind in ("sava", "sigra", "pesa", "dela"):
            value = self.evaluate(args[-1], scope, line)
            if kind == "dela":
                raise ReturnValue(value)
            if kind in ("sigra", "pesa"):
                if not isinstance(value, str):
                    raise SigraError(line, f"{kind} expects a text value")
                value = sigra(value) if kind == "sigra" else pesa(args[0], value)
            self.emit(line, value)
        elif kind == "risa":
            try:
                value = self.read()
            except EOFError:
                raise SigraError(line, "no more input") from None
            if type(value) is not str:  # the host must hand over text, never Python objects
                raise SigraError(line, "risa expects text from the host")
            scope[args[0]] = self.limit_value(line, value)
        elif kind == "se":
            condition = self.evaluate(args[0], scope, line)
            self.block(statement.body if condition else statement.otherwise, scope)
        elif kind == "denova":
            while self.evaluate(args[0], scope, line):
                self.block(statement.body, scope)
        elif kind == "norae":
            name, expression, *end = args
            iterable = self.evaluate(expression, scope, line)
            if end:
                upper = self.evaluate(end[0], scope, line)
                if type(iterable) is not int or type(upper) is not int:
                    raise SigraError(line, "counting limits must be whole numbers")
                iterable = range(iterable, upper + 1)
            elif not isinstance(iterable, (list, str)):
                raise SigraError(line, "counting with 'en' expects a list or text")
            for value in iterable:
                scope[name] = value
                self.block(statement.body, scope)
        elif kind == "fora":
            self.functions[args[0]] = (args[1], statement.body)

    def block(self, statements, scope):
        for statement in statements:
            self.steps -= 1
            if self.steps < 0:
                raise SigraError(statement.line, "program exhausted its step budget")
            try:
                self.execute(statement, scope)
            except SigraError:
                raise
            except (TypeError, ValueError, ArithmeticError, IndexError, EOFError, RecursionError) as error:
                raise SigraError(statement.line, str(error)) from error


def run(source, *, read=input, write=print, steps=10_000, output=32_000, depth=24):
    """Parse and interpret one program, with I/O and limits supplied by the caller (the host)."""
    statements = parse(source)
    interpreter = Interpreter(read, write, steps=steps, output=output, depth=depth)
    interpreter.block(statements, interpreter.globals)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", action="version", version=f"Sigra Code {VERSION}")
    parser.add_argument("--steps", type=int, default=10_000, help="step budget (default 10000, at most 10000000)")
    parser.add_argument("program", type=Path)
    options = parser.parse_args()
    if not 1 <= options.steps <= 10_000_000:
        parser.error("--steps must be between 1 and 10000000")
    try:
        run(options.program.read_text(encoding="utf-8"), steps=options.steps)
    except (OSError, SigraError) as error:
        print(f"Sigra error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
