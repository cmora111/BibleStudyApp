# Ultimate Bible App v8.1 User Guide

## Reader lookup improvements

You can now type book names more naturally.

Examples that should work:
- `galatians`
- `galations`
- `gal`
- `rom`
- `rev`
- `1 cor`
- `2 tim`

The app normalizes these inputs before looking up the verse.

## Typical use
1. Select a translation.
2. Type a book name, abbreviation, or close spelling.
3. Enter chapter and verse.
4. Click **Go**.

## Chapter reading
The same normalization can be used for **Read Chapter** if you applied the optional patch.

## Clickable references
If your UI uses `open_reference_from_string()`, assistant references like `Galatians 3:22` will also resolve more reliably after the patch.
