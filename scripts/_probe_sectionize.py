import json, re

SRC = "/mnt/c/2OPMD/2ndOpinionMD-MVP/data/NormanEricRoberts_decrypted_truncated.pages.json"
d = json.load(open(SRC))

# Kaiser boilerplate that appears at the top of many pages (before the real header).
CHROME = re.compile(
    r"\s*Release of Medical Information[^\n]{10,200}?MRN[:\s][^\n]{3,40}?DOB[:\s][^\n]{3,30}",
    re.I,
)
# Encounter header: MM/DD/YYYY - <visit type in department> [(continued)]<next section name>
ENC = re.compile(
    r"^\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*([A-Za-z][^(]{2,110}?)\s*(\(continued\))"
    r"|^\s*(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*([A-Za-z][^(]{2,110})$",
    re.I | re.M,
)
# Summary section like: "Patient (continued)Problem List (continued)" or "Patient (continued)Implants (continued)"
SUM = re.compile(
    r"^\s*Patient\s*\(continued\)\s*([A-Z][A-Za-z &/\-]{2,40}?)\s*\(continued\)",
    re.I,
)

# Fallback: encounter header anywhere in the first 400 chars
ENC_ANYWHERE = re.compile(
    r"(\d{1,2}/\d{1,2}/\d{2,4})\s*-\s*([A-Z][^(]{3,110}?)\s*\(continued\)",
    re.I,
)


def classify(text):
    t = text.strip()
    t_clean = CHROME.sub("", t, count=2).lstrip()
    # 1) Encounter
    m = ENC.search(t_clean[:400])
    if m:
        date = m.group(1) or m.group(4)
        vt = (m.group(2) or m.group(5)).strip()
        is_cont = bool(m.group(3))
        return ("encounter", date, vt, is_cont)
    # 2) Summary
    m = SUM.match(t_clean[:300])
    if m:
        return ("summary", None, m.group(1).strip(), True)
    # 3) Encounter anywhere (last-ditch)
    m = ENC_ANYWHERE.search(t_clean[:400])
    if m:
        return ("encounter", m.group(1), m.group(2).strip(), True)
    return ("other", None, None, False)


counts = {"encounter": 0, "summary": 0, "other": 0}
cont_counts = {"encounter": 0}
samples = {"other": [], "encounter": []}
for p in d["pages"]:
    t = p.get("text") or ""
    kind, date, name, is_cont = classify(t)
    counts[kind] += 1
    if kind == "encounter" and is_cont:
        cont_counts["encounter"] += 1
    if kind == "encounter" and len(samples["encounter"]) < 8:
        samples["encounter"].append((p["page_num"], date, name[:40], is_cont))
    if kind == "other" and len(samples["other"]) < 10:
        samples["other"].append((p["page_num"], (t.strip()[:200]).replace("\n", " ")))

print("counts:", counts, "of which encounter continuations:", cont_counts)
print("encounter samples:")
for s in samples["encounter"]:
    print(" ", s)
print("other samples:")
for s in samples["other"]:
    print(" ", s[0], "|", s[1][:140])
