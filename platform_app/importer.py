from __future__ import annotations

import hashlib
import json
import mimetypes
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}
MODULES = (
    ("hero", "Hero"),
    ("partners", "合作伙伴与背书"),
    ("reports", "报告样张"),
    ("loop", "经营闭环"),
    ("values", "经营价值"),
    ("services", "服务层级"),
    ("metrics", "增长与止损"),
    ("cta", "CTA"),
    ("footer", "页尾"),
)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


@dataclass
class Extracted:
    fields: list[dict] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)
    counts: dict[str, int] = field(default_factory=lambda: {"text": 0, "a11y": 0, "dom_images": 0, "canvas_images": 0})


class PageExtractor(HTMLParser):
    def __init__(self, page: Path, scenario: str, code_prefix: str):
        super().__init__(convert_charrefs=True)
        self.page = page
        self.scenario = scenario
        self.code_prefix = code_prefix
        self.result = Extracted()
        self.stack: list[tuple[str, str]] = []
        self.skip_depth = 0
        self.section_index = 0
        self.field_counters: dict[str, int] = {}
        self.asset_counters: dict[str, int] = {}

    def module_for(self, tag: str, attrs: dict[str, str | None]) -> str:
        parent = self.stack[-1][1] if self.stack else "hero"
        classes = set((attrs.get("class") or "").split())
        if tag == "header" or "hero" in classes or attrs.get("id") == "top":
            return "hero"
        if tag == "footer" or "export-button" in classes:
            return "footer"
        if tag == "section":
            self.section_index += 1
            if "clients" in classes:
                return "partners"
            if attrs.get("id") == "reports":
                return "reports"
            if attrs.get("id") == "loop":
                return "loop"
            if attrs.get("id") == "services":
                return "services"
            if "cta" in classes:
                return "cta"
            return {4: "values", 6: "metrics"}.get(self.section_index, parent)
        return parent

    def add_field(self, module: str, role: str, value: str, metadata: dict | None = None) -> None:
        self.field_counters[module] = self.field_counters.get(module, 0) + 1
        n = self.field_counters[module]
        module_number = next(i for i, (kind, _) in enumerate(MODULES, 1) if kind == module)
        self.result.fields.append({
            "code": f"P009.M{module_number:03d}.F{n:03d}.{self.code_prefix}",
            "module": module,
            "role": role,
            "value": value,
            "sort_order": n,
            "visible_scenarios": [self.scenario],
            "metadata": metadata or {},
        })

    def add_asset(self, module: str, source: str, role: str, title: str = "") -> None:
        if source.startswith(("http://", "https://", "data:")):
            return
        path = (self.page.parent / source).resolve()
        if not path.is_file():
            return
        self.asset_counters[module] = self.asset_counters.get(module, 0) + 1
        n = self.asset_counters[module]
        module_number = next(i for i, (kind, _) in enumerate(MODULES, 1) if kind == module)
        self.result.assets.append({
            "code": f"P009.M{module_number:03d}.A{n:03d}.{self.code_prefix}",
            "module": module,
            "role": role,
            "title": title or path.stem,
            "sort_order": n,
            "source_path": str(path),
            "filename": path.name,
            "sha256": digest(path),
            "bytes": path.stat().st_size,
            "media_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
            "visible_scenarios": [self.scenario],
        })

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        data = dict(attrs)
        module = self.module_for(tag, data)
        if tag in {"script", "style"}:
            self.skip_depth += 1
        self.stack.append((tag, module))
        for name in ("alt", "aria-label", "title"):
            if data.get(name):
                self.add_field(module, f"attribute:{name}", data[name] or "", {"tag": tag, "attribute": name})
                self.result.counts["a11y"] += 1
        if tag == "img" and data.get("src"):
            self.add_asset(module, data["src"] or "", "dom-image", data.get("alt") or "")
            self.result.counts["dom_images"] += 1
        if tag in VOID:
            self.stack.pop()

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.skip_depth:
            self.skip_depth -= 1
        for i in range(len(self.stack) - 1, -1, -1):
            if self.stack[i][0] == tag:
                del self.stack[i:]
                break

    def handle_data(self, data: str) -> None:
        if self.skip_depth or not data.strip():
            return
        module = self.stack[-1][1] if self.stack else "hero"
        tag = self.stack[-1][0] if self.stack else "body"
        self.add_field(module, tag, data.strip(), {"tag": tag})
        self.result.counts["text"] += 1


def extract_page(path: Path, scenario: str, code_prefix: str) -> Extracted:
    parser = PageExtractor(path, scenario, code_prefix)
    source = path.read_text(encoding="utf-8")
    parser.feed(source)
    for src, caption in re.findall(r"\{src:'([^']+)',cap:'([^']+)'", source):
        parser.add_asset("reports", src, "canvas-texture", caption)
        parser.result.counts["canvas_images"] += 1
    return parser.result


def p009_bundle(root: Path) -> dict:
    sales_path = root / "decks/tiansight-landing-v2/one-pager.html"
    corporate_path = root / "decks/tiansight-corporate/company-profile.html"
    sales = extract_page(sales_path, "P009.SCN.SALES", "SALES")
    corporate = extract_page(corporate_path, "P009.SCN.CORP", "CORP")
    sources = []
    for code, path, kind in (
        ("P009.SRC.SALES.HTML", sales_path, "html"),
        ("P009.SRC.CORP.HTML", corporate_path, "html"),
    ):
        sources.append({
            "code": code,
            "kind": kind,
            "title": path.name,
            "path": str(path.resolve()),
            "sha256": digest(path),
            "bytes": path.stat().st_size,
            "media_type": "text/html",
        })
    brand_version = "347cfbb"
    sources.append({
        "code": "P009.SRC.BRAND.API",
        "kind": "json-api",
        "title": "APUCH TIANSIGHT brand guide",
        "path": "https://apuch.art/api/brands/tiansight.json",
        "sha256": hashlib.sha256(f"apuch:tiansight:{brand_version}".encode()).hexdigest(),
        "bytes": 0,
        "media_type": "application/json",
        "metadata": {"brand_version": brand_version, "published": "2026-08-20", "checksum_scope": "API reference descriptor"},
    })
    all_fields = sales.fields + corporate.fields
    all_assets = sales.assets + corporate.assets
    for module_number, (kind, _) in enumerate(MODULES, 1):
        for number, item in enumerate((item for item in all_fields if item["module"] == kind), 1):
            item["code"] = f"P009.M{module_number:03d}.F{number:03d}"
        for number, item in enumerate((item for item in all_assets if item["module"] == kind), 1):
            item["code"] = f"P009.M{module_number:03d}.A{number:03d}"
    return {
        "project": {"code": "P009", "slug": "tiansight", "name": "TIANSIGHT 侍天", "description": "餐饮第二大脑"},
        "aliases": ["D09", "tiansight-corporate", "tiansight-landing-v2", "/decks/tiansight-corporate/", "/decks/tiansight-landing-v2/"],
        "brand": {"primary": "#EFE6D2", "accent": "#76551F", "secondary": "#8C3228", "surface": "#F4F0E7", "paper": "#FFFDF8", "ink": "#17130D", "muted": "#706758", "version": "347cfbb"},
        "modules": [{"kind": kind, "name": name, "sort_order": i} for i, (kind, name) in enumerate(MODULES, 1)],
        "scenarios": [
            {"code": "P009.SCN.SALES", "slug": "sales-landing", "name": "销售 Landing"},
            {"code": "P009.SCN.CORP", "slug": "corporate-profile", "name": "企业介绍"},
        ],
        "fields": all_fields,
        "assets": all_assets,
        "sources": sources,
        "acceptance": {"sales": sales.counts, "corporate": corporate.counts},
    }


if __name__ == "__main__":
    import sys

    bundle = p009_bundle(Path(sys.argv[1] if len(sys.argv) > 1 else ".").resolve())
    print(json.dumps(bundle["acceptance"], ensure_ascii=False, indent=2))
