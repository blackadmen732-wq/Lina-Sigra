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

MIT, see `LICENSE`. This covers this repository only (Sigra Code, Sigra Wire and the word registry).
EdgeBot, its strategies and its Decision Replay are not part of this grant.
