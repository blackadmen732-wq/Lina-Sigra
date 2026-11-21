# Copyright (c) 2026 Jahf Mark Aldonza
# SPDX-License-Identifier: AGPL-3.0-only
"""Prepare and validate local Sigra Wire text packets."""

from lina_sigra import NAME, NEW, NUM, WireError, check, decode, encode

WIRE_VERSION = "crc16-ccitt-v1"


def _unknown_words(codes):
    words = []
    i = 0
    while i < len(codes):
        code = codes[i]
        if code == NEW:
            words.append(codes[i + 1])
        i += 2 if code in (NAME, NEW, NUM) else 1
    return words


def sigra(sentence):
    return " ".join(encode(sentence))


def pesa(agent, sentence):
    codes = encode(sentence)
    reads_as = decode(codes)
    return {
        "wire_version": WIRE_VERSION,
        "to": agent,
        "codes": " ".join(codes),
        "check": check(codes),
        "unknown_words": _unknown_words(codes),
        "reads_as": reads_as,
    }


def verify_packet(packet):
    """Verify the token CRC and parse the frame. Sender and routing are host duties."""
    if not isinstance(packet, dict) or packet.get("wire_version") != WIRE_VERSION:
        return False
    if not isinstance(packet.get("codes"), str) or type(packet.get("check")) is not int:
        return False
    codes = packet["codes"].split()
    if packet["check"] != check(codes):
        return False
    try:
        return packet.get("reads_as") == decode(codes) and packet.get("unknown_words") == _unknown_words(codes)
    except WireError:
        return False
