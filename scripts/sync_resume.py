#!/usr/bin/env python3
"""Generate resume.html from the Resume 2026 Google Doc Markdown export.

Privacy: strips street address, phone, and full mailing-address lines.
Keeps name, title, "Scotts Valley, CA" (at most), email, LinkedIn/GitHub.
"""

from __future__ import annotations

import argparse
import html
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MD = ROOT / "data" / "resume.md"
DEFAULT_OUT = ROOT / "resume.html"

STREET_RE = re.compile(r"1360\s+Whispering\s+Pines\s+Drive", re.I)
PHONE_RE = re.compile(r"\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}")
ZIP_LINE_RE = re.compile(r"^Scotts Valley,\s*CA\s*\d{5}\s*$", re.I)
MD_LINK_RE = re.compile(r"\[([^\]]+)\]\(([^)]+)\)")
ESC_RE = re.compile(r"\\([\\`*_{}\[\]()#+\-.!>$])")


def unescape_md(text: str) -> str:
    return ESC_RE.sub(r"\1", text)


def strip_md_bold_italic(text: str) -> str:
    text = unescape_md(text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    return text.strip()


def md_inline_to_html(text: str) -> str:
    """Convert a single line of markdown inline markup to HTML."""
    text = unescape_md(text)

    parts: list[str] = []
    last = 0
    for m in MD_LINK_RE.finditer(text):
        parts.append(html.escape(text[last : m.start()]))
        label = html.escape(m.group(1))
        href = html.escape(m.group(2), quote=True)
        parts.append(f'<a href="{href}">{label}</a>')
        last = m.end()
    parts.append(html.escape(text[last:]))
    out = "".join(parts)
    out = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", out)
    out = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", out)
    return out


def is_private_contact_line(line: str) -> bool:
    raw = strip_md_bold_italic(line).strip().rstrip("\\").strip()
    if not raw:
        return False
    if STREET_RE.search(raw):
        return True
    if PHONE_RE.search(raw):
        return True
    if ZIP_LINE_RE.match(raw):
        return True
    # Bare zip / street fragments
    if re.match(r"^\d{5}(-\d{4})?$", raw):
        return True
    return False


def city_only(line: str) -> str | None:
    raw = strip_md_bold_italic(line).strip()
    if ZIP_LINE_RE.match(raw) or re.match(r"^Scotts Valley,\s*CA", raw, re.I):
        return "Scotts Valley, CA"
    return None


def parse_resume(md: str) -> dict:
    lines = md.replace("\r\n", "\n").split("\n")

    name = "Andy Perlitch"
    title = "Full Stack Software Engineer"
    summary = ""
    jobs: list[dict] = []
    education: dict = {"school": "", "degree": "", "dates": "", "courses": []}
    links: list[tuple[str, str]] = []
    contact_bits: list[str] = []  # location, email, linkedin (header)

    # Identify top-level sections by # headings (not ##)
    section = "header"
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        if re.match(r"^#\s+", stripped) and not stripped.startswith("##"):
            heading = strip_md_bold_italic(re.sub(r"^#\s+", "", stripped)).lower()
            if heading == "andy perlitch":
                name = "Andy Perlitch"
                section = "header"
            elif "summary" in heading:
                section = "summary"
            elif "experience" in heading:
                section = "experience"
            elif "education" in heading:
                section = "education"
            elif "link" in heading:
                section = "links"
            else:
                section = "other"
            i += 1
            continue

        if section == "header":
            if stripped.startswith("## ") and not stripped.startswith("###"):
                title = strip_md_bold_italic(stripped[3:])
            elif stripped:
                if is_private_contact_line(stripped):
                    city = city_only(stripped)
                    if city and city not in contact_bits:
                        contact_bits.append(city)
                else:
                    # Keep email / linkedin markdown links; skip empty
                    plain = strip_md_bold_italic(MD_LINK_RE.sub(r"\1", stripped))
                    if STREET_RE.search(plain) or PHONE_RE.search(plain):
                        pass
                    elif city_only(stripped):
                        c = city_only(stripped)
                        if c and c not in contact_bits:
                            contact_bits.append(c)
                    elif stripped:
                        # Prefer city-only if zip line already handled
                        contact_bits.append(stripped.rstrip("\\").strip())
            i += 1
            continue

        if section == "summary":
            if stripped:
                summary = (summary + " " + strip_md_bold_italic(stripped)).strip()
            i += 1
            continue

        if section == "experience":
            if stripped.startswith("## "):
                job = {
                    "company_role": strip_md_bold_italic(stripped[3:]),
                    "url": None,
                    "dates": "",
                    "bullets": [],
                    "tech": "",
                }
                i += 1
                # Consume job body until next ## or # section
                while i < len(lines):
                    L = lines[i].strip()
                    if L.startswith("## ") or (
                        re.match(r"^#\s+", L) and not L.startswith("##")
                    ):
                        break
                    if not L:
                        i += 1
                        continue
                    link_m = MD_LINK_RE.search(L)
                    if link_m and (
                        L.startswith("[http") or "http" in link_m.group(2)
                    ) and not job["url"]:
                        job["url"] = unescape_md(link_m.group(2))
                        i += 1
                        continue
                    if re.match(
                        r"^(January|February|March|April|May|June|July|August|"
                        r"September|October|November|December|Jan|Feb|Mar|Apr|"
                        r"May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
                        unescape_md(L),
                        re.I,
                    ):
                        job["dates"] = unescape_md(L)
                        i += 1
                        continue
                    if L.startswith("* ") or L.startswith("- "):
                        job["bullets"].append(
                            unescape_md(L[2:].rstrip("\\").strip())
                        )
                        i += 1
                        continue
                    if L.lower() == "technologies":
                        i += 1
                        # next non-empty line is tech list
                        while i < len(lines) and not lines[i].strip():
                            i += 1
                        if i < len(lines):
                            nxt = lines[i].strip()
                            if not nxt.startswith("#") and not nxt.startswith("*"):
                                job["tech"] = unescape_md(nxt)
                                i += 1
                        continue
                    i += 1
                jobs.append(job)
                continue
            i += 1
            continue

        if section == "education":
            if stripped.startswith("## "):
                body = strip_md_bold_italic(stripped[3:])
                if not education["school"]:
                    education["school"] = body
                elif not education["degree"]:
                    education["degree"] = body
            elif re.match(
                r"^(January|February|March|April|May|June|July|August|"
                r"September|October|November|December|Jan|Feb|Mar|Apr|"
                r"May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\b",
                unescape_md(stripped),
                re.I,
            ):
                education["dates"] = unescape_md(stripped)
            elif stripped and not stripped.startswith("#"):
                plain = strip_md_bold_italic(stripped)
                if plain.lower().rstrip(":").endswith("courses") or plain.lower().startswith("computer science courses"):
                    pass
                elif education["school"]:
                    education["courses"].append(plain)
            i += 1
            continue

        if section == "links":
            m = MD_LINK_RE.search(stripped)
            if m:
                href = unescape_md(m.group(2))
                label = unescape_md(m.group(1))
                # Prefer clean labels
                if "linkedin" in href.lower():
                    label = "LinkedIn"
                elif "github" in href.lower():
                    label = "GitHub"
                elif "giggable" in href.lower():
                    label = "Giggable tech blog"
                links.append((label, href))
            i += 1
            continue

        i += 1

    # Normalize header contact: ensure city present once; keep markdown links as-is
    location = None
    email_html = None
    other_links: list[str] = []
    for bit in contact_bits:
        if bit == "Scotts Valley, CA" or re.match(r"^Scotts Valley,\s*CA$", bit, re.I):
            location = "Scotts Valley, CA"
        elif "mailto:" in bit or "@" in bit:
            email_html = md_inline_to_html(bit)
        elif "linkedin" in bit.lower():
            other_links.append(md_inline_to_html(bit))
        elif not STREET_RE.search(bit) and not PHONE_RE.search(bit):
            # skip zip-only leftovers
            if not re.search(r"\d{5}", bit):
                other_links.append(md_inline_to_html(bit))

    return {
        "name": name,
        "title": title,
        "location": location,
        "email_html": email_html,
        "header_links": other_links,
        "summary": summary,
        "jobs": jobs,
        "education": education,
        "links": links,
    }


def render(data: dict) -> str:
    contact_parts = []
    if data["location"]:
        contact_parts.append(html.escape(data["location"]))
    if data["email_html"]:
        contact_parts.append(data["email_html"])
    contact_parts.extend(data["header_links"])
    contact = " · ".join(contact_parts)

    job_html = []
    for job in data["jobs"]:
        company_role = html.escape(job["company_role"])
        # Split "Company, Place - Role" style for nicer display when possible
        title_line = f"<b>{company_role}</b>"
        meta = []
        if job["dates"]:
            meta.append(html.escape(job["dates"]))
        if job["url"]:
            u = html.escape(job["url"], quote=True)
            host = re.sub(r"^https?://(www\.)?", "", job["url"]).rstrip("/")
            meta.append(f'<a href="{u}">{html.escape(host)}</a>')
        meta_html = "<br><small>" + " · ".join(meta) + "</small>" if meta else ""
        bullets = "".join(
            f"<li>{html.escape(b)}</li>" for b in job["bullets"]
        )
        bullets_html = f"<ul>{bullets}</ul>" if bullets else ""
        tech_html = (
            f'<p class="tech"><small>{html.escape(job["tech"])}</small></p>'
            if job["tech"]
            else ""
        )
        job_html.append(
            f'<div class="post">{title_line}{meta_html}{bullets_html}{tech_html}</div>'
        )

    edu = data["education"]
    edu_bits = []
    if edu["school"]:
        edu_bits.append(f"<b>{html.escape(edu['school'])}</b>")
    if edu["degree"]:
        edu_bits.append(html.escape(edu["degree"]))
    edu_head = "<br>".join(edu_bits) if edu_bits else ""
    edu_dates = (
        f"<br><small>{html.escape(edu['dates'])}</small>" if edu["dates"] else ""
    )
    courses = ""
    if edu["courses"]:
        items = "".join(f"<li>{html.escape(c)}</li>" for c in edu["courses"])
        courses = f"<p><small>Computer Science courses</small></p><ul>{items}</ul>"
    edu_html = f'<div class="post">{edu_head}{edu_dates}{courses}</div>'

    link_items = "".join(
        f'<li><a href="{html.escape(h, quote=True)}">{html.escape(lab)}</a></li>'
        for lab, h in data["links"]
    )
    links_html = f"<ul>{link_items}</ul>" if link_items else ""

    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Resume · Andy Perlitch</title>
<link rel="stylesheet" href="style.css">
<script src="theme.js"></script>
</head>
<body>
<main>
<a class="back" href="index.html">← Home</a>
<div class="resume-actions">
</div>
<h1 style="margin-top:24px">{html.escape(data['name'])}</h1>
<p class="sub">{html.escape(data['title'])}</p>
<p class="contact">{contact}</p>

<h2>Summary</h2>
<p>{html.escape(data['summary'])}</p>

<h2>Experience</h2>
{"".join(job_html)}

<h2>Education</h2>
{edu_html}

<h2>Links</h2>
{links_html}
</main>
</body>
</html>
"""


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "markdown",
        nargs="?",
        default=str(DEFAULT_MD),
        help=f"Path to Markdown export (default: {DEFAULT_MD})",
    )
    ap.add_argument(
        "-o",
        "--output",
        default=str(DEFAULT_OUT),
        help=f"Output HTML path (default: {DEFAULT_OUT})",
    )
    args = ap.parse_args()
    md_path = Path(args.markdown)
    out_path = Path(args.output)
    data = parse_resume(md_path.read_text(encoding="utf-8"))
    html_out = render(data)
    out_path.write_text(html_out, encoding="utf-8")
    print(f"Wrote {out_path} from {md_path}")
    print(f"  jobs={len(data['jobs'])} links={len(data['links'])} location={data['location']!r}")


if __name__ == "__main__":
    main()
