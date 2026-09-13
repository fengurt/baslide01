from __future__ import annotations

import hashlib
import json
import os
import shutil
from pathlib import Path
from typing import Iterator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool


class Conflict(Exception):
    pass


class Store:
    def __init__(self, database_url: str, root: Path, asset_store: Path):
        self.database_url = database_url
        self.root = root
        self.asset_store = asset_store
        self.pool = ConnectionPool(database_url, min_size=1, max_size=8, kwargs={"row_factory": dict_row})

    def close(self) -> None:
        self.pool.close()

    def init_schema(self) -> None:
        sql = (Path(__file__).with_name("schema.sql")).read_text(encoding="utf-8")
        with self.pool.connection() as conn:
            conn.execute(sql)
        self.seed_system_strings()

    def seed_system_strings(self) -> None:
        strings = {
            "admin.title": "项目内容工作台",
            "admin.modules": "模块",
            "admin.fields": "字段",
            "admin.preview.landing": "Landing 预览",
            "admin.preview.slides": "Slides 预览",
            "admin.publish": "发布当前草稿",
            "admin.saved": "已自动保存",
            "admin.conflict": "内容已在别处更新，请刷新后再试",
            "admin.history": "版本历史",
            "admin.assets": "素材",
            "hub.scenarios": "项目场景",
            "hub.history": "历史版本",
            "slides.next": "下一页",
            "slides.previous": "上一页",
            "slides.overview": "总览",
        }
        with self.pool.connection() as conn:
            conn.cursor().executemany(
                """INSERT INTO system_string(code,value) VALUES (%s,%s) ON CONFLICT (code,locale)
                   DO UPDATE SET value=EXCLUDED.value, version=system_string.version+1
                   WHERE system_string.value IS DISTINCT FROM EXCLUDED.value""",
                strings.items(),
            )

    def system_strings(self) -> dict[str, str]:
        with self.pool.connection() as conn:
            return {row["code"]: row["value"] for row in conn.execute("SELECT code,value FROM system_string WHERE locale='zh-CN'")}

    def _copy_object(self, path: Path, sha256: str) -> str:
        target = self.asset_store / sha256 / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            shutil.copy2(path, target)
        return str(target.relative_to(self.asset_store))

    def seed_project(self, bundle: dict) -> bool:
        with self.pool.connection() as conn:
            if conn.execute("SELECT 1 FROM project WHERE code=%s", (bundle["project"]["code"],)).fetchone():
                return False
            with conn.transaction():
                project = conn.execute(
                    "INSERT INTO project(code,slug,name,description,metadata) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                    (*bundle["project"].values(), json.dumps({"brand": bundle["brand"], "acceptance": bundle["acceptance"]})),
                ).fetchone()
                project_id = project["id"]
                for alias in bundle["aliases"]:
                    conn.execute("INSERT INTO project_alias(project_id,alias_type,alias) VALUES (%s,'legacy',%s)", (project_id, alias))
                published = conn.execute(
                    "INSERT INTO project_revision(project_id,code,number,status,message,published_at) VALUES (%s,'P009.R001',1,'published','Imported legacy sources',now()) RETURNING id",
                    (project_id,),
                ).fetchone()["id"]
                draft = conn.execute(
                    "INSERT INTO project_revision(project_id,code,number,status,based_on_id,message) VALUES (%s,'P009.DRAFT.R002',2,'draft',%s,'Working draft') RETURNING id",
                    (project_id, published),
                ).fetchone()["id"]
                conn.execute("UPDATE project SET active_revision_id=%s WHERE id=%s", (published, project_id))
                category = conn.execute(
                    "INSERT INTO content_category(code,name) VALUES ('project-copy','项目文案') ON CONFLICT (code) DO UPDATE SET name=EXCLUDED.name RETURNING id"
                ).fetchone()["id"]
                module_ids = {}
                for i, item in enumerate(bundle["modules"], 1):
                    code = f"P009.M{i:03d}"
                    mid = conn.execute(
                        "INSERT INTO module(project_id,code,kind,name,sort_order) VALUES (%s,%s,%s,%s,%s) RETURNING id",
                        (project_id, code, item["kind"], item["name"], item["sort_order"]),
                    ).fetchone()["id"]
                    module_ids[item["kind"]] = mid
                    conn.cursor().executemany(
                        "INSERT INTO module_version(module_id,project_revision_id,sort_order,visible) VALUES (%s,%s,%s,true)",
                        [(mid, published, item["sort_order"]), (mid, draft, item["sort_order"])],
                    )
                source_version_ids = {}
                for source in bundle["sources"]:
                    sid = conn.execute(
                        "INSERT INTO source_document(project_id,code,kind,title) VALUES (%s,%s,%s,%s) RETURNING id",
                        (project_id, source["code"], source["kind"], source["title"]),
                    ).fetchone()["id"]
                    source_path = source["path"]
                    if source_path.startswith("https://"):
                        object_path = source_path
                    else:
                        object_path = self._copy_object(Path(source_path), source["sha256"])
                    source_version_ids[source["code"]] = conn.execute(
                        "INSERT INTO source_version(source_id,version,sha256,object_path,media_type,bytes,metadata) VALUES (%s,1,%s,%s,%s,%s,%s) RETURNING id",
                        (sid, source["sha256"], object_path, source["media_type"], source["bytes"], json.dumps(source.get("metadata", {}))),
                    ).fetchone()["id"]
                scenario_ids = {}
                scenario_revision_ids = {}
                for item in bundle["scenarios"]:
                    sid = conn.execute(
                        "INSERT INTO scenario(project_id,code,slug,name) VALUES (%s,%s,%s,%s) RETURNING id",
                        (project_id, item["code"], item["slug"], item["name"]),
                    ).fetchone()["id"]
                    scenario_ids[item["code"]] = sid
                    published_sr = conn.execute(
                        "INSERT INTO scenario_revision(scenario_id,project_revision_id,code,number,status,published_at) VALUES (%s,%s,%s,1,'published',now()) RETURNING id",
                        (sid, published, item["code"] + ".R001"),
                    ).fetchone()["id"]
                    draft_sr = conn.execute(
                        "INSERT INTO scenario_revision(scenario_id,project_revision_id,code,number,status) VALUES (%s,%s,%s,2,'draft') RETURNING id",
                        (sid, draft, item["code"] + ".DRAFT.R002"),
                    ).fetchone()["id"]
                    scenario_revision_ids[item["code"]] = {"published": published_sr, "draft": draft_sr}
                    conn.execute("UPDATE scenario SET active_revision_id=%s WHERE id=%s", (published_sr, sid))
                    for kind, suffix in (("landing", "LANDING"), ("slides", "SLIDES"), ("offline-html", "OFFLINE"), ("coverage", "COVERAGE")):
                        conn.execute(
                            "INSERT INTO artifact_definition(project_id,scenario_id,code,kind,slug) VALUES (%s,%s,%s,%s,%s)",
                            (project_id, sid, f"P009.ART.{suffix}.{item['code'].split('.')[-1]}", kind, kind),
                        )
                sales_source = source_version_ids["P009.SRC.SALES.HTML"]
                corp_source = source_version_ids["P009.SRC.CORP.HTML"]
                for field in bundle["fields"]:
                    source_version = sales_source if field["code"].endswith(".SALES") else corp_source
                    fid = conn.execute(
                        """INSERT INTO content_field(project_id,module_id,category_id,code,role,sort_order,source_type,source_version_id,visible_scenarios,created_revision_id,metadata)
                           VALUES (%s,%s,%s,%s,%s,%s,'import',%s,%s,%s,%s) RETURNING id""",
                        (project_id, module_ids[field["module"]], category, field["code"], field["role"], field["sort_order"], source_version, field["visible_scenarios"], published, json.dumps(field["metadata"])),
                    ).fetchone()["id"]
                    conn.cursor().executemany(
                        "INSERT INTO content_value(field_id,project_revision_id,value) VALUES (%s,%s,%s)",
                        [(fid, published, json.dumps(field["value"], ensure_ascii=False)), (fid, draft, json.dumps(field["value"], ensure_ascii=False))],
                    )
                for asset in bundle["assets"]:
                    aid = conn.execute(
                        "INSERT INTO asset(project_id,module_id,code,role,title,sort_order,visible_scenarios,created_revision_id) VALUES (%s,%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                        (project_id, module_ids[asset["module"]], asset["code"], asset["role"], asset["title"], asset["sort_order"], asset["visible_scenarios"], published),
                    ).fetchone()["id"]
                    object_path = self._copy_object(Path(asset["source_path"]), asset["sha256"])
                    avid = conn.execute(
                        "INSERT INTO asset_version(asset_id,version,sha256,object_path,media_type,bytes) VALUES (%s,1,%s,%s,%s,%s) RETURNING id",
                        (aid, asset["sha256"], object_path, asset["media_type"], asset["bytes"]),
                    ).fetchone()["id"]
                    conn.cursor().executemany(
                        "INSERT INTO asset_binding(asset_id,project_revision_id,asset_version_id) VALUES (%s,%s,%s)",
                        [(aid, published, avid), (aid, draft, avid)],
                    )
                conn.execute(
                    "INSERT INTO change_event(project_id,revision_id,kind,payload) VALUES (%s,%s,'project.seeded',%s)",
                    (project_id, draft, json.dumps(bundle["acceptance"])),
                )
        return True

    def seed_legacy_catalog(self) -> int:
        catalog_path = self.root / "decks.json"
        if not catalog_path.is_file():
            return 0
        records = json.loads(catalog_path.read_text(encoding="utf-8")).get("decks", [])
        created = 0
        with self.pool.connection() as conn, conn.transaction():
            for record in records:
                if record["id"] == "D09":
                    continue
                code = f"P{int(record['id'][1:]):03d}"
                if conn.execute("SELECT 1 FROM project WHERE code=%s", (code,)).fetchone():
                    continue
                project_id = conn.execute(
                    "INSERT INTO project(code,slug,name,description,metadata) VALUES (%s,%s,%s,'Legacy project awaiting field migration',%s) RETURNING id",
                    (code, record["slug"], record["title"], json.dumps({"legacy": record}, ensure_ascii=False)),
                ).fetchone()["id"]
                published = conn.execute(
                    "INSERT INTO project_revision(project_id,code,number,status,message,published_at) VALUES (%s,%s,1,'published','Catalog import',now()) RETURNING id",
                    (project_id, code + ".R001"),
                ).fetchone()["id"]
                conn.execute(
                    "INSERT INTO project_revision(project_id,code,number,status,based_on_id,message) VALUES (%s,%s,2,'draft',%s,'Migration draft')",
                    (project_id, code + ".DRAFT.R002", published),
                )
                conn.execute("UPDATE project SET active_revision_id=%s WHERE id=%s", (published, project_id))
                aliases = {record["id"], record["slug"], record.get("href", "")}
                for alias in aliases - {""}:
                    conn.execute("INSERT INTO project_alias(project_id,alias_type,alias) VALUES (%s,'legacy',%s) ON CONFLICT DO NOTHING", (project_id, alias))
                variants = record.get("variants") or [{"id": record["id"] + ".1", "title": record["title"], "href": record.get("href"), "source": record.get("source")}]
                for index, variant in enumerate(variants, 1):
                    scenario_code = f"{code}.SCN.{index:02d}"
                    slug = "default" if len(variants) == 1 else f"variant-{index}"
                    scenario_id = conn.execute(
                        "INSERT INTO scenario(project_id,code,slug,name) VALUES (%s,%s,%s,%s) RETURNING id",
                        (project_id, scenario_code, slug, variant["title"]),
                    ).fetchone()["id"]
                    sr = conn.execute(
                        "INSERT INTO scenario_revision(scenario_id,project_revision_id,code,number,status,published_at) VALUES (%s,%s,%s,1,'published',now()) RETURNING id",
                        (scenario_id, published, scenario_code + ".R001"),
                    ).fetchone()["id"]
                    conn.execute("UPDATE scenario SET active_revision_id=%s WHERE id=%s", (sr, scenario_id))
                    href = variant.get("href")
                    if href:
                        conn.execute("INSERT INTO project_alias(project_id,alias_type,alias) VALUES (%s,'legacy-url',%s) ON CONFLICT DO NOTHING", (project_id, href))
                    source = variant.get("source")
                    if source:
                        source_path = Path(source)
                        if not source_path.is_absolute():
                            source_path = self.root / source_path
                        if source_path.is_file():
                            sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
                            sid = conn.execute(
                                "INSERT INTO source_document(project_id,code,kind,title) VALUES (%s,%s,'legacy-source',%s) RETURNING id",
                                (project_id, f"{code}.SRC.{index:03d}", source_path.name),
                            ).fetchone()["id"]
                            conn.execute(
                                "INSERT INTO source_version(source_id,version,sha256,object_path,media_type,bytes,metadata) VALUES (%s,1,%s,%s,%s,%s,%s)",
                                (sid, sha, self._copy_object(source_path, sha), "application/octet-stream", source_path.stat().st_size, json.dumps({"legacy_path": source})),
                            )
                        else:
                            conn.execute(
                                "INSERT INTO migration_hold(path,sha256,reason) VALUES (%s,%s,'legacy source is missing') ON CONFLICT DO NOTHING",
                                (source, hashlib.sha256(source.encode()).hexdigest()),
                            )
                created += 1
            registered = {record["slug"] for record in records}
            slides_root = self.root / "slides"
            if slides_root.is_dir():
                for path in slides_root.iterdir():
                    if path.is_dir() and path.name not in registered:
                        conn.execute(
                            "INSERT INTO migration_hold(path,sha256,reason) VALUES (%s,%s,'unregistered slides directory requires project assignment') ON CONFLICT DO NOTHING",
                            (str(path.relative_to(self.root)), hashlib.sha256(str(path).encode()).hexdigest()),
                        )
        return created

    def resolve_project(self, value: str, conn=None) -> dict:
        query = """SELECT DISTINCT p.* FROM project p LEFT JOIN project_alias a ON a.project_id=p.id
                   WHERE p.code=%s OR p.slug=%s OR a.alias=%s"""
        if conn is not None:
            row = conn.execute(query, (value, value, value)).fetchone()
        else:
            with self.pool.connection() as db:
                row = db.execute(query, (value, value, value)).fetchone()
        if not row:
            raise KeyError(value)
        return row

    def list_projects(self) -> list[dict]:
        with self.pool.connection() as conn:
            return list(conn.execute("""SELECT p.code,p.slug,p.name,p.description,p.metadata,
              (SELECT count(*) FROM scenario s WHERE s.project_id=p.id) AS scenario_count,
              (SELECT code FROM project_revision r WHERE r.id=p.active_revision_id) AS active_revision
              FROM project p ORDER BY p.code"""))

    def scenarios(self, project_value: str) -> list[dict]:
        with self.pool.connection() as conn:
            project = self.resolve_project(project_value, conn)
            return list(conn.execute("SELECT code,slug,name FROM scenario WHERE project_id=%s ORDER BY id", (project["id"],)))

    def add_asset(self, draft_code: str, module_code: str, role: str, title: str, filename: str, media_type: str, body: bytes) -> dict:
        if not body or len(body) > 20 * 1024 * 1024:
            raise ValueError("asset must contain 1 byte to 20 MiB")
        sha256 = hashlib.sha256(body).hexdigest()
        safe_name = Path(filename).name
        if safe_name in {"", ".", ".."}:
            raise ValueError("invalid filename")
        target = self.asset_store / sha256 / safe_name
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            target.write_bytes(body)
        object_path = str(target.relative_to(self.asset_store))
        with self.pool.connection() as conn, conn.transaction():
            draft = conn.execute("SELECT * FROM project_revision WHERE code=%s AND status='draft' FOR UPDATE", (draft_code,)).fetchone()
            if not draft:
                raise KeyError(draft_code)
            module = conn.execute("SELECT * FROM module WHERE code=%s AND project_id=%s", (module_code, draft["project_id"])).fetchone()
            if not module:
                raise KeyError(module_code)
            n = conn.execute("SELECT count(*)+1 AS n FROM asset WHERE module_id=%s", (module["id"],)).fetchone()["n"]
            code = f"{module_code}.A{n:03d}.MANUAL"
            aid = conn.execute(
                "INSERT INTO asset(project_id,module_id,code,role,title,sort_order,created_revision_id) VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id",
                (draft["project_id"], module["id"], code, role, title or safe_name, n, draft["id"]),
            ).fetchone()["id"]
            avid = conn.execute(
                "INSERT INTO asset_version(asset_id,version,sha256,object_path,media_type,bytes) VALUES (%s,1,%s,%s,%s,%s) RETURNING id",
                (aid, sha256, object_path, media_type, len(body)),
            ).fetchone()["id"]
            conn.execute("INSERT INTO asset_binding(asset_id,project_revision_id,asset_version_id) VALUES (%s,%s,%s)", (aid, draft["id"], avid))
            conn.execute("INSERT INTO change_event(project_id,revision_id,kind,payload) VALUES (%s,%s,'asset.added',%s)", (draft["project_id"], draft["id"], json.dumps({"asset": code})))
            conn.execute("UPDATE project_revision SET version=version+1 WHERE id=%s", (draft["id"],))
            return {"code": code, "sha256": sha256, "object_path": object_path}

    def snapshot(self, project_value: str, scenario_value: str, revision: str = "published") -> dict:
        with self.pool.connection() as conn:
            project = self.resolve_project(project_value, conn)
            scenario = conn.execute(
                "SELECT * FROM scenario WHERE project_id=%s AND (code=%s OR slug=%s)",
                (project["id"], scenario_value, scenario_value),
            ).fetchone()
            if not scenario:
                raise KeyError(scenario_value)
            if revision == "draft":
                base = conn.execute("SELECT * FROM project_revision WHERE project_id=%s AND status='draft' ORDER BY number DESC LIMIT 1", (project["id"],)).fetchone()
                sr = conn.execute("SELECT * FROM scenario_revision WHERE scenario_id=%s AND project_revision_id=%s AND status='draft'", (scenario["id"], base["id"])).fetchone()
            elif revision in {"published", "active"}:
                base = conn.execute("SELECT * FROM project_revision WHERE id=%s", (project["active_revision_id"],)).fetchone()
                sr = conn.execute("SELECT * FROM scenario_revision WHERE id=%s", (scenario["active_revision_id"],)).fetchone()
            else:
                base = conn.execute("SELECT * FROM project_revision WHERE project_id=%s AND code=%s", (project["id"], revision)).fetchone()
                if not base:
                    raise KeyError(revision)
                sr = conn.execute("SELECT * FROM scenario_revision WHERE scenario_id=%s AND project_revision_id=%s", (scenario["id"], base["id"])).fetchone()
            if not base or not sr:
                raise KeyError(revision)
            rows = list(conn.execute(
                """SELECT f.id,f.code,f.role,f.data_type,f.sort_order,f.metadata,m.code AS module_code,m.kind AS module_kind,m.name AS module_name,m.sort_order AS module_order,
                    COALESCE(o.value,v.value) AS value,COALESCE(o.sort_order,f.sort_order) AS effective_order,COALESCE(o.version,v.version) AS version,
                    v.version AS base_version,o.version AS override_version,COALESCE(o.visible,true) AS visible
                   FROM content_field f JOIN module m ON m.id=f.module_id
                   JOIN content_value v ON v.field_id=f.id AND v.project_revision_id=%s
                   LEFT JOIN scenario_override o ON o.field_id=f.id AND o.scenario_revision_id=%s
                   WHERE f.project_id=%s AND (cardinality(f.visible_scenarios)=0 OR %s=ANY(f.visible_scenarios))
                   ORDER BY m.sort_order,effective_order,f.code""",
                (base["id"], sr["id"], project["id"], scenario["code"]),
            ))
            assets = list(conn.execute(
                """SELECT a.id,a.code,a.role,a.title,a.sort_order,m.code AS module_code,m.kind AS module_kind,
                   av.sha256,av.object_path,av.media_type,av.width,av.height
                   FROM asset a LEFT JOIN module m ON m.id=a.module_id
                   JOIN asset_binding ab ON ab.asset_id=a.id AND ab.project_revision_id=%s AND ab.visible
                   JOIN asset_version av ON av.id=ab.asset_version_id
                   WHERE a.project_id=%s AND (cardinality(a.visible_scenarios)=0 OR %s=ANY(a.visible_scenarios))
                   ORDER BY m.sort_order,a.sort_order,a.code""",
                (base["id"], project["id"], scenario["code"]),
            ))
            modules = []
            for module in conn.execute("SELECT code,kind,name,sort_order FROM module WHERE project_id=%s ORDER BY sort_order", (project["id"],)):
                module_fields = [row for row in rows if row["module_code"] == module["code"] and row["visible"]]
                module_assets = [row for row in assets if row["module_code"] == module["code"]]
                if module_fields or module_assets:
                    modules.append({**module, "fields": module_fields, "assets": module_assets})
            return {
                "project": {k: project[k] for k in ("code", "slug", "name", "description", "metadata")},
                "scenario": {k: scenario[k] for k in ("code", "slug", "name")},
                "revision": {"code": base["code"], "number": base["number"], "status": base["status"], "version": base["version"]},
                "scenario_revision": {"code": sr["code"], "number": sr["number"], "status": sr["status"]},
                "modules": modules,
                "fields": [row for row in rows if row["visible"]],
                "assets": assets,
            }

    def update_field(self, draft_code: str, field_code: str, value, expected_version: int, scenario_code: str | None = None) -> dict:
        with self.pool.connection() as conn, conn.transaction():
            draft = conn.execute("SELECT * FROM project_revision WHERE code=%s AND status='draft' FOR UPDATE", (draft_code,)).fetchone()
            if not draft:
                raise KeyError(draft_code)
            field = conn.execute("SELECT * FROM content_field WHERE code=%s AND project_id=%s", (field_code, draft["project_id"])).fetchone()
            if not field:
                raise KeyError(field_code)
            if scenario_code:
                sr = conn.execute("""SELECT sr.* FROM scenario_revision sr JOIN scenario s ON s.id=sr.scenario_id
                    WHERE s.code=%s AND sr.project_revision_id=%s AND sr.status='draft'""", (scenario_code, draft["id"])).fetchone()
                if not sr:
                    raise KeyError(scenario_code)
                row = conn.execute("SELECT * FROM scenario_override WHERE scenario_revision_id=%s AND field_id=%s", (sr["id"], field["id"])).fetchone()
                base_value = conn.execute("SELECT version FROM content_value WHERE field_id=%s AND project_revision_id=%s", (field["id"], draft["id"])).fetchone()
                if (row or base_value)["version"] != expected_version:
                    raise Conflict(field_code)
                if row:
                    version = row["version"] + 1
                    conn.execute("UPDATE scenario_override SET value=%s,version=%s WHERE id=%s", (json.dumps(value, ensure_ascii=False), version, row["id"]))
                else:
                    version = 1
                    conn.execute("INSERT INTO scenario_override(scenario_revision_id,field_id,value,version) VALUES (%s,%s,%s,1)", (sr["id"], field["id"], json.dumps(value, ensure_ascii=False)))
            else:
                row = conn.execute("SELECT * FROM content_value WHERE field_id=%s AND project_revision_id=%s FOR UPDATE", (field["id"], draft["id"])).fetchone()
                if row["version"] != expected_version:
                    raise Conflict(field_code)
                version = row["version"] + 1
                conn.execute("UPDATE content_value SET value=%s,version=%s,updated_at=now() WHERE id=%s", (json.dumps(value, ensure_ascii=False), version, row["id"]))
            conn.execute(
                "INSERT INTO change_event(project_id,revision_id,kind,payload) VALUES (%s,%s,'field.updated',%s)",
                (draft["project_id"], draft["id"], json.dumps({"field": field_code, "scenario": scenario_code, "version": version})),
            )
            conn.execute("UPDATE project_revision SET version=version+1 WHERE id=%s", (draft["id"],))
            return {"field": field_code, "version": version, "etag": f'"{version}"'}

    def publish(self, draft_code: str, rendered: dict) -> dict:
        with self.pool.connection() as conn, conn.transaction():
            draft = conn.execute("SELECT * FROM project_revision WHERE code=%s AND status='draft' FOR UPDATE", (draft_code,)).fetchone()
            if not draft:
                raise KeyError(draft_code)
            project = conn.execute("SELECT * FROM project WHERE id=%s FOR UPDATE", (draft["project_id"],)).fetchone()
            scenario_revisions = list(conn.execute("""SELECT sr.*,s.code AS scenario_code FROM scenario_revision sr
                JOIN scenario s ON s.id=sr.scenario_id WHERE sr.project_revision_id=%s AND sr.status='draft' FOR UPDATE""", (draft["id"],)))
            if not scenario_revisions:
                raise ValueError("draft has no scenarios")
            for sr in scenario_revisions:
                builds = rendered.get(sr["scenario_code"])
                if not builds or {"landing", "slides", "offline-html", "coverage"} - set(builds):
                    raise ValueError(f"missing artifacts for {sr['scenario_code']}")
                if builds["coverage"]["coverage"].get("revision_version") != draft["version"]:
                    raise Conflict(draft_code)
                for kind, build in builds.items():
                    definition = conn.execute("SELECT * FROM artifact_definition WHERE scenario_id=%s AND kind=%s", (sr["scenario_id"], kind)).fetchone()
                    number = conn.execute("SELECT COALESCE(max(number),0)+1 AS n FROM artifact_build WHERE artifact_definition_id=%s", (definition["id"],)).fetchone()["n"]
                    bid = conn.execute(
                        """INSERT INTO artifact_build(artifact_definition_id,project_revision_id,scenario_revision_id,number,status,checksum,output_path,output_text,coverage,metadata)
                           VALUES (%s,%s,%s,%s,'ready',%s,%s,%s,%s,%s) RETURNING id""",
                        (definition["id"], draft["id"], sr["id"], number, build["checksum"], build["output_path"], build.get("output_text"), json.dumps(build.get("coverage", {})), json.dumps(build.get("metadata", {}))),
                    ).fetchone()["id"]
                    conn.execute("UPDATE artifact_definition SET active_build_id=%s WHERE id=%s", (bid, definition["id"]))
                    for location in build.get("field_map", []):
                        conn.execute("INSERT INTO artifact_field_map(build_id,field_id,location) SELECT %s,id,%s FROM content_field WHERE code=%s", (bid, location["location"], location["code"]))
                    for location in build.get("asset_map", []):
                        conn.execute("INSERT INTO artifact_field_map(build_id,asset_id,location) SELECT %s,id,%s FROM asset WHERE code=%s", (bid, location["location"], location["code"]))
                conn.execute("UPDATE scenario_revision SET status='published',published_at=now() WHERE id=%s", (sr["id"],))
                conn.execute("UPDATE scenario SET active_revision_id=%s WHERE id=%s", (sr["id"], sr["scenario_id"]))
            conn.execute("UPDATE project_revision SET status='published',published_at=now() WHERE id=%s", (draft["id"],))
            conn.execute("UPDATE project SET active_revision_id=%s WHERE id=%s", (draft["id"], project["id"]))
            next_number = draft["number"] + 1
            next_code = f"{project['code']}.DRAFT.R{next_number:03d}"
            next_draft = conn.execute(
                "INSERT INTO project_revision(project_id,code,number,status,based_on_id,message) VALUES (%s,%s,%s,'draft',%s,'Working draft') RETURNING id",
                (project["id"], next_code, next_number, draft["id"]),
            ).fetchone()["id"]
            conn.execute("INSERT INTO content_value(field_id,project_revision_id,value) SELECT field_id,%s,value FROM content_value WHERE project_revision_id=%s", (next_draft, draft["id"]))
            conn.execute("INSERT INTO module_version(module_id,project_revision_id,sort_order,visible) SELECT module_id,%s,sort_order,visible FROM module_version WHERE project_revision_id=%s", (next_draft, draft["id"]))
            conn.execute("INSERT INTO asset_binding(asset_id,project_revision_id,asset_version_id,visible) SELECT asset_id,%s,asset_version_id,visible FROM asset_binding WHERE project_revision_id=%s", (next_draft, draft["id"]))
            for old_sr in scenario_revisions:
                next_sr = conn.execute(
                    "INSERT INTO scenario_revision(scenario_id,project_revision_id,code,number,status) VALUES (%s,%s,%s,%s,'draft') RETURNING id",
                    (old_sr["scenario_id"], next_draft, old_sr["scenario_code"] + f".DRAFT.R{next_number:03d}", next_number),
                ).fetchone()["id"]
                conn.execute("""INSERT INTO scenario_override(scenario_revision_id,field_id,value,visible,sort_order)
                    SELECT %s,field_id,value,visible,sort_order FROM scenario_override WHERE scenario_revision_id=%s""", (next_sr, old_sr["id"]))
            conn.execute(
                "INSERT INTO change_event(project_id,revision_id,kind,payload) VALUES (%s,%s,'project.published',%s)",
                (project["id"], draft["id"], json.dumps({"published": draft_code, "next_draft": next_code})),
            )
            return {"published_revision": draft_code, "draft": next_code}

    def artifact_text(self, project_value: str, scenario_value: str, kind: str) -> str | None:
        with self.pool.connection() as conn:
            project = self.resolve_project(project_value, conn)
            row = conn.execute("""SELECT b.output_text FROM artifact_definition d JOIN scenario s ON s.id=d.scenario_id
                JOIN artifact_build b ON b.id=d.active_build_id
                WHERE d.project_id=%s AND (s.code=%s OR s.slug=%s) AND d.kind=%s""",
                (project["id"], scenario_value, scenario_value, kind)).fetchone()
            return row["output_text"] if row else None

    def register_export(self, project_value: str, scenario_value: str, kind: str, output_path: str, checksum: str, size: int) -> dict:
        if kind not in {"png", "pdf"}:
            raise ValueError(kind)
        with self.pool.connection() as conn, conn.transaction():
            project = self.resolve_project(project_value, conn)
            scenario = conn.execute("SELECT * FROM scenario WHERE project_id=%s AND (code=%s OR slug=%s)", (project["id"], scenario_value, scenario_value)).fetchone()
            source = conn.execute("""SELECT b.* FROM artifact_definition d JOIN artifact_build b ON b.id=d.active_build_id
                WHERE d.project_id=%s AND d.scenario_id=%s AND d.kind='landing'""", (project["id"], scenario["id"])).fetchone()
            if not source:
                raise ValueError("landing build is missing")
            suffix = scenario["code"].split(".")[-1]
            definition = conn.execute(
                """INSERT INTO artifact_definition(project_id,scenario_id,code,kind,slug) VALUES (%s,%s,%s,%s,%s)
                   ON CONFLICT (scenario_id,kind,slug) DO UPDATE SET code=artifact_definition.code RETURNING id""",
                (project["id"], scenario["id"], f"{project['code']}.ART.{kind.upper()}.{suffix}", kind, kind),
            ).fetchone()
            number = conn.execute("SELECT COALESCE(max(number),0)+1 AS n FROM artifact_build WHERE artifact_definition_id=%s", (definition["id"],)).fetchone()["n"]
            build_id = conn.execute(
                """INSERT INTO artifact_build(artifact_definition_id,project_revision_id,scenario_revision_id,number,status,checksum,output_path,coverage,metadata)
                   VALUES (%s,%s,%s,%s,'ready',%s,%s,%s,%s) RETURNING id""",
                (definition["id"], source["project_revision_id"], source["scenario_revision_id"], number, checksum, output_path, json.dumps(source["coverage"]), json.dumps({"kind": kind, "bytes": size, "derived_from": source["id"]})),
            ).fetchone()["id"]
            conn.execute("""INSERT INTO artifact_field_map(build_id,field_id,asset_id,location)
                SELECT %s,field_id,asset_id,'rendered:'||location FROM artifact_field_map WHERE build_id=%s""", (build_id, source["id"]))
            conn.execute("UPDATE artifact_definition SET active_build_id=%s WHERE id=%s", (build_id, definition["id"]))
            conn.execute("INSERT INTO change_event(project_id,revision_id,kind,payload) VALUES (%s,%s,'artifact.exported',%s)", (project["id"], source["project_revision_id"], json.dumps({"kind": kind, "path": output_path})))
            return {"kind": kind, "build_id": build_id, "revision_id": source["project_revision_id"], "checksum": checksum}

    def history(self, project_value: str) -> dict:
        with self.pool.connection() as conn:
            project = self.resolve_project(project_value, conn)
            revisions = list(conn.execute("SELECT code,number,status,message,version,created_at,published_at FROM project_revision WHERE project_id=%s ORDER BY number DESC", (project["id"],)))
            events = list(conn.execute("SELECT id,kind,payload,created_at FROM change_event WHERE project_id=%s ORDER BY id DESC LIMIT 100", (project["id"],)))
            return {"project": project["code"], "revisions": revisions, "events": events}

    def listen(self, project_value: str) -> Iterator[str]:
        project = self.resolve_project(project_value)
        with psycopg.connect(self.database_url, autocommit=True, row_factory=dict_row) as conn:
            conn.execute("LISTEN project_change")
            yield "event: ready\ndata: {}\n\n"
            while True:
                received = False
                for notify in conn.notifies(timeout=15, stop_after=1):
                    received = True
                    payload = json.loads(notify.payload)
                    if payload.get("project_id") == project["id"]:
                        yield f"event: change\ndata: {json.dumps(payload)}\n\n"
                if not received:
                    yield ": keepalive\n\n"

    def media_path(self, object_path: str) -> Path:
        path = (self.asset_store / object_path).resolve()
        path.relative_to(self.asset_store.resolve())
        return path
