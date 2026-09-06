from app.core.step_display import step_plain_text


cases = [
    (
        "breaks",
        "one<BR />two<br>three<br />four<BR>five",
        "one\ntwo\nthree\nfour\nfive",
    ),
    (
        "bold italic",
        "<b>bold</b> and <i>italic</i>",
        "bold and italic",
    ),
    (
        "reference",
        "<ref='Mat.1.13'>Mat.1:13</ref>",
        "Mat.1:13",
    ),
    (
        "semantic wrappers",
        "<note>note text</note> <greek>δοῦλος</greek> "
        "<def>definition</def> <corr>ἀγάπῃ</corr>",
        "note text δοῦλος definition ἀγάπῃ",
    ),
    (
        "bibliographic wrappers",
        '<a href="javascript:void(0)" title="Aristotle Philosopher">'
        "Refs 4th c.BC</a> "
        "<date>variant dates<author>Anthology Palantina</author></date>",
        "Refs 4th c.BC variant datesAnthology Palantina",
    ),
    (
        "re wrapper",
        "<re><i>SYN.</i>: related lexical discussion.</re>",
        "SYN.: related lexical discussion.",
    ),
    (
        "literal angle notation",
        "future<->past",
        "future<->past",
    ),
    (
        "unknown markup preserved",
        "before<unknown>inside</unknown>after",
        "before<unknown>inside</unknown>after",
    ),
]

failed = False

for name, source, expected in cases:
    actual = step_plain_text(source)

    if actual != expected:
        failed = True
        print(f"FAIL {name}")
        print(f"  expected: {expected!r}")
        print(f"  actual:   {actual!r}")
    else:
        print(f"PASS {name}")

if failed:
    raise SystemExit(1)

print()
print("ALL STEP DISPLAY TESTS PASSED")
