# Copyright (c) 2026 Jahf Mark Aldonza
# SPDX-License-Identifier: AGPL-3.0-only
"""Parse the Sigra Code grammar and keep original source positions."""
import ast
from dataclasses import dataclass, field
import math
import re


class SigraError(ValueError):
    def __init__(self, line, message):
        super().__init__(f"line {line}: {message}" if line else message)


TOKEN = re.compile(
    r"""(?P<space>\s+)|(?P<comment>--)"""
    r"""|(?P<string>"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')"""
    r"""|(?P<number>[0-9]+(?:\.[0-9]+)?)|(?P<name>[^\W\d]\w*)"""
    r"""|(?P<symbol>!=|>=|<=|//|[=@:(),\[\]+*/%<>-])"""
)
BINDING = {
    "o": 1, "e": 2, "=": 3, "!=": 3, "<": 3, ">": 3, "<=": 3, ">=": 3, "en": 3,
    "+": 4, "-": 4, "*": 5, "/": 5, "//": 5, "%": 5,
}
COMPARE = {"=", "!=", "<", ">", "<=", ">=", "en"}
LITERALS = {"vora": True, "falsa": False, "nul": None}
RESERVED = set(LITERALS) | {
    "e", "o", "no", "se", "en", "es", "dela", "denova", "fora", "norae", "pasa", "pesa", "risa", "sava", "sigra",
}


@dataclass
class Statement:
    line: int
    kind: str
    args: tuple = ()
    body: list = field(default_factory=list)
    otherwise: list = field(default_factory=list)


class Line:
    def __init__(self, number, source):
        self.number = number
        self.indent = len(source) - len(source.lstrip(" "))
        self.tokens = []
        self.index = 0
        offset = self.indent
        while offset < len(source):
            match = TOKEN.match(source, offset)
            if match is None or source[offset] == "\t":
                raise self.error(f"unexpected character at column {offset + 1}")
            kind = match.lastgroup
            if kind == "comment":
                if offset == self.indent or source[offset - 1].isspace():
                    break
                self.tokens.append(("symbol", "-"))
                offset += 1
                continue
            if kind != "space":
                self.tokens.append((kind, match[0]))
            offset = match.end()
        if len(self.tokens) > 160:
            raise self.error("the line contains more than 160 tokens")

    def error(self, message):
        return SigraError(self.number, message)

    def peek(self):
        return self.tokens[self.index][1] if self.index < len(self.tokens) else None

    def take(self, expected):
        if self.peek() != expected:
            raise self.error(f"expected {expected!r}, got {self.peek()!r}")
        self.index += 1

    def end(self):
        if self.peek() is not None:
            raise self.error(f"unexpected token {self.peek()!r}")

    def name(self):
        if self.peek() is None or self.tokens[self.index][0] != "name":
            raise self.error("expected a name")
        name = self.peek()
        if name in RESERVED or name.startswith("_"):
            raise self.error(f"{name!r} is reserved")
        self.index += 1
        return name

    def sequence(self, closing, parse_item):
        items = []
        if self.peek() != closing:
            items.append(parse_item())
            while self.peek() == ",":
                self.take(",")
                items.append(parse_item())
        self.take(closing)
        return items

    def atom(self):
        token = self.peek()
        if token in ("no", "+", "-"):
            self.take(token)
            return ("unary", token, self.expression(3 if token == "no" else 6))
        if token == "(":
            self.take("(")
            expression = self.expression()
            self.take(")")
            return expression
        if token == "[":
            self.take("[")
            return ("list", self.sequence("]", self.expression))
        if token in LITERALS:
            self.take(token)
            return ("literal", LITERALS[token])
        if token is None:
            raise self.error("expected an expression")
        kind = self.tokens[self.index][0]
        if kind == "number" or kind == "string":
            self.take(token)
            try:
                value = ast.literal_eval(token) if kind == "string" else float(token) if "." in token else int(token)
            except (ValueError, SyntaxError, OverflowError) as error:
                raise self.error("invalid literal") from error
            if type(value) is float and not math.isfinite(value):
                raise self.error("number must be finite")
            return ("literal", value)
        name = self.name()
        if self.peek() == "(":
            self.take("(")
            return ("call", name, self.sequence(")", self.expression))
        return ("name", name)

    def expression(self, minimum=1):
        result = self.atom()
        while self.peek() == "[":
            self.take("[")
            index = self.expression()
            self.take("]")
            result = ("index", result, index)
        while BINDING.get(self.peek(), 0) >= minimum:
            operator = self.peek()
            if operator in COMPARE:
                tests = []
                while self.peek() in COMPARE:
                    comparator = self.peek()
                    self.take(comparator)
                    tests.append((comparator, self.expression(BINDING[comparator] + 1)))
                result = ("compare", result, tests)
            else:
                self.take(operator)
                result = ("binary", operator, result, self.expression(BINDING[operator] + 1))
        return result


class Parser:
    def __init__(self, source):
        self.lines = []
        for number, source_line in enumerate(source.splitlines(), 1):
            line = Line(number, source_line)
            if line.tokens:
                self.lines.append(line)
        self.index = 0

    def block(self, indent, inside_function=False):
        statements = []
        while self.index < len(self.lines):
            line = self.lines[self.index]
            if line.indent < indent:
                break
            if line.indent > indent:
                raise line.error("unexpected indentation")
            self.index += 1
            statements.append(self.statement(line, inside_function))
        return statements

    def body(self, header, inside_function):
        header.take(":")
        header.end()
        if self.index == len(self.lines) or self.lines[self.index].indent <= header.indent:
            raise header.error("expected an indented block")
        return self.block(self.lines[self.index].indent, inside_function)

    def conditional(self, line, inside_function):
        condition = line.expression()
        statement = Statement(line.number, "se", (condition,), self.body(line, inside_function))
        if self.index < len(self.lines):
            alternative = self.lines[self.index]
            if alternative.indent == line.indent and alternative.peek() == "o":
                self.index += 1
                alternative.take("o")
                if alternative.peek() == "se":
                    alternative.take("se")
                    statement.otherwise = [self.conditional(alternative, inside_function)]
                else:
                    statement.otherwise = self.body(alternative, inside_function)
        return statement

    def statement(self, line, inside_function):
        kind = line.peek()
        if kind == "se":
            line.take("se")
            return self.conditional(line, inside_function)
        if kind == "fora":
            if line.indent:
                raise line.error("define functions at the top level")
            line.take("fora")
            name = line.name()
            parameters = []
            if line.peek() == "toma":
                line.take("toma")
                parameters.append(line.name())
                while line.peek() == ",":
                    line.take(",")
                    parameters.append(line.name())
            if len(parameters) != len(set(parameters)):
                raise line.error("function parameters must have distinct names")
            return Statement(line.number, kind, (name, parameters), self.body(line, True))
        if kind == "denova":
            line.take("denova")
            line.take("kana")
            condition = line.expression()
            return Statement(line.number, kind, (condition,), self.body(line, inside_function))
        if kind == "norae":
            line.take("norae")
            name = line.name()
            if line.peek() == "de":
                line.take("de")
                start = line.expression()
                line.take("a")
                args = (name, start, line.expression())
            else:
                line.take("en")
                args = (name, line.expression())
            return Statement(line.number, kind, args, self.body(line, inside_function))
        if kind in {"dela", "sava", "sigra"}:
            line.take(kind)
            if kind == "dela" and not inside_function:
                raise line.error("dela belongs inside a function")
            args = (("literal", None) if kind == "dela" and line.peek() is None else line.expression(),)
        elif kind == "risa":
            line.take(kind)
            args = (line.name(),)
        elif kind == "pesa":
            line.take(kind)
            line.take("@")
            args = (line.name(), line.expression())
        elif kind == "pasa":
            line.take(kind)
            args = ()
        else:
            name = line.name()
            line.take("es")
            kind, args = "es", (name, line.expression())
        line.end()
        return Statement(line.number, kind, args)


def parse(source):
    if len(source) > 32_000 or len(source.splitlines()) > 300:
        raise SigraError(0, "program exceeds the preview source limit")
    try:
        return Parser(source).block(0)
    except RecursionError as error:
        raise SigraError(0, "program exceeds the syntax nesting limit") from error
