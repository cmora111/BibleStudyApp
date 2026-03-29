# Strong's Word Study Module

The Strong's module adds:

- Strong's lexicon storage in SQLite
- verse-to-Strong's code linking
- lexicon CSV import
- lookup by Strong's ID such as `G26` or `H2617`
- keyword search across lemma, transliteration, definition, and gloss
- occurrence search for verses containing a specific Strong's code

## Bible import with Strong's codes

Pipe-delimited import files may include a fifth column:

```text
john|3|16|For God so loved the world...|G1063 G2316 G25 G3588 G2889
```

The code list is stored on the verse record and used by the UI and study assistant.

## Lexicon CSV format

```csv
strongs_id,lemma,transliteration,definition,language,gloss
G26,ἀγάπη,agape,self-giving love,Greek,love
H2617,חֶסֶד,chesed,covenant love or steadfast mercy,Hebrew,steadfast love
```
