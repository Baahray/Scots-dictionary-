"""Convert every authentic Scots entry in the kaikki.org Scots Wiktionary TSV into the JSON schema:
headword, variants, ipa, phonetic, pos, register, region, etymology, definition, example_scots, example_en, cross_references
"""
import re, html, sys, json, difflib
from collections import defaultdict
from wordfreq import zipf_frequency as zf
from nltk.corpus import wordnet as wn


def english_same_meaning(word, gloss_text):
    """True if English uses this exact spelling with this meaning (e.g. 'poem', 'daft' = foolish)."""
    gw = set(re.findall(r"[a-z]+", gloss_text.lower()))
    for s in wn.synsets(word.replace("-", "_")):
        if any(d.name().startswith("scotland") for d in s.region_domains()):
            continue                                      # WordNet itself marks this sense as Scottish
        names = set()
        for x in [s] + s.similar_tos() + s.hypernyms()[:1]:
            names |= {l.lower().replace("_", " ") for l in x.lemma_names()}
        if names & gw:
            return True
    return False

SRC, WORDS, TOPICS, OUT = sys.argv[1:5]

# ---------------------------------------------------------------- source
SKIP_POS = {"symbol", "character", "abbrev", "name", "article", "particle"}
POS = {"noun": "Noun", "verb": "Verb", "adj": "Adjective", "adv": "Adverb", "pron": "Pronoun", "prep": "Preposition",
       "num": "Numeral", "intj": "Interjection", "det": "Determiner", "conj": "Conjunction", "phrase": "Idiom"}
FORM_OF = re.compile(r"^(?:(?:alternative|obsolete|archaic|dated|rare|eye[- ]dialect|scots)\s+)*(?:form|spelling|variant)s? of\s+([^\s,.;:(]+)", re.I)
INFL = re.compile(r"^(?:(?:simple )?past|past participle|present participle|plural|comparative|superlative|third-person|second-person|first-person|feminine|diminutive|gerund|inflection)\b", re.I)


def clean(s):
    return re.sub(r"\s+", " ", s).strip()


def strip_labels(s):
    labels = []
    while True:
        m = re.match(r"^\(([^()]{1,70})\)\s*", s)
        if not m:
            break
        labels += [x.strip() for x in m.group(1).split(",") if x.strip()]
        s = s[m.end():]
    return labels, s.strip()


def gloss(sense, head=None):
    m = re.search(r"\(“([^”]+)”\)", sense)
    g = (m.group(1) if m else sense).strip().rstrip(".")
    g = re.sub(r"\s*\([^)]*\)", "", g)
    g = re.sub(r"^(to|a|an|the)\s+", "", g, flags=re.I)
    parts = [p.strip().lower() for p in re.split(r"[;,]", g) if p.strip()]
    if head and len(parts) > 1 and parts[0] == head.lower():
        parts = parts[1:]
    return parts[0] if parts else ""


rows = []
for line in open(SRC, encoding="utf-8"):
    line = line.rstrip("\n")
    if "\t" not in line:
        continue
    heads, defs = line.split("\t", 1)
    forms = [clean(f) for f in heads.split("|") if f.strip()]
    for pos, body in re.findall(r"<i>([^<]+)</i><br><ol>(.*?)</ol>", defs):
        senses = [clean(html.unescape(re.sub(r"<[^>]+>", "", s))) for s in re.findall(r"<li>(.*?)</li>", body)]
        senses = [s for s in senses if s]
        if senses and forms:
            rows.append((forms[0], forms[1:], pos.strip(), senses))

plain = {}
for head, _, pos, senses in rows:
    _, s = strip_labels(senses[0])
    if not FORM_OF.match(s) and not INFL.match(s) and not s.lower().startswith("contraction"):
        plain.setdefault(head.lower(), gloss(s, head))


CHECKED = set()
for _l in open(WORDS, encoding="utf-8"):
    if _l.startswith("# ---------- More Scots words from Wiktionary"):
        break
    if "|" in _l and not _l.startswith("#"):
        for _s in _l.split("|")[1].split(","):
            if _s.strip() and " " not in _s.strip():
                CHECKED.add(_s.strip().lower())

# ---------------------------------------------------------------- authentic-Scots filter
def keep(head, pos, senses):
    if pos in SKIP_POS: return None, "name / symbol / contraction"
    if re.search(r"\d", head) or not re.search(r"[a-z]", head): return None, "digits / proper name"
    labels, s = strip_labels(senses[0])
    if s.lower().startswith("contraction"): return None, "name / symbol / contraction"
    if INFL.match(s): return None, "grammar form"
    m = FORM_OF.match(s)
    en = plain.get(m.group(1).lower()) if m else gloss(s, head)
    if not en: return None, "form of unknown word"
    hl = head.lower()
    if hl == "bra" and pos == "noun": return None, "English word (same meaning)"
    if hl in CHECKED: return en, None                     # on the hand-checked Scots list
    if hl == en or hl in re.findall(r"[a-z']+", en): return None, "same as English"
    if " " not in hl and zf(hl, "en") >= 4.0: return None, "common English word"
    if re.search(r"(ass|arse)hole|shit|piss", hl): return None, "slur / vulgar"
    if " " not in hl and zf(hl, "en") >= 3.5 and english_same_meaning(hl, en + " " + " ".join(strip_labels(x)[1] for x in senses[:2])):
        return None, "English word (same meaning)"
    if "ee" in hl and "ee" not in en and "i" in en and len(en) >= 4: return None, "made-up respelling"
    if any(w in hl for w in ("cunt", "fuck")) or "deej" == hl: return None, "slur / vulgar"
    if any(l.lower() in ("slang",) for l in labels) and zf(hl, "en") >= 2.5: return None, "English slang"
    sim = " " not in en and difflib.SequenceMatcher(None, hl, en).ratio() >= 0.6
    if sim and zf(en, "en") < 4.5: return None, "respelling of uncommon word"
    return en, None


# ---------------------------------------------------------------- tags
REGION = [("south scots", "Borders"), ("hawick", "Borders"), ("borders", "Borders"), ("galloway", "General Scots"),
          ("shetland", "Insular"), ("orkney", "Insular"), ("caithness", "Doric/North East"), ("doric", "Doric/North East"),
          ("north east", "Doric/North East"), ("aberdeen", "Doric/North East"), ("glasgow", "West Central/Glasgow"),
          ("west central", "West Central/Glasgow"), ("edinburgh", "East/Mid"), ("fife", "East/Mid"), ("lothian", "East/Mid")]
OLD = ("obsolete", "archaic", "middle scots", "obsolescent", "historical", "dated")
LIT = ("poetic", "literary")
COLL = ("slang", "colloquial", "informal", "vulgar")


def tags(labels, curated_note):
    reg, rgn = [], []
    for l in labels:
        k = l.lower()
        if any(o in k for o in OLD) and "Archaic" not in reg: reg.append("Archaic")
        if any(o in k for o in LIT) and "Traditional/Literary" not in reg: reg.append("Traditional/Literary")
        if any(o in k for o in COLL) and "Modern/Colloquial" not in reg: reg.append("Modern/Colloquial")
        for name, r in REGION:
            if name in k and r not in rgn: rgn.append(r)
    n = (curated_note or "").lower()
    if "glasgow" in n and "West Central/Glasgow" not in rgn: rgn.append("West Central/Glasgow")
    if re.search(r"\bne\b", n) and "Doric/North East" not in rgn: rgn.append("Doric/North East")
    if curated_note is not None and not reg: reg.append("Everyday/Spoken")   # in the everyday list
    if "slang" in n and "Modern/Colloquial" not in reg: reg.append("Modern/Colloquial")
    if not rgn: rgn = ["General Scots"]
    return reg, rgn


# ---------------------------------------------------------------- pronunciation (rule-based)
# Respelling rules: CAPITALS = stress; a = cat; aw = law/braw; o = clock; oo = hoose/moon; kh = loch; ' = Glasgow glottal stop
V = [("aa", "aw", "ɑː"), ("ui", "i", "ɪ"), ("ou", "oo", "u"), ("oo", "oo", "u"), ("ow", "ow", "ʌu"), ("au", "aw", "ɑː"),
     ("aw", "aw", "ɑː"), ("ae", "ay", "e"), ("ai", "ay", "e"), ("ay", "ay", "e"), ("ei", "ee", "i"), ("ee", "ee", "i"),
     ("ea", "ee", "i"), ("ie", "ee", "i"), ("ey", "ay", "e"), ("oa", "oh", "o"), ("oi", "oy", "əi"), ("oy", "oy", "əi"),
     ("eu", "yoo", "ju"), ("a", "a", "a"), ("e", "e", "ɛ"), ("i", "i", "ɪ"), ("o", "o", "ɔ"), ("u", "u", "ʌ"), ("y", "ee", "i"),
     ("ü", "oo", "ø")]
C = [("tch", "ch", "tʃ"), ("sch", "sk", "sk"), ("ch", "kh", "x"), ("gh", "kh", "x"), ("sh", "sh", "ʃ"), ("th", "th", "θ"),
     ("wh", "wh", "ʍ"), ("ph", "f", "f"), ("ck", "k", "k"), ("ng", "ng", "ŋ"), ("qu", "kw", "kw"), ("dg", "j", "dʒ"),
     ("b", "b", "b"), ("c", "k", "k"), ("d", "d", "d"), ("f", "f", "f"), ("g", "g", "ɡ"), ("h", "h", "h"), ("j", "j", "dʒ"),
     ("k", "k", "k"), ("l", "l", "l"), ("m", "m", "m"), ("n", "n", "n"), ("p", "p", "p"), ("r", "r", "r"), ("s", "s", "s"),
     ("t", "t", "t"), ("v", "v", "v"), ("w", "w", "w"), ("x", "ks", "ks"), ("z", "z", "z")]
SHORT = {"a", "e", "i", "o", "u"}
UNSTRESSED_PREFIX = ("a", "be", "for", "un", "ower", "aff")


def units(word):
    """[kind, respelling, ipa, doubled]"""
    w = word.lower().replace("'", "").replace("’", "")
    syll_le = bool(re.search(r"[^aeiouy]le$", w)) and len(w) > 3
    if syll_le:
        w = w[:-2]
    out, i = [], 0
    while i < len(w):
        for g, r, p in V:
            if w.startswith(g, i):
                if g == "y" and (i == 0 or (i + 1 < len(w) and w[i + 1] in "aeiou")):
                    out.append(["C", "y", "j", False]); i += 1; break
                if g == "e" and i == len(w) - 1 and len(out) >= 2 and out[-1][0] == "C" and out[-2][0] == "V":
                    long = {"a": ("ay", "e"), "i": ("y", "əi"), "o": ("oh", "o"), "u": ("oo", "u"), "e": ("ee", "i")}
                    if out[-2][1] in long:
                        out[-2][1], out[-2][2] = long[out[-2][1]]
                    i += 1; break
                out.append(["V", r, p, False]); i += len(g); break
        else:
            for g, r, p in C:
                if w.startswith(g, i):
                    if g == "ch" and (i == 0 or w[i - 1] not in "aeiouy"):
                        r, p = "ch", "tʃ"
                    if g == "c" and i + 1 < len(w) and w[i + 1] in "eiy":
                        r, p = "s", "s"
                    if out and out[-1][0] == "C" and out[-1][1] == r:
                        out[-1][3] = True               # doubled consonant (tt, bb…)
                    else:
                        out.append(["C", r, p, False])
                    i += len(g); break
            else:
                i += 1
    if syll_le:
        out += [["V", "u", "ə", False], ["C", "l", "l", False]]
    return out


def syllables(us):
    vidx = [i for i, u in enumerate(us) if u[0] == "V"]
    if len(vidx) < 2:
        return [us]
    sy, last = [], 0
    for a, b in zip(vidx, vidx[1:]):
        cons = list(range(a + 1, b))
        short = us[a][1] in SHORT
        if not cons:
            cut, dup = a + 1, None
        elif len(cons) == 1:
            c = cons[0]
            if us[c][3]:                 # doubled: WAT-tur
                cut, dup = c + 1, c
            elif short:                  # short vowel keeps the consonant: WAB-it
                cut, dup = c + 1, None
            else:
                cut, dup = c, None
        else:
            cut, dup = cons[0] + 1, None
        seg = [u[:] for u in us[last:cut]]
        sy.append(seg)
        last = cut
        if dup is not None:
            us = us[:cut] + [[us[dup][0], us[dup][1], "", False]] + us[cut:]
            vidx = [i if i < cut else i + 1 for i in vidx]
    sy.append(us[last:])
    return [s for s in sy if s]


def stress_index(word, n):
    w = word.lower()
    if n > 1:
        for p in UNSTRESSED_PREFIX:
            if w.startswith(p) and len(w) > len(p) + 2 and w[len(p)] not in "aeiou" + p[-1]:
                return 1
    return 0


def pronounce(word):
    """Returns (phonetic, ipa) for a word or phrase."""
    ph_parts, ipa_parts = [], []
    for token in re.split(r"[\s-]+", word.strip()):
        if not token:
            continue
        sy = syllables(units(token))
        si = stress_index(token, len(sy))
        resp, ipas = [], []
        for k, s in enumerate(sy):
            r = "".join(u[1] for u in s)
            p = "".join(u[2] for u in s)
            if k != si and k == len(sy) - 1 and r.endswith("er"):      # unstressed -er: WAT-tur
                r, p = r[:-2] + "ur", p[:-2] + "ər"
            resp.append(r); ipas.append(p)
        if len(resp) > 1:
            resp[si] = resp[si].upper()
            ph = "-".join(resp)
            ipa = "".join(("ˈ" if i == si else "") + x for i, x in enumerate(ipas))
        else:
            ph, ipa = (resp[0] if resp else token), (ipas[0] if ipas else "")
        # Glasgow glottal stop for t between vowels:  WAT-tur / WA'-ur
        alt = None
        for k in range(len(resp) - 1):
            if resp[k][-1:].lower() == "t" and resp[k + 1][:1].lower() in "aeiouy" and len(resp[k]) > 1:
                parts = resp[:]; parts[k] = parts[k][:-1] + "'"; alt = "-".join(parts)
            elif resp[k][-1:].lower() == "t" and resp[k + 1][:1].lower() == "t":
                parts = resp[:]; parts[k] = parts[k][:-1] + "'"; parts[k + 1] = parts[k + 1][1:]; alt = "-".join(parts)
            if alt:
                break
        ph_parts.append(ph + (" / " + alt if alt else ""))
        ipa_parts.append(ipa)
    return " ".join(ph_parts), "/" + " ".join(ipa_parts) + "/"


SAY_IPA = [("aw", "ɑː"), ("ay", "e"), ("ee", "i"), ("oo", "u"), ("ow", "ʌu"), ("oy", "əi"), ("kh", "x"), ("ch", "tʃ"),
           ("sh", "ʃ"), ("th", "θ"), ("ng", "ŋ"), ("wh", "ʍ"), ("ur", "ər"), ("oh", "o"), ("a", "a"), ("e", "ɛ"), ("i", "ɪ"),
           ("o", "ɔ"), ("u", "ʌ"), ("y", "əi"), ("j", "dʒ"), ("g", "ɡ"), ("'", "ʔ")]


def say_ipa(phon):
    """'HAY-vur' -> /ˈhevər/ (first form only)."""
    first = phon.split(" / ")[0]
    parts = first.split("-")
    out = []
    for p in parts:
        stressed = len(parts) > 1 and p.isupper()
        s, i, ipa = p.lower(), 0, ""
        while i < len(s):
            for g, v in SAY_IPA:
                if s.startswith(g, i):
                    if g == "ur" and stressed:
                        v = "ʌr"
                    ipa += v; i += len(g); break
            else:
                ipa += s[i]; i += 1
        out.append(("ˈ" if stressed else "") + ipa)
    ipa = "".join(out)
    ipa = re.sub(r"([bdfɡklmnprstvz])ˈ?\1", lambda m: m.group(0).replace(m.group(1), "", 1), ipa)   # WAT-tur: one t sound
    return "/" + ipa + "/"


def stress_say(say, head, fallback):
    """'hay-ver' -> 'HAY-vur' (checked spelling from the app, put into the stress format)."""
    say = re.sub(r"\s*\(.*?\)", "", say.lower()).strip()
    if not re.fullmatch(r"[a-z'-]+", say):
        return fallback
    parts = [x for x in say.split("-") if x]
    if len(parts) == 1:
        if "-" in fallback.split(" / ")[0]:
            return fallback                      # e.g. 'watter' -> WAT-tur / WA'-ur
        return parts[0]
    si = stress_index(head, len(parts))
    if parts[-1].endswith("er") and si != len(parts) - 1:
        parts[-1] = parts[-1][:-2] + "ur"
    parts[si] = parts[si].upper()
    out = "-".join(parts)
    for k in range(len(parts) - 1):       # Glasgow glottal stop
        if parts[k][-1:].lower() == "t" and parts[k + 1][:1].lower() in "aeiouy":
            q = parts[:]; q[k] = q[k][:-1] + "'"; return out + " / " + "-".join(q)
    return out


# ---------------------------------------------------------------- data from the app's own word list
curated_note, curated_ex, topic_of, curated_en, curated_say = {}, {}, {}, defaultdict(set), {}
in_wikt = False
for l in open(WORDS, encoding="utf-8"):
    if l.startswith("# ---------- More Scots words from Wiktionary"):
        in_wikt = True
    if "|" not in l or l.startswith("#"):
        continue
    p = [x.strip() for x in l.split("|")]
    note = p[3] if len(p) > 3 else ""
    ex = p[4] if len(p) > 4 else ""
    scots_here = [s.strip().lower() for s in p[1].split(",") if s.strip()]
    says = [s.strip() for s in (p[2] if len(p) > 2 else "").split(",")]
    for j, k in enumerate(scots_here):
        if not in_wikt and j < len(says) and says[j] and " " not in k and k not in curated_say:
            curated_say[k] = says[j]
        curated_en[k].add(p[0].lower())
        if not in_wikt and (len(scots_here) == 1 or "topic:" in note):
            curated_note.setdefault(k, note)
        ex_words = re.findall(r"[a-z']+", ex.lower())
        if ex and not in_wikt and k not in curated_ex and (k in ex_words or any(w.startswith(k) for w in ex_words)):
            curated_ex[k] = ex
        m = re.search(r"topic:\s*([a-z-]+)", note)
        if m:
            topic_of.setdefault(k, set()).add(m.group(1))

# ---------------------------------------------------------------- build entries
entries, dropped = {}, defaultdict(int)
SUFFIX = re.compile(r"^(s|es|in|ing|it|t|ed|d|er|ers|est|ies|en|'s)$")
for head, forms, pos, senses in rows:
    en, why = keep(head, pos, senses)
    if why:
        dropped[why] += 1
        continue
    key = (head.lower(), POS.get(pos, pos.title()))
    labels_all = []
    for s in senses:
        for lab in strip_labels(s)[0]:
            if lab not in labels_all:
                labels_all.append(lab)
    defs = [strip_labels(s)[1].rstrip(".") for s in senses]
    defs = [d for d in defs if d]
    hl = head.lower()
    variants = []
    for f in forms:
        fl = f.lower()
        if fl == hl or " " in f and " " not in head:
            continue
        if fl.startswith(hl) and SUFFIX.match(fl[len(hl):]):   # inflection, not a spelling variant
            continue
        if re.match(r"^(maist|mair) ", fl) or zf(fl, "en") >= 3.5:
            continue
        if fl not in [v.lower() for v in variants]:
            variants.append(f)
    if key in entries:   # same word & part of speech: merge senses
        e = entries[key]
        for d in defs:
            if d not in e["_defs"]:
                e["_defs"].append(d)
        continue
    reg, rgn = tags(labels_all, curated_note.get(hl))
    phon, ipa = pronounce(head)
    if hl in curated_say:
        phon = stress_say(curated_say[hl], head, phon)
        if phon.split(" / ")[0].lower().replace("-", "") != hl.replace("-", ""):   # respelled: IPA follows it
            ipa = say_ipa(phon)
    ex = curated_ex.get(hl, "")
    m = re.match(r"^(.*?)\s*\(([^()]*)\)\s*$", ex)
    entries[key] = {
        "headword": head, "variants": variants[:8], "ipa": ipa, "phonetic": phon, "pos": POS.get(pos, pos.title()),
        "register": reg, "region": rgn, "etymology": "",
        "_defs": defs, "_gloss": en,
        "example_scots": (m.group(1).strip() if m else ex.strip()), "example_en": (m.group(2).strip() if m else ""),
        "cross_references": [],
    }

# ---------------------------------------------------------------- original writing
# Every definition, origin note and example comes from data/original-content.txt (written for this dictionary),
# never from the source file. Rows marked DROP were checked by hand and left out. Rows not yet written are left out.
import os, subprocess
HERE = os.path.dirname(os.path.abspath(OUT))
orig = {}
for l in open(os.path.join(HERE, "original-content.txt"), encoding="utf-8"):
    if l.startswith("#") or not l.strip():
        continue
    p = [x.strip() for x in l.rstrip("\n").split(" | ")]
    orig[(p[0].lower(), p[1])] = p[2:]
not_written = []
for key in list(entries):
    e = entries[key]
    o = orig.get((e["headword"].lower(), e["pos"]))
    if o is None:
        not_written.append(e["headword"]); del entries[key]; continue
    if o[0] == "DROP":
        dropped["checked by hand: not Scots"] += 1; del entries[key]; continue
    gl, df, et, exs, exe = (o + [""] * 5)[:5]
    e["_gloss"], e["_defs"], e["etymology"] = gl, [df], et
    if not e["example_scots"]:
        e["example_scots"], e["example_en"] = exs, exe

# words Scots shares with English, kept only for their own Scots meanings
EXTRA_HEADS = set()
for l in open(os.path.join(HERE, "extra-scots-senses.txt"), encoding="utf-8"):
    if l.startswith("#") or not l.strip():
        continue
    h, var, pos, reg, rgn, gl, df, et, exs, exe = [x.strip() for x in l.rstrip("\n").split("|")]
    key = (h.lower(), pos)
    EXTRA_HEADS.add(h.lower())
    if key in entries:
        e = entries[key]
        if df not in e["_defs"]: e["_defs"].append(df)
        continue
    phon, ipa = pronounce(h)
    if h.lower() in curated_say:
        phon = stress_say(curated_say[h.lower()], h, phon)
        if phon.split(" / ")[0].lower().replace("-", "") != h.lower().replace("-", ""): ipa = say_ipa(phon)
    entries[key] = {"headword": h, "variants": [v.strip() for v in var.split(",") if v.strip()], "ipa": ipa, "phonetic": phon,
                    "pos": pos, "register": [reg], "region": [rgn], "etymology": et, "_defs": [df], "_gloss": gl,
                    "example_scots": exs, "example_en": exe, "cross_references": []}

# changes made in the app to the word list's Wiktionary section ("Edit: … → …" commits): keep them
user_lines = {}
try:
    log = subprocess.run(["git", "-C", os.path.dirname(os.path.abspath(WORDS)), "log", "--reverse", "--grep=^Edit", "-p",
                          "--unified=0", "--format=format:@@COMMIT", "--", "words.txt"], capture_output=True, text=True).stdout
    for chunk in log.split("@@COMMIT"):
        minus = [x[1:] for x in chunk.splitlines() if x.startswith("-") and not x.startswith("---") and "Wiktionary" in x]
        plus = [x[1:] for x in chunk.splitlines() if x.startswith("+") and not x.startswith("+++")]
        for a, b in zip(minus, plus):
            old = a.split("|")[1].strip().lower(); user_lines[old] = b
except Exception:
    pass
for old, line in user_lines.items():
    p = [x.strip() for x in line.split("|")]
    for e in entries.values():
        if e["headword"].lower() == old:
            e["variants"] = [e["headword"]] + e["variants"]
            e["headword"] = p[1].split(",")[0].strip()
            if len(p) > 2 and p[2]: e["phonetic"] = p[2].split(",")[0].strip()

# hand-set sounds for words the spelling rules get wrong (stress in CAPITALS, ' = Glasgow glottal stop)
SAY_FIX = {"ye": ("yee", "/ji/"), "messages": ("MES-sij-iz", "/ˈmɛsɪdʒɪz/"), "again": ("a-GEN", "/əˈɡɛn/"),
           "agent": ("AY-jent", "/ˈedʒənt/"), "black affrontit": ("blak a-FRUN-tit", "/blak əˈfrʌntɪt/"),
           "dozen": ("DOZ-un", "/ˈdɔzən/"), "worry": ("WUR-ree", "/ˈwʌri/"), "bucket": ("BUK-it / BUK-i'", "/ˈbʌkɪt/"),
           "air-yesterday": ("ayr YES-tur-day", "/er ˈjɛstərde/"), "first-fit": ("FURST-fit", "/ˈfʌrstfɪt/"),
           "ca": ("kaw", "/kɑː/")}

SAY_FIX.update({"abye": ("a-BY", "/əˈbae/"), "acre-a-bung": ("AY-kur-a-bung", "/ˈekərəbʌŋ/"), "aesomeness": ("AY-sum-nis", "/ˈesʌmnɪs/"),
    "afore": ("a-FORE", "/əˈfor/"), "aforetimes": ("a-FORE-tymz", "/əˈfortaemz/"), "aftwhiles": ("AFT-whylz", "/ˈaftʍaelz/"),
    "ance": ("anss", "/ans/"), "ance errand": ("anss ER-rand", "/ans ˈɛrənd/"), "arrie": ("AR-ree", "/ˈari/"),
    "ballion": ("BAL-yun", "/ˈbaljən/"), "beguess": ("bee-GESS", "/bɪˈɡɛs/"), "belly-flaucht": ("BEL-lee-flawkht", "/ˈbɛliflɑːxt/"),
    "benty": ("BEN-tee", "/ˈbɛnti/"), "'bootgates": ("BOOT-gayts", "/ˈbutɡets/"), "collogue": ("ko-LOHG", "/kəˈloɡ/"),
    "corbie messinger": ("KOR-bee MES-sin-jur", "/ˈkɔrbi ˈmɛsɪndʒər/"), "donnered": ("DON-nurd", "/ˈdɔnərd/"),
    "dree one's weird": ("dree wunz weerd", "/dri wʌnz wird/"), "eddication": ("ed-dee-KAY-shun", "/ɛdɪˈkeʃən/"),
    "forbye": ("for-BY", "/fɔrˈbae/"), "guesten": ("GEST-en", "/ˈɡɛstən/"), "gullion": ("GUL-yun", "/ˈɡʌljən/"),
    "hamespun": ("HAYM-spun", "/ˈhemspʌn/"), "hellicat": ("HEL-lee-kat", "/ˈhɛlɪkat/"), "hellisom": ("HEL-lee-sum", "/ˈhɛlɪsəm/"),
    "ithergates": ("ITH-ur-gayts", "/ˈɪðərɡets/"), "lang acre": ("lang AY-kur", "/laŋ ˈekər/"), "mallivoag": ("MAL-lee-vohg", "/ˈmalivoɡ/"),
    "menseless": ("MENSS-liss", "/ˈmɛnsləs/"), "mirligoes": ("MIR-lee-gohz", "/ˈmɪrliɡoz/"), "on one's groof": ("on wunz groof", "/ɔn wʌnz ɡruf/"),
    "preses": ("PREE-seez", "/ˈprisiz/"), "prettikin": ("PRET-tee-kin / PRE'-ee-kin", "/ˈprɛtɪkɪn/"),
    "rickle o banes": ("RIK-ul o baynz", "/ˈrɪkəl o benz/"), "sassenach": ("SAS-sen-akh", "/ˈsasənax/"),
    "whiffinger": ("WHIF-fin-jur", "/ˈʍɪfɪndʒər/"), "whiles": ("whylz", "/ʍaelz/"), "whilk": ("whilk", "/ʍɪlk/"), "weirdfu": ("WEERD-foo", "/ˈwirdfu/")})

# ---------------------------------------------------------------- merge spelling variants into one headword
def gl_close(a, b):
    a, b = a.lower(), b.lower()
    return a == b or a in b.split("; ") or b in a.split("; ")

groups = {}                                       # headword -> list of entries (one per part of speech)
for e in entries.values():
    groups.setdefault(e["headword"].lower(), []).append(e)
parent = {h: h for h in groups}
def find(h):
    while parent[h] != h:
        parent[h] = parent[parent[h]]; h = parent[h]
    return h
def rank(h):                                       # which spelling leads: on the hand-checked list, everyday, mainstream
    es = groups[h]
    regs = {r for e in es for r in e["register"]}; rgns = {r for e in es for r in e["region"]}
    return (h in CHECKED, h in EXTRA_HEADS, "Everyday/Spoken" in regs, "General Scots" in rgns or "West Central/Glasgow" in rgns,
            "Archaic" not in regs, -len(h), h)
def union(a, b, lead=None):
    ra, rb = find(a), find(b)
    if ra == rb: return
    if lead is None: lead = ra if rank(ra) >= rank(rb) else rb
    other = rb if lead == ra else ra
    parent[other] = lead
FORM = re.compile(r"^(?:Variant of|Reduced form of|(?:Southern Scots|Shetland|Borders|Glasgow|North East) form of)\s+([a-z'-]+(?: [a-z'-]+)*)\.?$", re.I)
for h, es in groups.items():
    for e in es:
        m = FORM.match(e["etymology"])
        if m and m.group(1).lower() in groups and m.group(1).lower() != h:
            t = m.group(1).lower()
            if any(gl_close(e["_gloss"], x["_gloss"]) or e["_gloss"].lower() in x["_defs"][0].lower() for x in groups[t]):
                union(h, t, lead=find(t))
        for v in e["variants"]:
            v = v.lower()
            if v in groups and v != h and any(gl_close(e["_gloss"], x["_gloss"]) for x in groups[v]):
                union(h, v)
by_gloss0 = defaultdict(list)
for h, es in groups.items():
    if " " in h: continue
    for e in es: by_gloss0[(e["_gloss"].lower(), e["pos"])].append(h)
for (g, pos), hs in by_gloss0.items():
    hs = sorted(set(hs))
    for i, a in enumerate(hs):
        for b in hs[i + 1:]:
            if difflib.SequenceMatcher(None, a, b).ratio() >= 0.75 and a[0] == b[0]:
                union(a, b)

clusters = defaultdict(list)
for h in groups:
    clusters[find(h)].append(h)

merged = []
POS_ORDER = ["Noun", "Verb", "Adjective", "Adverb", "Pronoun", "Determiner", "Preposition", "Conjunction", "Numeral", "Interjection", "Idiom"]
for lead, members in clusters.items():
    members = [lead] + sorted((m for m in members if m != lead), key=lambda m: rank(m), reverse=True)
    senses = []                                   # (pos, gloss, definition, ex_sc, ex_en)
    variants, regs, rgns, ety, form_ety = [], [], [], "", ""
    for m in members:
        for e in sorted(groups[m], key=lambda e: POS_ORDER.index(e["pos"]) if e["pos"] in POS_ORDER else 99):
            for d in e["_defs"]:
                if not any(s[0] == e["pos"] and (gl_close(s[1], e["_gloss"]) or s[2] == d) for s in senses):
                    senses.append((e["pos"], e["_gloss"], d, e["example_scots"], e["example_en"]))
            if m == lead:
                for r in e["register"]:
                    if r not in regs: regs.append(r)
                for r in e["region"]:
                    if r not in rgns: rgns.append(r)
            if (not ety or ety.startswith("Origin uncertain")) and e["etymology"] and not FORM.match(e["etymology"]):
                ety = e["etymology"]
            if m == lead and not form_ety and FORM.match(e["etymology"]):
                form_ety = e["etymology"]
            for v in [e["headword"]] + e["variants"]:
                if v.lower() != lead and v.lower() not in [x.lower() for x in variants]:
                    variants.append(v)
    first = groups[lead][0]
    pos_list = []
    for s in senses:
        if s[0] not in pos_list: pos_list.append(s[0])
    if len(pos_list) > 1 and len({s[2] for s in senses}) > 1:
        definition = " ".join(f"({p.lower()}) " + "; ".join(s[2].rstrip(".") for s in senses if s[0] == p) + "." for p in pos_list)
    else:
        definition = "; ".join(dict.fromkeys(s[2].rstrip(".") for s in senses)) + "."
    ex = next((s for s in senses if s[3]), None)
    merged.append({"headword": first["headword"], "variants": variants[:10], "ipa": first["ipa"], "phonetic": first["phonetic"],
                   "pos": " / ".join(pos_list), "register": regs, "region": rgns or ["General Scots"],
                   "etymology": (form_ety if (not ety or ety.startswith("Origin uncertain")) and form_ety else ety) or "Origin uncertain.", "definition": definition,
                   "example_scots": ex[3] if ex else "", "example_en": ex[4] if ex else "",
                   "cross_references": [], "_senses": senses, "_members": members})

# words no longer in everyday use (data/old-words.txt): register Archaic
OLD_WORDS = {l.strip().lower() for l in open(os.path.join(HERE, "old-words.txt"), encoding="utf-8") if l.strip() and not l.startswith("#")}
for e in merged:
    if e["headword"].lower() in OLD_WORDS:
        e["register"] = ["Archaic"] + [r for r in e["register"] if r not in ("Archaic", "Everyday/Spoken")]

# a spelling that is a headword of its own is not listed as a variant of another word
heads_now = {e["headword"].lower() for e in merged}
for e in merged:
    e["variants"] = [v for v in e["variants"] if v.lower() not in heads_now]
    fix = SAY_FIX.get(e["headword"].lower())
    if fix:
        e["phonetic"], e["ipa"] = fix

# ---------------------------------------------------------------- cross references
by_gloss = defaultdict(list)
for e in merged:
    for s in e["_senses"]:
        by_gloss[s[1].lower()].append(e["headword"])
by_topic = defaultdict(list)
for k, ts in topic_of.items():
    for t in ts:
        by_topic[t].append(k)
lead_of = {}
for e in merged:
    for m in e["_members"]: lead_of[m] = e["headword"]
for e in merged:
    hl = e["headword"].lower()
    refs = [h for s in e["_senses"] for h in by_gloss[s[1].lower()]]
    for t in topic_of.get(hl, ()):
        refs += [lead_of.get(w, w) for w in by_topic[t]]
    for en in curated_en.get(hl, ()):
        for k, ens in curated_en.items():
            if en in ens and " " not in k:
                refs.append(lead_of.get(k, k))
    seen, out = {hl} | {v.lower() for v in e["variants"]}, []
    for r in refs:
        if r.lower() not in seen:
            seen.add(r.lower()); out.append(r)
    e["cross_references"] = out[:10]

order = ["headword", "variants", "ipa", "phonetic", "pos", "register", "region", "etymology", "definition",
         "example_scots", "example_en", "cross_references"]
merged.sort(key=lambda x: (x["headword"].lower().lstrip("'"), x["pos"]))
data = [{k: e[k] for k in order} for e in merged]
json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("entries:", len(data), "| merged spellings:", sum(len(e["_members"]) - 1 for e in merged), "| not yet written:", len(not_written))
print("dropped:", dict(dropped))
print("with example:", sum(1 for d in data if d["example_scots"]), "| with cross-refs:", sum(1 for d in data if d["cross_references"]),
      "| with variants:", sum(1 for d in data if d["variants"]))

# ---------------------------------------------------------------- the app's word list: rewrite its Wiktionary section
if "--words" in sys.argv:
    HEAD = "# ---------- More Scots words from Wiktionary"
    lines = open(WORDS, encoding="utf-8").read().split("\n")
    cut = next(i for i, l in enumerate(lines) if l.startswith(HEAD))
    keep_lines = lines[:cut]
    while keep_lines and not keep_lines[-1].strip(): keep_lines.pop()
    user_by_head = {[x.strip() for x in l.split("|")][1].split(",")[0].strip().lower(): l for l in user_lines.values()}
    def tidy(s): return s.replace("|", "/").strip()
    out, done_user = [], set()
    for e in merged:
        hl = e["headword"].lower()
        if hl in CHECKED: continue                 # already in the hand-checked list above
        if hl in user_by_head:
            if hl not in done_user: out.append(user_by_head[hl]); done_user.add(hl)
            continue
        vs = []
        words = [e["headword"]] + vs
        says = [e["phonetic"].split(" / ")[0]] + [pronounce(v)[0] for v in vs]
        tags_ = [r for r in e["region"] if r != "General Scots"] + [r for r in e["register"] if r != "Everyday/Spoken"]
        for pos, gl, d, xs, xe in e["_senses"]:
            note = " – ".join([("phrase – " if " " in e["headword"] else "") + pos.lower()] + tags_ +
                              ([e["etymology"].rstrip(".")] if e["etymology"] and not e["etymology"].startswith("Origin uncertain") else []))
            ex = f"{xs} ({xe})" if xs else ""
            out.append(" | ".join([tidy(gl), ", ".join(tidy(w) for w in words), ", ".join(tidy(s) for s in says), tidy(note), tidy(ex)]))
    text = "\n".join(keep_lines + ["", HEAD + " (word list via kaikki.org, CC BY-SA 4.0; meanings, origins and examples written for this dictionary) ----------"] + out) + "\n"
    open(WORDS, "w", encoding="utf-8").write(text)
    print("word list lines in Wiktionary section:", len(out))
