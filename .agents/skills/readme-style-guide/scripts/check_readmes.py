#!/usr/bin/env python3
"""Offline, read-only checks for explicitly selected bilingual README pairs.

Supports common ATX/Setext headings, fenced code, single-line inline/reference
links, Markdown images, and ordinary GitHub-style heading slugs. This is not a
complete CommonMark/GFM parser. HTML links/images/custom IDs, multiline link
definitions, complex nested blocks, and unusual Unicode slug behavior require
manual checking. Fenced/indented code, inline code, and HTML comments are ignored.
Linked Markdown is read only when needed to check an explicit fragment; its
links are never followed. Other local targets receive existence/case checks only.
Each selected directory is a permitted document root. Targets may not leave it;
symbolic links and Windows reparse points are rejected instead of followed.
No required content sections, product behavior, facts, or translations are judged.
"""

from __future__ import annotations

import argparse
import html
import os
import re
import stat
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit


NAVIGATION = {
    "README.md": re.compile(r"\[中文\]\(README\.zh-CN\.md\) / (?:ENG|\*\*ENG\*\*)"),
    "README.zh-CN.md": re.compile(r"(?:中文|\*\*中文\*\*) / \[ENG\]\(README\.md\)"),
}
FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
ATX = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)(.*)$")
SETEXT = re.compile(r"^ {0,3}(=+|-+)[ \t]*$")
REFERENCE = re.compile(r"^ {0,3}\[([^\]]+)\]:[ \t]*(.*)$")
ESCAPE = re.compile(r"\\([!\"#$%&'()*+,\-./:;<=>?@\[\]\\^_`{|}~])")


@dataclass
class Issue:
    path: Path
    line: int
    code: str
    message: str


@dataclass
class Link:
    line: int
    target: str
    image: bool = False
    alt: str = ""


@dataclass
class Document:
    path: Path
    lines: list[str]
    headings: list[tuple[int, int, str]]
    anchors: set[str]
    links: list[Link]
    issues: list[Issue]


def unescape(value: str) -> str:
    return html.unescape(ESCAPE.sub(r"\1", value))


def reference_id(value: str) -> str:
    return " ".join(unescape(value).split()).casefold()


def mask_inline_code(line: str) -> str:
    chars = list(line)
    position = 0
    while position < len(line):
        if line[position] == "\\":
            position += 2
            continue
        if line[position] != "`":
            position += 1
            continue
        end = position
        while end < len(line) and line[end] == "`":
            end += 1
        marker = line[position:end]
        closing = end
        while True:
            closing = line.find(marker, closing)
            if closing < 0:
                break
            after = closing + len(marker)
            if (closing == 0 or line[closing - 1] != "`") and (
                after == len(line) or line[after] != "`"
            ):
                chars[position:after] = " " * (after - position)
                position = after
                break
            closing = after
        else:  # pragma: no cover
            pass
        if closing < 0:
            position = end
    return "".join(chars)


def destination(text: str, opening: int) -> tuple[str, int] | None:
    """Read a destination with balanced parentheses and an optional title."""
    position = opening + 1
    while position < len(text) and text[position].isspace():
        position += 1
    start = position
    if position < len(text) and text[position] == "<":
        position += 1
        start = position
        while position < len(text) and text[position] != ">":
            position += 2 if text[position] == "\\" else 1
        if position >= len(text):
            return None
        target = text[start:position]
        position += 1
    else:
        depth = 0
        while position < len(text):
            char = text[position]
            if char == "\\":
                position += 2
                continue
            if char == "(":
                depth += 1
            elif char == ")":
                if depth == 0:
                    break
                depth -= 1
            elif char.isspace() and depth == 0:
                break
            position += 1
        if depth:
            return None
        target = text[start:position]
    had_space = position < len(text) and text[position].isspace()
    while position < len(text) and text[position].isspace():
        position += 1
    if had_space and position < len(text) and text[position] in "\"'(":
        closer = ")" if text[position] == "(" else text[position]
        position += 1
        while position < len(text) and text[position] != closer:
            position += 2 if text[position] == "\\" else 1
        if position >= len(text):
            return None
        position += 1
        while position < len(text) and text[position].isspace():
            position += 1
    if position < len(text) and text[position] == ")":
        return unescape(target), position + 1
    return None


def bracket_end(text: str, start: int) -> int | None:
    depth = 1
    position = start + 1
    while position < len(text):
        if text[position] == "\\":
            position += 2
            continue
        if text[position] == "[":
            depth += 1
        elif text[position] == "]":
            depth -= 1
            if depth == 0:
                return position
        position += 1
    return None


def visible_text(value: str) -> str:
    value = re.sub(r"!?\[([^\]]*)\]\([^)]*\)", r"\1", value)
    value = re.sub(r"!?\[([^\]]*)\]\[[^\]]*\]", r"\1", value)
    value = re.sub(r"<[^>]*>", "", value)
    value = re.sub(r"`+([^`]+)`+", r"\1", value)
    for _ in range(3):
        value = re.sub(r"(\*\*|__|\*|_|~~)(?=\S)(.+?)(?<=\S)\1", r"\2", value)
    return unescape(value).strip()


def heading_slug(title: str) -> str:
    title = visible_text(title).lower()
    return "".join(
        "-" if char.isspace() else char
        for char in title
        if char.isspace() or char in "-_" or unicodedata.category(char)[0] in "LNM"
    )


def parse_document(path: Path, text: str) -> Document:
    lines = text.splitlines()
    without_comments = re.sub(
        r"<!--[\s\S]*?-->", lambda match: "\n" * match.group().count("\n"), text
    ).splitlines()
    visible = list(without_comments)
    issues: list[Issue] = []
    opened: tuple[str, int, int] | None = None
    for index, line in enumerate(without_comments):
        match = FENCE.match(line)
        if opened:
            visible[index] = ""
            if match and match[1][0] == opened[0] and len(match[1]) >= opened[1] and not match[2].strip():
                opened = None
        elif match and not (match[1][0] == "`" and "`" in match[2]):
            opened = (match[1][0], len(match[1]), index + 1)
            visible[index] = ""
        elif line.startswith("    ") or line.startswith("\t"):
            visible[index] = ""
    if opened:
        issues.append(Issue(path, opened[2], "fence", "Unclosed fenced code block."))

    references: dict[str, str] = {}
    for index, line in enumerate(visible):
        match = REFERENCE.match(line)
        if match:
            parsed = destination("(" + match[2] + ")", 0)
            if parsed:
                references.setdefault(reference_id(match[1]), parsed[0])
            visible[index] = ""

    headings: list[tuple[int, int, str]] = []
    index = 0
    while index < len(visible):
        line = visible[index]
        atx = ATX.match(line)
        if atx:
            title = re.sub(r"[ \t]+#+[ \t]*$", "", atx[2]).strip()
            headings.append((index + 1, len(atx[1]), title))
        elif line.strip() and index + 1 < len(visible) and SETEXT.match(visible[index + 1]):
            if not re.match(r"^ {0,3}(?:[-+*>]|\d+[.)])\s", line):
                headings.append((index + 1, 1 if visible[index + 1].lstrip().startswith("=") else 2, line.strip()))
                index += 1
        index += 1
    anchors: set[str] = set()
    for _, _, title in headings:
        base = heading_slug(title)
        slug = base
        number = 0
        while slug in anchors:
            number += 1
            slug = f"{base}-{number}"
        anchors.add(slug)

    links: list[Link] = []

    def scan(raw: str, line_number: int) -> None:
        masked = mask_inline_code(raw)
        position = 0
        while position < len(masked):
            if masked[position] == "\\":
                position += 2
                continue
            image = masked.startswith("![", position)
            opening = position + 1 if image else position
            if masked[opening:opening + 1] != "[":
                position += 1
                continue
            closing = bracket_end(masked, opening)
            if closing is None:
                position += 1
                continue
            label = raw[opening + 1:closing]
            after = closing + 1
            parsed = destination(raw, after) if raw[after:after + 1] == "(" else None
            target: str | None = None
            if parsed:
                target, after = parsed
            elif masked[after:after + 1] == "[":
                reference_end = bracket_end(masked, after)
                if reference_end is not None:
                    identifier = reference_id(raw[after + 1:reference_end] or label)
                    target = references.get(identifier)
                    after = reference_end + 1
                    if target is None:
                        issues.append(Issue(path, line_number, "reference", "Undefined explicit link reference."))
            elif reference_id(label) in references:
                target = references[reference_id(label)]
            if target is not None:
                links.append(Link(line_number, target, image, label))
                if "![" in label:
                    scan(label, line_number)
                position = after
            else:
                position = closing + 1

    for index, line in enumerate(visible):
        scan(line, index + 1)
    return Document(path, lines, headings, anchors, links, issues)


def boundary_error(path: Path, root: Path) -> str | None:
    """Reject lexical escape and link components before any traversal/read."""
    try:
        relative = path.relative_to(root)
    except ValueError:
        return "path-boundary"
    if ".." in relative.parts:
        return "path-boundary"
    cursor = root
    for part in (None, *relative.parts):
        if part is not None:
            cursor = cursor / part
        try:
            entry = cursor.lstat()
        except OSError:
            return "path-missing"
        if stat.S_ISLNK(entry.st_mode) or getattr(entry, "st_file_attributes", 0) & 0x400:
            return "path-boundary"
    return None


def local_path(directory: Path, target: str, root: Path) -> tuple[Path | None, str | None]:
    """Check case within root; never enumerate an escaped or linked directory."""
    cursor = directory
    wrong_case = False
    for part in target.split("/"):
        if part in ("", "."):
            continue
        error = boundary_error(cursor, root)
        if error:
            return None, error
        try:
            if not stat.S_ISDIR(cursor.lstat().st_mode):
                return None, "path-missing"
        except OSError:
            return None, "path-missing"
        if part == "..":
            if cursor == root:
                return None, "path-boundary"
            cursor = cursor.parent
            continue
        try:
            names = {entry.name for entry in cursor.iterdir()}
        except OSError:
            return None, "path-missing"
        if part in names:
            cursor = cursor / part
        else:
            alternatives = sorted(name for name in names if name.casefold() == part.casefold())
            if not alternatives:
                return None, "path-missing"
            wrong_case = True
            cursor = cursor / alternatives[0]
        error = boundary_error(cursor, root)
        if error:
            return None, error
    error = boundary_error(cursor, root)
    if error:
        return None, error
    return cursor, "path-case" if wrong_case else None


def label(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.name


def check_pair(root: Path) -> tuple[list[Issue], set[tuple[str, int, str]], set[tuple[str, int, str]]]:
    issues: list[Issue] = []
    external: set[tuple[str, int, str]] = set()
    skipped: set[tuple[str, int, str]] = set()
    cache: dict[Path, Document | None] = {}

    def read(path: Path, origin: Path, line: int) -> Document | None:
        error = boundary_error(path, root)
        if error:
            issues.append(Issue(origin, line, error, "Markdown target is outside the permitted root, linked, or unavailable."))
            return None
        if path not in cache:
            try:
                text = path.read_bytes().decode("utf-8-sig", errors="strict")
                cache[path] = parse_document(path, text)
            except UnicodeDecodeError:
                issues.append(Issue(origin, line, "utf8", f"Target is not UTF-8: {label(path, root)!r}."))
                cache[path] = None
            except OSError:
                issues.append(Issue(origin, line, "read", f"Cannot read Markdown target: {label(path, root)!r}."))
                cache[path] = None
        return cache[path]

    for filename, navigation in NAVIGATION.items():
        requested = root / filename
        path, error = local_path(root, filename, root)
        if error:
            issues.append(Issue(requested, 1, error, "README target is missing, mis-cased, linked, or outside the permitted root."))
        if path is None:
            continue
        doc = read(path, path, 1)
        if doc is None:
            continue
        if not doc.lines or not navigation.fullmatch(doc.lines[0].rstrip()):
            issues.append(Issue(path, 1, "navigation", "First line must contain the specified Chinese / ENG relative navigation."))
        issues.extend(doc.issues)
        if sum(level == 1 for _, level, _ in doc.headings) != 1:
            issues.append(Issue(path, 1, "h1", "Expected exactly one H1 heading."))
        previous = 0
        for line, level, _ in doc.headings:
            if level > previous + 1:
                issues.append(Issue(path, line, "heading-level", f"Heading jumps from level {previous} to {level}."))
            previous = level
        for link in doc.links:
            if link.image and not visible_text(link.alt):
                issues.append(Issue(path, link.line, "image-alt", "Markdown images require nonempty alternative text."))
            try:
                parts = urlsplit(link.target)
                if parts.scheme or parts.netloc or link.target.startswith("//"):
                    external.add((label(path, root), link.line, link.target))
                    continue
                target_name = unquote(parts.path, encoding="utf-8", errors="strict")
                fragment = unquote(parts.fragment, encoding="utf-8", errors="strict")
            except (ValueError, UnicodeError):
                issues.append(Issue(path, link.line, "target", "Invalid URI or percent-encoded UTF-8 destination."))
                continue
            if target_name.startswith("/"):
                skipped.add((label(path, root), link.line, "Root-relative target: " + link.target))
                continue
            if "\\" in target_name or "\x00" in target_name:
                issues.append(Issue(path, link.line, "target", "Local destinations must use forward slashes and contain no NUL."))
                continue
            target, error = local_path(path.parent, target_name, root) if target_name else (path, None)
            if error:
                issues.append(Issue(path, link.line, error, f"Local target: {link.target!r}."))
            if target is None or not fragment:
                continue
            if target.suffix.lower() not in {".md", ".markdown"}:
                skipped.add((label(path, root), link.line, "Fragment on a non-Markdown target: " + link.target))
                continue
            target_doc = read(target, path, link.line)
            if target_doc is not None and fragment not in target_doc.anchors:
                issues.append(Issue(path, link.line, "anchor", f"Heading anchor not found: {link.target!r}."))
    return issues, external, skipped


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check mechanical Markdown rules in explicit bilingual README directories, offline.",
        epilog="No directory recursion, code execution, input writes, or semantic/translation validation. "
        "UTF-8 BOM and CRLF are accepted. Active navigation text may be bold. "
        "Local targets must stay within each selected root; symbolic/reparse links are rejected. "
        "External URLs are listed only. HTML/custom anchors and complex Markdown require manual checking.",
    )
    parser.add_argument("directories", nargs="+", type=Path, help="Directories containing the two README files")
    args = parser.parse_args(argv)
    failed = False
    for index, supplied in enumerate(args.directories, 1):
        root = Path(os.path.abspath(supplied))
        print(f"Directory {index}: {root.name}")
        error = boundary_error(root, root)
        if error == "path-boundary":
            print("ERROR [path-boundary] The explicit root is a symbolic/reparse link.")
            failed = True
            continue
        if not root.is_dir():
            print("ERROR [directory] Explicit directory does not exist.")
            failed = True
            continue
        issues, external, skipped = check_pair(root)
        for issue in sorted(issues, key=lambda item: (label(item.path, root), item.line, item.code, item.message)):
            print(f"ERROR {label(issue.path, root)}:{issue.line} [{issue.code}] {issue.message}")
        for source, line, target in sorted(external):
            print(f"EXTERNAL {source}:{line} {target!r} (not fetched)")
        for source, line, reason in sorted(skipped):
            print(f"UNCHECKED {source}:{line} {reason!r}")
        failed |= bool(issues)
        print(f"Mechanical checks: {'FAIL' if issues else 'PASS'}; {len(issues)} error(s), "
              f"{len(external)} external URL(s), {len(skipped)} unchecked target(s).")
    print("Scope: common Markdown only; no facts, translations, product behavior, or remote targets were validated.")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
