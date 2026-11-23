# Scots Dictionary

An English ⇄ Scots dictionary, Scots words only, with a Glasgow flavour. You can search it, flip it between English → Scots and Scots → English, and it still works offline once you've saved it to your phone.

**Live site:** https://baahray.github.io/scots-dictionary-/

## Adding or fixing words

All the words are in **`words.txt`**. To change them:

1. Open `words.txt` on GitHub and tap the pencil ✏️ icon.
2. Edit or add lines in this format:

   ```
   english | scots | note
   ```

   - Separate several Scots words with commas: `child | wean, bairn`
   - The note is optional: `toilet | cludgie, lavvy | slang`
   - Lines that start with `#` are ignored.
   - The site sorts everything A–Z itself, so new lines can go anywhere.
3. Tap **Commit changes**. The site updates within a minute or two.

## Saving it to your phone

- **iPhone (Safari):** open the site → Share button → **Add to Home Screen**.
- **Android (Chrome):** open the site → ⋮ menu → **Add to Home screen** / **Install app**.

## Files

| File | What it is |
|------|-----------|
| `words.txt` | The word list, the only file you need to edit |
| `index.html` | The dictionary page |
| `manifest.json`, `sw.js`, `icon-*.png` | Let it install on your phone and work offline |
