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
        if ex and k not in curated_ex and (k in ex_words or any(w.startswith(k) for w in ex_words)):
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

# cross references: same core meaning, or same topic in the app
by_gloss = defaultdict(list)
for e in entries.values():
    by_gloss[e["_gloss"]].append(e["headword"])
by_topic = defaultdict(list)
for k, ts in topic_of.items():
    for t in ts:
        by_topic[t].append(k)
heads_lower = {e["headword"].lower(): e["headword"] for e in entries.values()}
for e in entries.values():
    refs = [h for h in by_gloss[e["_gloss"]] if h != e["headword"]]
    for t in topic_of.get(e["headword"].lower(), ()):
        refs += [heads_lower.get(w, w) for w in by_topic[t] if w != e["headword"].lower()]
    for en in curated_en.get(e["headword"].lower(), ()):     # other Scots words for the same English in the app
        for k, ens in curated_en.items():
            if en in ens and k != e["headword"].lower() and " " not in k:
                refs.append(heads_lower.get(k, k))
    seen, out = set(), []
    for r in refs:
        if r.lower() not in seen and r.lower() != e["headword"].lower():
            seen.add(r.lower()); out.append(r)
    e["cross_references"] = out[:10]
    e["definition"] = "; ".join(e.pop("_defs"))
    del e["_gloss"]

order = ["headword", "variants", "ipa", "phonetic", "pos", "register", "region", "etymology", "definition",
         "example_scots", "example_en", "cross_references"]
data = sorted(({k: e[k] for k in order} for e in entries.values()), key=lambda x: (x["headword"].lower().lstrip("'"), x["pos"]))
json.dump(data, open(OUT, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
print("entries:", len(data))
print("dropped:", dict(dropped))
print("with example:", sum(1 for d in data if d["example_scots"]), "| with cross-refs:", sum(1 for d in data if d["cross_references"]),
      "| with variants:", sum(1 for d in data if d["variants"]))
