# Scots Dictionary

A Scots pocket dictionary with a Glasgow flavour, built for your phone:

- **Words**: search over 1,000 Scots words and phrases, English → Scots or Scots → English, with a play button to hear each one.
- **Translate**: type a sentence and it's swapped into Scots (or back), word by word. Tap an underlined word to try another Scots option.
- **Say it**: a guide to how Scots spelling sounds (ch, ae, oo, ui, -nae and more).

It works offline once you've saved it to your phone.

**Live site:** https://baahray.github.io/Scots-dictionary-/

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

## Sources and credits

Most words were written for this dictionary. Some come from:

- **Wiktionary** (Scots entries, via [kaikki.org](https://kaikki.org)), licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Under that licence, the word list (`words.txt`) is also shared under CC BY-SA 4.0.
- **Alexander Warrack, *A Scots Dialect Dictionary*** (W. & R. Chambers, 1911), [on the Internet Archive](https://archive.org/details/cu31924026538813). Public domain. Words from it are marked "Warrack 1911".
