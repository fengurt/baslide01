#!/usr/bin/env python3
"""Guard the Qingshuiting freshwater taxonomy in the generated deck."""

from pathlib import Path
import re


HTML = Path(__file__).with_name("presentation.html")
text = HTML.read_text(encoding="utf-8")
slides = re.findall(r'<section class="slide[^>]*>.*?</section>', text, re.S)
assert len(slides) == 109, f"expected 109 slides, got {len(slides)}"
slide_text = "\n".join(slides)

required = (
    "河鲜总类 42 支贡献 <em>¥1,914.8 万</em>",
    "占品项收入 <em>52.9%</em>",
    "河鲜总类（42 支）",
    "套餐已纳入河鲜总类，单列仅用于观察，不重复加总",
    "河鲜总类＝河鲜单品＋套餐；鱼头属于河鲜单品子类",
)
for value in required:
    assert value in text, f"missing taxonomy marker: {value}"

for forbidden in ("河鲜（25 支）", "河鲜类 25 支贡献", "十类合计 ¥3,616.8 万；河鲜占 37.9%"):
    assert forbidden not in slide_text, f"stale exclusive taxonomy: {forbidden}"

for ambiguous_metric in (
    "河鲜品类数",
    "河鲜占单品收入",
    "河鲜占收入比例",
    "河鲜占比",
    "河鲜渗透",
    "河鲜点单率",
    "无河鲜账单",
    "河鲜真实占比",
):
    assert ambiguous_metric not in slide_text, f"ambiguous metric taxonomy: {ambiguous_metric}"

print("PASS qingshuiting taxonomy")
