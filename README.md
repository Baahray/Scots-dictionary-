# Scots Dictionary

A Scots pocket dictionary with a Glasgow flavour, built for your phone:

- **Words**: every English word shows its most common Scots word; tap it to see all the Scots options, how to say each one, where it's used and an example. Searching shows every linked word and phrase. There's a word of the day too.
- **Search by meaning**: type *hit*, *slap* or *punch* and you get every Scots word for hitting – *skelp, dunt, clout, blooter, malky…* – each with what makes it different, how to say it and an example. This works for any word: similar English meanings (from WordNet) are shown too.
- **Phrases**: sayings like *haud yer wheesht* and *gonnae no*.
- **Test**: you're shown an English sentence – pick the right Scots, or type it.
- **Translate**: type a sentence and it's swapped into Scots (or back), word by word. Tap an underlined word to try another Scots option.
- **Say it**: a guide to how Scots spelling sounds (ch, ae, oo, ui, -nae and more).

It works offline once you've saved it to your phone.

**Live site:** https://baahray.github.io/Scots-dictionary-/

## Adding or fixing words

### In the app (easiest)

1. Tap **Edit** at the top of the app.
2. The first time, follow the steps on screen: make a GitHub key (Contents: Read and write, for this repository only), paste it in, and choose a password. The key is kept only on your phone, locked with your password.
3. Each word now has a pencil button to edit or delete it, and there's a **+** button to add a word. Changes save straight to `words.txt` on GitHub.
4. Tap **Done** when you're finished. Next time, **Edit** just asks for your password.

Forgot the password? Tap **Edit → Remove key** and set it up again with a new key.

### On GitHub

All the words are in **`words.txt`**. To change them:

1. Open `words.txt` on GitHub and tap the pencil ✏️ icon.
2. Edit or add lines in this format:

   ```
   english | scots | how to say it | note | example
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

## Topics

`topics.txt` lists groups of Scots words that share a meaning (hitting, crying, drunk, tired…):

```
id | title | English words that bring it up in search | short intro
```

To put a word in a topic, add `topic: id` to the note of its line in `words.txt`.

`meanings.json` links English words with similar meanings so search can find related entries. It's made from [WordNet](https://wordnet.princeton.edu/) (Princeton University, free licence) and rebuilt when the word list changes a lot.

## Translator rules (`data/phrase-rules.json`)

English → Scots translation works in this order, Glasgow / West Central speech by default:

1. **Phrase rules** – multi-word patterns checked first, with look-ahead slots. `give me a drink of {drink}` gives *gies a drap ae watter* for water, *gies a dram* for whisky, *gies a swally* for booze, *gies a drink ae ginger* for juice or pop, *gies a mug ae tea* for tea, and *gies a drink ae …* for anything else.
2. **Single-word choices** (`words`) – e.g. of → *ae*, find → *fun*, round → *roon*, through → *throu*, above → *abune*, give me → *gies*.
3. **The word list** (`words.txt`), with Glasgow lines preferred.
4. **The dictionary's English keywords** (`data/scots-dictionary.json`), e.g. archway → *pend*.

Words in `never_use` (cuppa, shoosh, yon…) are never given. To add an idiom, add a rule to `rules`: rules are tried top to bottom, so put specific patterns above general ones.

## Structured dataset (`data/scots-dictionary.json`)

1,745 Scots headwords, built from every row of the Wiktionary file (via kaikki.org), as JSON:

```
headword, variants, ipa, phonetic, pos, register, region, etymology, definition, keywords, usage_notes, example_scots, example_en, cross_references
```

- **Original writing:** every definition, origin note and example sentence was written for this dictionary (`data/original-content.txt`). Nothing is copied from another dictionary; the source file only supplied which words exist.
- **Kept:** genuine Scots words and idioms. **Left out:** names, symbols, numbers, contractions, grammar forms, English words used with their English meaning, general British/American slang, made-up respellings of English, and slurs. Rows checked by hand and left out are marked `DROP`.
- **Shared with English:** words like *black*, *fair*, *clean*, *close*, *press* and *piece* appear only for their Scots meanings (*black affrontit*, *fair puggled*, a *jeely piece*) – see `data/extra-scots-senses.txt`.
- **Variants:** different spellings of one word are grouped under one headword (*frae, thrae* → *fae*; *nihin, nithin* → *naething*), and the parts of speech of one word are combined in one entry.
- **phonetic:** CAPITALS = stress; `a` as in cat, `aw` as in law/braw, `o` as in clock, `oo` as in hoose, `kh` as in loch, `'` = Glasgow glottal stop (e.g. `WAT-tur / WA'-ur`). Words in the app's word list use its checked pronunciations; the rest are generated from the spelling, so treat them – and the broad IPA – as a guide, not gospel.
- **register / region:** from the source labels (archaic, Shetland, South Scots…) and the app's notes; *General Scots* when nothing more specific is known.
- **usage_notes:** when to use a word, when not to, common mix-ups and regional differences (*thon* in Glasgow vs *yon* elsewhere). About 440 everyday words have hand-written notes (`data/usage-notes.txt`); the rest get a shorter note built from their region, register and spellings. The app shows them on the word card under "How to use it" (from `data/usage-notes.json`).
- **etymology:** short origin notes; "Origin uncertain." where it isn't known.

The app reads `words.txt`; its last section ("More Scots words") is generated from the dataset, and edits made in the app are kept when it is rebuilt. Rebuild both with `python3 tools/build_json.py <kaikki-scots.tsv> words.txt topics.txt data/scots-dictionary.json --words` (needs `wordfreq` and `nltk` with WordNet).

## Sources and credits

Most words were written for this dictionary. Some come from:

- **Wiktionary** (Scots entries, via [kaikki.org](https://kaikki.org)), licensed under [CC BY-SA 4.0](https://creativecommons.org/licenses/by-sa/4.0/). Under that licence, the word list (`words.txt`) is also shared under CC BY-SA 4.0.
- **Alexander Warrack, *A Scots Dialect Dictionary*** (W. & R. Chambers, 1911), [on the Internet Archive](https://archive.org/details/cu31924026538813). Public domain. Words from it are marked "Warrack 1911".
