#!/usr/bin/env python3
from __future__ import annotations

import os
import json
from pathlib import Path

from platform_app.importer import p009_bundle
from platform_app.render import build
from platform_app.store import Store


def main() -> None:
    root = Path(os.environ.get("BASLIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
    store = Store(os.environ["DATABASE_URL"], root, Path(os.environ.get("ASSET_STORE", root / "var/assets")))
    try:
        expected = p009_bundle(root)["acceptance"]["sales"]
        assert expected == {"text": 105, "a11y": 20, "dom_images": 12, "canvas_images": 5}
        assert len(store.list_projects()) == len(json.loads((root / "decks.json").read_text())["decks"])
        for scenario in store.scenarios("P009"):
            snapshot = store.snapshot("P009", scenario["code"], "published")
            artifacts = build(snapshot, store.system_strings(), store.asset_store)
            assert all(not values for values in artifacts["coverage"]["coverage"]["difference"].values())
        sales = store.snapshot("P009", "P009.SCN.SALES", "published")
        assert len(sales["fields"]) == 125
        assert len(sales["assets"]) == 17
        with store.pool.connection() as conn:
            builds = list(conn.execute("""SELECT s.code, count(DISTINCT b.project_revision_id) AS base_revisions,
                count(DISTINCT b.scenario_revision_id) AS scenario_revisions
                FROM artifact_definition d JOIN artifact_build b ON b.id=d.active_build_id
                JOIN scenario s ON s.id=d.scenario_id WHERE d.project_id=(SELECT id FROM project WHERE code='P009')
                GROUP BY s.code"""))
            assert len(builds) == 2
            assert all(row["base_revisions"] == 1 and row["scenario_revisions"] == 1 for row in builds)
        print("project check: catalog project count exact, P009 counts exact, artifact coverage exact")
    finally:
        store.close()


if __name__ == "__main__":
    main()
