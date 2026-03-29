# Release Notes v8.1

## Focus
UI lookup reliability.

## Added
- canonical book normalizer
- abbreviation support
- fuzzy book matching

## Fixed
- verse lookup failures when the DB contains the verse but the UI uses a different book spelling
- common typo handling such as `galations`

## Recommended next step
Merge the v8 scholar UI wiring with the v8.1 book normalizer so both scholar tokens and reliable lookup work together.
