from __future__ import annotations

import base64
import hashlib
import html
import json
import re
from pathlib import Path


def esc(value) -> str:
    return html.escape(str(value), quote=True)


def field_node(field: dict) -> str:
    value = esc(field["value"])
    role = field["role"]
    code = esc(field["code"])
    if role == "h1":
        return f'<h1 data-field-code="{code}">{value}</h1>'
    if role in {"h2", "h3"}:
        return f'<{role} data-field-code="{code}">{value}</{role}>'
    if role in {"p", "li", "cite", "strong", "b", "figcaption"}:
        tag = "p" if role == "li" else role
        return f'<{tag} data-field-code="{code}">{value}</{tag}>'
    if role.startswith("attribute:"):
        return f'<span class="a11y-copy" data-field-code="{code}">{value}</span>'
    return f'<span class="copy" data-field-code="{code}">{value}</span>'


def asset_node(asset: dict, media_prefix: str, eager: bool = False) -> str:
    url = f"{media_prefix}/{asset['object_path']}"
    loading = "eager"
    return (
        f'<figure class="asset asset--{esc(asset["role"])}" data-asset-code="{esc(asset["code"])}">'
        f'<img src="{esc(url)}" alt="{esc(asset["title"])}" loading="{loading}">'
        f'<figcaption>{esc(asset["title"])}</figcaption></figure>'
    )


def module_html(module: dict, media_prefix: str) -> str:
    fields = "".join(field_node(field) for field in module["fields"])
    assets = module["assets"]
    if module["kind"] in {"hero", "reports"} and assets:
        visual = "".join(asset_node(asset, media_prefix, True) for asset in assets)
        return f'<section class="module module--{module["kind"]}" data-module-code="{module["code"]}"><div class="module-copy">{fields}</div><div class="shelf"><div class="shelf-track">{visual}</div></div></section>'
    if module["kind"] == "partners" and assets:
        visual = "".join(asset_node(asset, media_prefix) for asset in assets)
        return f'<section class="module module--partners" data-module-code="{module["code"]}"><div class="module-copy">{fields}</div><div class="partner-grid">{visual}</div></section>'
    if module["kind"] == "cta" and assets:
        visual = "".join(asset_node(asset, media_prefix) for asset in assets)
        return f'<section class="module module--cta" data-module-code="{module["code"]}"><div class="module-copy">{fields}</div><div class="cta-media">{visual}</div></section>'
    visual = "".join(asset_node(asset, media_prefix) for asset in assets)
    return f'<section class="module module--{module["kind"]}" data-module-code="{module["code"]}"><div class="module-copy flow-copy">{fields}</div>{visual}</section>'


def brand_css(snapshot: dict) -> str:
    brand = snapshot["project"].get("metadata", {}).get("brand", {})
    return ";".join(f"--{key}:{value}" for key, value in brand.items() if str(value).startswith("#"))


BASE_CSS = r"""
*{box-sizing:border-box}html{scroll-behavior:smooth;background:var(--surface,#F4F0E7);color:var(--ink,#17130D)}body{margin:0;font-family:"Songti SC","Noto Serif SC",Georgia,serif;background:var(--surface,#F4F0E7)}img{display:block;max-width:100%}.landing{overflow:hidden}.project-nav{width:min(1120px,calc(100% - 48px));height:84px;margin:auto;display:flex;align-items:center;gap:28px;border-bottom:1px solid var(--line,rgba(23,19,13,.18));font-family:Arial,sans-serif}.project-nav a{color:inherit;text-decoration:none}.project-nav .wordmark{font-weight:800;letter-spacing:.18em;margin-right:auto}.project-nav .nav-links{display:flex;gap:20px;font-size:12px}.project-nav .meta{color:var(--muted,#706758);font-size:12px;letter-spacing:.08em}.module{width:min(1120px,calc(100% - 48px));margin:auto;padding:104px 0;border-bottom:1px solid var(--line,rgba(23,19,13,.18))}.module-copy{max-width:780px;display:flex;flex-wrap:wrap;gap:15px 22px;align-items:baseline}.module-copy h1,.module-copy h2,.module-copy h3,.module-copy p{flex-basis:100%;margin:0}.module-copy h1{font-size:clamp(54px,8vw,112px);line-height:1.02;font-weight:500;letter-spacing:-.045em;text-wrap:balance}.module-copy h2{font-size:clamp(38px,5vw,66px);line-height:1.14;font-weight:500;letter-spacing:-.03em;text-wrap:balance}.module-copy h3{font-size:24px;line-height:1.35}.module-copy p{max-width:760px;color:var(--muted,#706758);font-size:18px;line-height:1.9}.copy{font-size:16px;line-height:1.65}.a11y-copy{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.module--hero{padding-top:76px}.module--hero .module-copy{max-width:none;margin-bottom:70px}.shelf{position:relative;margin-top:64px;padding:64px 5% 52px;perspective:1500px;background:rgba(239,230,210,.34);border:1px solid rgba(118,85,31,.2)}.shelf:after{content:"";position:absolute;left:4%;right:4%;bottom:34px;height:12px;background:#CDBD9E;box-shadow:0 24px 36px rgba(23,19,13,.2)}.shelf-track{display:flex;align-items:flex-end;justify-content:center;gap:0;transform-style:preserve-3d;min-height:520px}.shelf .asset{width:min(34%,360px);margin:0 -5%;padding:8px 8px 34px;background:var(--paper,#FFFDF8);border:1px solid rgba(23,19,13,.18);box-shadow:0 28px 48px rgba(23,19,13,.16);transform:rotateY(8deg) translateZ(0)}.shelf .asset:nth-child(even){transform:translateY(-28px) translateZ(42px)}.shelf .asset:nth-child(3n){transform:rotateY(-8deg) translateZ(4px)}.shelf .asset img{width:100%;aspect-ratio:4/5;object-fit:cover;object-position:top}.shelf .asset figcaption{padding:14px 10px 0;color:var(--accent,#76551F);font:700 12px/1.4 Arial,sans-serif}.partner-grid{display:grid;grid-template-columns:repeat(4,1fr);margin-top:60px;border-top:1px solid var(--line);border-left:1px solid var(--line)}.partner-grid .asset{min-height:190px;margin:0;padding:28px;border-right:1px solid var(--line);border-bottom:1px solid var(--line);display:flex;align-items:center;justify-content:center}.partner-grid img{max-height:110px;object-fit:contain}.partner-grid figcaption{position:absolute;width:1px;height:1px;overflow:hidden}.flow-copy{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));max-width:none;gap:0;border-top:1px solid var(--accent,#76551F)}.flow-copy>*{min-height:72px;padding:18px 22px;border-bottom:1px solid var(--line);border-right:1px solid var(--line)}.flow-copy h2{grid-column:1/-1;padding:34px 0;min-height:0;border-right:0}.flow-copy p{font-size:16px}.module--cta{display:grid;grid-template-columns:1fr 180px;gap:60px;background:var(--primary,#EFE6D2);border:1px solid var(--accent,#76551F);padding:64px;margin-top:90px;margin-bottom:100px}.cta-media .asset{margin:0}.cta-media figcaption{text-align:center;margin-top:10px;font:12px Arial,sans-serif}.cta-media img{aspect-ratio:1;object-fit:contain;background:white;padding:6px}@media(max-width:760px){.module{width:min(100% - 32px,1120px);padding:70px 0}.project-nav{width:calc(100% - 32px)}.project-nav .nav-links,.project-nav .meta{display:none}.shelf-track{min-height:340px}.shelf .asset{width:48%;margin:0 -14%}.partner-grid{grid-template-columns:repeat(2,1fr)}.flow-copy{grid-template-columns:1fr}.flow-copy h2{grid-column:1}.module--cta{display:block;margin-inline:16px;padding:34px}.cta-media{width:130px;margin-top:28px}}
"""


def landing(snapshot: dict, media_prefix: str = "/api/v1/media") -> str:
    title_field = next((f for f in snapshot["fields"] if f["role"] == "title"), None)
    title = title_field["value"] if title_field else snapshot["project"]["name"]
    hero = next((module for module in snapshot["modules"] if module["kind"] == "hero"), None)
    brand_field = next((f for f in (hero or {}).get("fields", []) if f["role"] == "strong"), None)
    nav_fields = [f for f in (hero or {}).get("fields", []) if f["role"] == "a"]
    used = {f["code"] for f in nav_fields}
    if brand_field:
        used.add(brand_field["code"])
    if title_field:
        used.add(title_field["code"])
    modules = []
    for module in snapshot["modules"]:
        modules.append({**module, "fields": [field for field in module["fields"] if field["code"] not in used]})
    body = "".join(module_html(module, media_prefix) for module in modules)
    brand = brand_field or {"code": "", "value": snapshot["project"]["name"]}
    nav_targets = ("reports", "loop", "services")
    nav = "".join(f'<a href="#{target}" data-field-code="{esc(field["code"])}">{esc(field["value"])}</a>' for target, field in zip(nav_targets, nav_fields))
    title_attr = f' data-field-code="{esc(title_field["code"])}"' if title_field else ""
    revision_label = f"R{snapshot['revision']['number']:03d}"
    return f"""<!doctype html><html lang="zh-CN" style="{brand_css(snapshot)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title{title_attr}>{esc(title)}</title><style>{BASE_CSS}</style></head><body><main class="landing"><nav class="project-nav"><a class="wordmark" href="/projects/{esc(snapshot['project']['code'])}/" data-field-code="{esc(brand['code'])}">{esc(brand['value'])}</a><span class="nav-links">{nav}</span><span class="meta">{esc(snapshot['scenario']['name'])} · {revision_label}</span></nav>{body}</main></body></html>"""


SLIDE_CSS = r"""
*{box-sizing:border-box}html,body{margin:0;background:#15120d;color:var(--ink,#17130D);font-family:"Songti SC","Noto Serif SC",Georgia,serif}.deck{min-height:100vh}.slide{position:relative;width:100vw;aspect-ratio:16/9;min-height:100vh;padding:6.2vw 8vw;background:var(--surface,#F4F0E7);overflow:hidden;display:none}.slide.is-active{display:grid;grid-template-columns:1.08fr .92fr;gap:5vw}.slide-copy{align-self:center;display:flex;flex-direction:column;gap:1.1vw}.slide-copy h1,.slide-copy h2,.slide-copy h3,.slide-copy p,.slide-copy span{margin:0}.slide-copy h1,.slide-copy h2{font-size:clamp(34px,4.3vw,76px);font-weight:500;line-height:1.08}.slide-copy h3{font-size:clamp(22px,2vw,36px)}.slide-copy p,.slide-copy span{font-size:clamp(14px,1.3vw,24px);line-height:1.55;color:var(--muted,#706758)}.slide-copy .a11y-copy{position:absolute;width:1px;height:1px;padding:0;margin:-1px;overflow:hidden;clip:rect(0,0,0,0);white-space:nowrap;border:0}.slide-assets{align-self:center;display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1.2vw;perspective:1100px}.slide-assets .asset{margin:0;padding:.7vw;background:var(--paper,#FFFDF8);border:1px solid rgba(118,85,31,.25);box-shadow:0 1.8vw 3vw rgba(23,19,13,.16);transform:rotateY(-4deg)}.slide-assets img{width:100%;height:18vw;object-fit:contain}.slide-assets figcaption{font:600 .8vw Arial,sans-serif;color:var(--accent,#76551F);margin-top:.5vw}.slide-footer{position:absolute;left:8vw;right:8vw;bottom:2.7vw;display:flex;justify-content:space-between;border-top:1px solid rgba(23,19,13,.18);padding-top:.9vw;font:600 .72vw Arial,sans-serif;letter-spacing:.13em;color:var(--muted,#706758)}.controls{position:fixed;right:24px;bottom:24px;display:flex;gap:8px;z-index:4}.controls button{width:44px;height:44px;border:1px solid #EFE6D2;background:#17130D;color:#FFFDF8;font-size:20px;cursor:pointer}@media print{.slide{display:grid!important;break-after:page;min-height:0}.controls{display:none}}@media(max-aspect-ratio:4/3){.slide{min-height:auto}.slide.is-active{grid-template-columns:1fr}.slide-assets{display:flex}.slide-assets .asset{width:25%}}
"""


def chunked(items: list, size: int) -> list[list]:
    return [items[i:i + size] for i in range(0, len(items), size)] or [[]]


def slides(snapshot: dict, strings: dict, media_prefix: str = "/api/v1/media") -> str:
    pages = []
    page_number = 0
    for module in snapshot["modules"]:
        hidden_fields = [
            field for field in module["fields"]
            if field["role"].startswith("attribute:")
            or (module["kind"] == "hero" and field["role"] in {"title", "a", "strong"})
        ]
        visible_fields = [field for field in module["fields"] if field not in hidden_fields]
        field_chunks = chunked(visible_fields, 12)
        field_chunks[0] = hidden_fields + field_chunks[0]
        asset_chunks = chunked(module["assets"], 6)
        count = max(len(field_chunks), len(asset_chunks))
        for index in range(count):
            page_number += 1
            fields = field_chunks[index] if index < len(field_chunks) else []
            assets = asset_chunks[index] if index < len(asset_chunks) else []
            copy = "".join(
                f'<span class="a11y-copy" data-field-code="{esc(field["code"])}">{esc(field["value"])}</span>'
                if module["kind"] == "hero" and field["role"] in {"title", "a", "strong"}
                else field_node(field)
                for field in fields
            )
            visuals = "".join(asset_node(asset, media_prefix, True) for asset in assets)
            pages.append(f'<section class="slide{(" is-active" if page_number == 1 else "")}" data-slide="{page_number}" data-module-code="{module["code"]}"><div class="slide-copy">{copy}</div><div class="slide-assets">{visuals}</div><footer class="slide-footer"><span>{esc(snapshot["project"]["name"])}</span><span>{page_number:02d}</span></footer></section>')
    labels = {key: esc(strings.get(key, key)) for key in ("slides.previous", "slides.next")}
    script = """<script>(()=>{const s=[...document.querySelectorAll('.slide')];let i=0;function go(n){s[i].classList.remove('is-active');i=(n+s.length)%s.length;s[i].classList.add('is-active');location.hash='slide-'+(i+1)}document.querySelector('[data-prev]').onclick=()=>go(i-1);document.querySelector('[data-next]').onclick=()=>go(i+1);addEventListener('keydown',e=>{if(['ArrowRight','PageDown',' '].includes(e.key))go(i+1);if(['ArrowLeft','PageUp'].includes(e.key))go(i-1)})})()</script>"""
    return f"""<!doctype html><html lang="zh-CN" style="{brand_css(snapshot)}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{esc(snapshot['project']['name'])} Slides</title><style>{SLIDE_CSS}</style></head><body><main class="deck">{''.join(pages)}</main><nav class="controls" aria-label="Slides"><button data-prev aria-label="{labels['slides.previous']}">‹</button><button data-next aria-label="{labels['slides.next']}">›</button></nav>{script}</body></html>"""


def locations(markup: str, attribute: str) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for index, code in enumerate(re.findall(fr'{attribute}="([^"]+)"', markup), 1):
        result.setdefault(code, []).append(str(index))
    return result


def coverage(snapshot: dict, landing_html: str, slides_html: str) -> dict:
    expected_fields = {field["code"] for field in snapshot["fields"]}
    expected_assets = {asset["code"] for asset in snapshot["assets"]}
    land_fields = locations(landing_html, "data-field-code")
    slide_fields = locations(slides_html, "data-field-code")
    land_assets = locations(landing_html, "data-asset-code")
    slide_assets = locations(slides_html, "data-asset-code")
    missing = {
        "landing_fields": sorted(expected_fields - set(land_fields)),
        "slides_fields": sorted(expected_fields - set(slide_fields)),
        "landing_assets": sorted(expected_assets - set(land_assets)),
        "slides_assets": sorted(expected_assets - set(slide_assets)),
    }
    if any(missing.values()):
        raise ValueError(f"artifact coverage failed: {missing}")
    return {
        "project": snapshot["project"]["code"],
        "scenario": snapshot["scenario"]["code"],
        "revision": snapshot["revision"]["code"],
        "field_count": len(expected_fields),
        "asset_count": len(expected_assets),
        "character_count": sum(len(str(field["value"])) for field in snapshot["fields"]),
        "landing": {"fields": land_fields, "assets": land_assets},
        "slides": {"fields": slide_fields, "assets": slide_assets},
        "difference": missing,
    }


def artifact(text: str, path: str, manifest: dict, kind: str) -> dict:
    checksum = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return {
        "checksum": checksum,
        "output_path": path,
        "output_text": text,
        "coverage": manifest,
        "metadata": {"kind": kind, "bytes": len(text.encode("utf-8"))},
        "field_map": [{"code": code, "location": ",".join(locations)} for code, locations in manifest.get(kind, {}).get("fields", {}).items()],
        "asset_map": [{"code": code, "location": ",".join(locations)} for code, locations in manifest.get(kind, {}).get("assets", {}).items()],
    }


def build(snapshot: dict, strings: dict, asset_store: Path) -> dict:
    land = landing(snapshot)
    deck = slides(snapshot, strings)
    manifest = coverage(snapshot, land, deck)
    offline = land
    for asset in snapshot["assets"]:
        path = asset_store / asset["object_path"]
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        offline = offline.replace(
            f"/api/v1/media/{asset['object_path']}",
            f"data:{asset['media_type']};base64,{encoded}",
        )
    coverage_text = json.dumps(manifest, ensure_ascii=False, indent=2, default=str)
    prefix = f"export/{snapshot['project']['code']}/{snapshot['scenario']['slug']}/{snapshot['revision']['code']}"
    return {
        "landing": artifact(land, prefix + "/landing.html", manifest, "landing"),
        "slides": artifact(deck, prefix + "/slides.html", manifest, "slides"),
        "offline-html": artifact(offline, prefix + "/offline.html", manifest, "offline-html"),
        "coverage": artifact(coverage_text, prefix + "/coverage.json", manifest, "coverage"),
    }


def write_build_files(root: Path, builds: dict) -> None:
    for scenario_builds in builds.values():
        for build_data in scenario_builds.values():
            target = root / build_data["output_path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_text(build_data["output_text"] or "", encoding="utf-8")
            tmp.replace(target)
