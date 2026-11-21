# Lina Sigra parser preview

Lina is the Eldorian vocabulary. Sigra Code uses those words in small programs.
Sigra Wire encodes Eldorian text as ordered tokens. EdgeBot uses the same word
registry for its separate Sigra Rules evaluator.

## Run a program

Use Python 3.8 or newer. Open a terminal in the extracted folder.

    python3 sigra.py examples/sela.sg
    python3 sigra.py examples/fibonacci.sg
    python3 -m unittest discover -s tests

A Sigra program looks like this.

    risk es 91
    se risk >= 80:
        sava "PAUSE"
    o:
        sava "WATCH"

Use "es" to assign a value and "=" to compare expressions. "o" combines
conditions and "o:" starts an else block. Start a comment with "--" at the
beginning of a line or after a space.

The parser reports errors against the original Sigra line. It accepts numbers,
strings, booleans, flat lists, arithmetic, comparisons, branches, loops, top-level
functions, and the built-in statements used in the bundled examples. "risa"
reads text. Blocks use spaces for indentation.

The interpreter evaluates Sigra statements directly. This preview uses Python
as its implementation language and has no Python expression fallback. Arbitrary
Python functions, object attributes, and imports are outside the grammar.
The old Python export and interactive mode are outside this preview's scope.
Run reviewed examples locally. This preview has limits on execution steps,
function depth, and output, and has not been reviewed as a security sandbox.

## Built-in helpers (v0.2)

    sava "risk " + letra(91)        -- letra (letter): a number, vora/falsa or nul as text
    sava lorga([35, 62, 91])        -- lorga (long): the length of a list or a text
    x es [1, 2] + [3]               -- lists join with +

"+" stays strict: text joins only with text, so "risk " + 91 is an error that tells you to use letra(...).
Built-in names can't be redefined. A list holds at most 1,000 values.

Limits are set by whoever runs the program (the host): run(source, steps=..., output=..., depth=...).
From the command line, use --steps (default 10,000). python3 sigra.py --version prints the version.

## Sigra Wire

    python3 lina_sigra.py encode "Crème brûlée -12.5"
    python3 lina_sigra.py decode "1001 2030 0098 0099"

The decoder requires a complete message frame and reports bad tokens. Negative
decimals stay together. Accented French text survives NFC normalization and
unknown words use the data marker 0092. The text codec normalizes case and
punctuation.

An instruction such as 'pesa @starline "Mi ama Eldoria."' prints a local packet.
The crc16-ccitt-v1 packet uses the order-sensitive CRC-16 from EdgeBot PR #32,
over the UTF-8 bytes of its tokens joined by single spaces. The CRC covers token
text, including unknown words. Destination metadata, sender identity, and
authorization belong to the host. There is no network transport in this preview.

## Word registry and bot rules

The bundled registry matches EdgeBot's copy byte for byte. In Code, "es" assigns
a value. In existing EdgeBot rules, "es" is the comparison word. The rules grammar
and Decision Replay receipts stay with EdgeBot. Use the exact evaluator version
identified by a saved receipt to replay it.

## License

Copyright (c) 2026 Jahf Mark Aldonza.

Licensed under the GNU Affero General Public License v3.0 only (AGPL-3.0-only); see `LICENSE`. In short:
you may use, study, change and share this code; if you share it or a changed version, or run a changed version
for others over a network, you must make the full source available under the same license, keep this copyright
notice, and mark what you changed. The license also includes a patent grant.

For a different license (for example, to use Lina Sigra inside a closed product), contact the copyright holder.

This covers this repository only (Sigra Code, Sigra Wire and the word registry). EdgeBot, its strategies and
its Decision Replay are not part of it.

## Trademark

"Lina Sigra", "Sigra Code" and "Sigra Wire" are trademarks of Jahf Mark Aldonza. The license covers the code,
not the names: a changed version must not be presented as the official Lina Sigra.
