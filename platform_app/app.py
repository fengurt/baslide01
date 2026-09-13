from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, File, Form, Header, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .importer import p009_bundle
from .render import build, esc, landing, slides, write_build_files
from .store import Conflict, Store

ROOT = Path(os.environ.get("BASLIDE_ROOT", Path(__file__).resolve().parents[1])).resolve()
ASSET_STORE = Path(os.environ.get("ASSET_STORE", ROOT / "var/assets")).resolve()
READ_ONLY = os.environ.get("BASLIDE_READ_ONLY", "1") != "0"
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://baslide:baslide-local@127.0.0.1:54329/baslide")


def publish_all(store: Store, project: str, draft: str) -> dict:
    strings = store.system_strings()
    rendered = {}
    for scenario in store.scenarios(project):
        snapshot = store.snapshot(project, scenario["code"], "draft")
        rendered[scenario["code"]] = build(snapshot, strings, store.asset_store)
    write_build_files(store.root, rendered)
    return store.publish(draft, rendered)


@asynccontextmanager
async def lifespan(app: FastAPI):
    store = Store(DATABASE_URL, ROOT, ASSET_STORE)
    store.init_schema()
    seeded = store.seed_project(p009_bundle(ROOT))
    store.seed_legacy_catalog()
    if seeded or not store.artifact_text("P009", "P009.SCN.SALES", "landing"):
        draft = store.snapshot("P009", "P009.SCN.SALES", "draft")["revision"]["code"]
        publish_all(store, "P009", draft)
    app.state.store = store
    yield
    store.close()


app = FastAPI(title="Baslide Project Publishing", version="1.0.0", lifespan=lifespan)


@app.middleware("http")
async def protect_editor(request: Request, call_next):
    if READ_ONLY and (request.method not in {"GET", "HEAD", "OPTIONS"}
                      or request.url.path.startswith("/admin/")
                      or request.url.path.endswith("/snapshot")
                      or request.url.path.endswith("/history")
                      or request.url.path == "/api/v1/events"
                      or request.query_params.get("revision", "published") not in {"published", "active"}):
        return JSONResponse({"detail": "Editor access is disabled on this public instance"}, status_code=403)
    response = await call_next(request)
    if request.url.path.startswith(("/api/", "/admin/", "/projects/")):
        response.headers.setdefault("Cache-Control", "no-store")
    return response


@app.exception_handler(KeyError)
async def missing_content(request: Request, exc: KeyError):
    return JSONResponse({"detail": "Content not found"}, status_code=404)


def db(request: Request) -> Store:
    return request.app.state.store


class FieldPatch(BaseModel):
    value: str | int | float | bool | list | dict | None
    scenario: str | None = None


@app.get("/api/v1/projects")
def api_projects(request: Request):
    return db(request).list_projects()


@app.get("/healthz")
def healthz(request: Request):
    return {"status": "ok", "projects": len(db(request).list_projects()), "release": os.environ.get("BASLIDE_RELEASE", "development")}


@app.get("/api/v1/projects/{project}/snapshot")
def api_snapshot(request: Request, project: str, scenario: str = Query(...), revision: str = "published"):
    try:
        response = JSONResponse(db(request).snapshot(project, scenario, revision))
        import hashlib
        response.headers["ETag"] = '"' + hashlib.sha256(response.body).hexdigest() + '"'
        return response
    except KeyError as exc:
        raise HTTPException(404, f"not found: {exc.args[0]}") from exc


@app.patch("/api/v1/drafts/{draft}/fields/{field_code}")
def api_patch_field(request: Request, draft: str, field_code: str, patch: FieldPatch, if_match: str | None = Header(None)):
    if if_match is None:
        raise HTTPException(428, "If-Match is required")
    try:
        expected = int(if_match.strip('"'))
        result = db(request).update_field(draft, field_code, patch.value, expected, patch.scenario)
        response = JSONResponse(result)
        response.headers["ETag"] = result["etag"]
        return response
    except Conflict as exc:
        raise HTTPException(412, "field version conflict") from exc
    except ValueError as exc:
        raise HTTPException(400, str(exc)) from exc
    except KeyError as exc:
        raise HTTPException(404, str(exc)) from exc


@app.post("/api/v1/drafts/{draft}/assets")
async def api_add_asset(
    request: Request,
    draft: str,
    file: UploadFile = File(...),
    module: str = Form(...),
    role: str = Form("dom-image"),
    title: str = Form(""),
):
    try:
        return db(request).add_asset(draft, module, role, title, file.filename or "asset", file.content_type or "application/octet-stream", await file.read(20 * 1024 * 1024 + 1))
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.post("/api/v1/drafts/{draft}/publish")
def api_publish(request: Request, draft: str):
    try:
        return publish_all(db(request), draft.split(".")[0], draft)
    except Conflict as exc:
        raise HTTPException(409, "Draft changed during rendering; retry publishing") from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc


@app.get("/api/v1/events")
def api_events(request: Request, project: str = Query(...)):
    return StreamingResponse(db(request).listen(project), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.get("/api/v1/media/{object_path:path}")
def api_media(request: Request, object_path: str):
    try:
        path = db(request).media_path(object_path)
    except ValueError as exc:
        raise HTTPException(404) from exc
    if not path.is_file():
        raise HTTPException(404)
    return FileResponse(path, headers={"Cache-Control": "public,max-age=31536000,immutable"})


@app.get("/projects/{project}/", response_class=HTMLResponse)
def project_hub(request: Request, project: str):
    try:
        p = db(request).resolve_project(project)
        scenarios = db(request).scenarios(project)
    except KeyError as exc:
        raise HTTPException(404) from exc
    p = {k: esc(v) for k, v in p.items()}
    scenarios = [{k: esc(v) for k, v in item.items()} for item in scenarios]
    strings = db(request).system_strings()
    links = "".join(f'<article><p>{s["code"]}</p><h2>{s["name"]}</h2><a href="/projects/{p["code"]}/{s["slug"]}/landing">Landing</a><a href="/projects/{p["code"]}/{s["slug"]}/slides">Slides</a></article>' for s in scenarios)
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{p['name']}</title><style>{HUB_CSS}</style></head><body><header><p>{p['code']}</p><h1>{p['name']}</h1><p>{p['description']}</p><nav><a href="/admin/projects/{p['code']}">{strings['admin.title']}</a><a href="/projects/{p['code']}/history">{strings['hub.history']}</a></nav></header><main><h2 class="label">{strings['hub.scenarios']}</h2><section>{links}</section></main></body></html>"""


@app.get("/projects/{project}/{scenario}/landing", response_class=HTMLResponse)
def public_landing(request: Request, project: str, scenario: str, revision: str = "published"):
    store = db(request)
    if revision in {"published", "active"}:
        text = store.artifact_text(project, scenario, "landing")
        if text:
            return text
    return landing(store.snapshot(project, scenario, revision))


@app.get("/projects/{project}/{scenario}/slides", response_class=HTMLResponse)
def public_slides(request: Request, project: str, scenario: str, revision: str = "published"):
    store = db(request)
    if revision in {"published", "active"}:
        text = store.artifact_text(project, scenario, "slides")
        if text:
            return text
    return slides(store.snapshot(project, scenario, revision), store.system_strings())


@app.get("/projects/{project}/{scenario}/pages/{slug}", response_class=HTMLResponse)
def public_subpage(request: Request, project: str, scenario: str, slug: str, revision: str = "published"):
    snapshot = db(request).snapshot(project, scenario, revision)
    selected = [module for module in snapshot["modules"] if module["kind"] == slug or module["code"] == slug]
    if not selected:
        raise HTTPException(404)
    snapshot["modules"] = selected
    snapshot["fields"] = [field for module in selected for field in module["fields"]]
    snapshot["assets"] = [asset for module in selected for asset in module["assets"]]
    return landing(snapshot)


@app.get("/projects/{project}/history")
def project_history(request: Request, project: str):
    return db(request).history(project)


@app.get("/admin/projects/{project}", response_class=HTMLResponse)
def project_admin(request: Request, project: str):
    store = db(request)
    p = store.resolve_project(project)
    scenarios = store.scenarios(project)
    strings = store.system_strings()
    return admin_html(p, scenarios, strings)


@app.get("/decks/tiansight-landing-v2/one-pager.html")
def legacy_sales():
    return RedirectResponse("/projects/P009/sales-landing/landing", status_code=307)


@app.get("/decks/tiansight-corporate/one-pager.html")
def legacy_d09_sales():
    return RedirectResponse("/projects/P009/sales-landing/landing", status_code=307)


@app.get("/decks/tiansight-corporate/company-profile.html")
def legacy_d09_corporate():
    return RedirectResponse("/projects/P009/corporate-profile/landing", status_code=307)


HUB_CSS = """*{box-sizing:border-box}body{margin:0;background:#F4F0E7;color:#17130D;font-family:Arial,sans-serif}header,main{width:min(1120px,calc(100% - 48px));margin:auto}header{padding:90px 0 64px;border-bottom:1px solid rgba(23,19,13,.18)}header>p:first-child,.label,article>p{color:#76551F;font-size:12px;font-weight:800;letter-spacing:.14em;text-transform:uppercase}h1{font-family:Georgia,"Songti SC",serif;font-size:clamp(54px,8vw,108px);font-weight:500;line-height:1;margin:22px 0}nav{display:flex;gap:18px;margin-top:30px}a{color:#76551F;text-underline-offset:4px}main{padding:70px 0}main>section{display:grid;grid-template-columns:repeat(2,1fr);border-top:1px solid #76551F}article{min-height:280px;padding:38px 30px;border-bottom:1px solid rgba(23,19,13,.18)}article+article{border-left:1px solid rgba(23,19,13,.18)}article h2{font:500 34px Georgia,"Songti SC",serif;margin:45px 0}article a{margin-right:20px}@media(max-width:700px){main>section{grid-template-columns:1fr}article+article{border-left:0}}"""


def admin_html(project: dict, scenarios: list[dict], strings: dict) -> str:
    options = "".join(f'<option value="{s["code"]}" data-slug="{s["slug"]}">{s["name"]}</option>' for s in scenarios)
    labels = json.dumps(strings, ensure_ascii=False)
    return f"""<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{strings['admin.title']} · {project['name']}</title><style>{ADMIN_CSS}</style></head><body><header><div><span>{project['code']}</span><strong>{project['name']}</strong></div><label>场景<select id="scenario">{options}</select></label><label class="override"><input id="override" type="checkbox">场景覆盖</label><button id="publish">{strings['admin.publish']}</button><a href="/projects/{project['code']}/">项目 Hub</a></header><main><aside><h2>{strings['admin.modules']}</h2><nav id="modules"></nav></aside><section class="editor"><div class="status"><span id="revision"></span><span id="save-state"></span></div><div id="fields"></div></section><section class="preview"><nav><button data-view="landing">{strings['admin.preview.landing']}</button><button data-view="slides">{strings['admin.preview.slides']}</button></nav><iframe id="preview" title="实时预览"></iframe></section></main><script>const PROJECT={json.dumps(project['code'])},LABELS={labels};{ADMIN_JS}</script></body></html>"""


ADMIN_CSS = """*{box-sizing:border-box}body{margin:0;background:#F4F0E7;color:#17130D;font:14px Arial,sans-serif;height:100vh;overflow:hidden}header{height:64px;padding:0 20px;display:flex;align-items:center;gap:20px;border-bottom:1px solid rgba(23,19,13,.22);background:#FFFDF8}header div{margin-right:auto}header span{color:#76551F;font-size:11px;letter-spacing:.12em;margin-right:10px}header select,header button{height:36px;border:1px solid rgba(23,19,13,.25);background:#FFFDF8;color:#17130D;padding:0 12px}header button{background:#17130D;color:#FFFDF8;cursor:pointer}header a{color:#76551F}main{display:grid;grid-template-columns:190px minmax(320px,440px) 1fr;height:calc(100vh - 64px)}aside,.editor{border-right:1px solid rgba(23,19,13,.18);overflow:auto}aside{padding:22px 14px}aside h2{font-size:11px;color:#76551F;letter-spacing:.14em}aside button{display:block;width:100%;padding:11px 8px;border:0;border-bottom:1px solid rgba(23,19,13,.1);text-align:left;background:transparent;cursor:pointer}.editor{padding:18px}.status{display:flex;justify-content:space-between;color:#706758;font-size:11px;margin-bottom:14px}.field{padding:14px 0;border-top:1px solid rgba(23,19,13,.14)}.field label{display:flex;justify-content:space-between;color:#76551F;font-size:10px;letter-spacing:.04em;margin-bottom:7px}.field textarea{width:100%;min-height:72px;resize:vertical;border:1px solid rgba(23,19,13,.18);background:#FFFDF8;padding:10px;color:#17130D;line-height:1.5}.preview{min-width:0;background:#d8d2c8}.preview nav{height:44px;display:flex;align-items:center;padding:0 14px;gap:8px;background:#17130D}.preview button{border:1px solid #76551F;background:transparent;color:#FFFDF8;padding:7px 12px;cursor:pointer}.preview iframe{display:block;width:100%;height:calc(100% - 44px);border:0;background:white}.override{display:flex;align-items:center;gap:6px}@media(max-width:1000px){main{grid-template-columns:160px 1fr}.preview{position:fixed;inset:64px 0 0 52%;z-index:3}.editor{padding-right:calc(48% + 18px)}}"""


ADMIN_JS = r"""
const scenario=document.querySelector('#scenario'),fields=document.querySelector('#fields'),modules=document.querySelector('#modules'),frame=document.querySelector('#preview');
let snapshot,view='landing',queue=Promise.resolve(),saveError=false;
const state=document.querySelector('#save-state');
function preview(){frame.src=`/projects/${PROJECT}/${scenario.options[scenario.selectedIndex].dataset.slug}/${view}?revision=draft&v=${Date.now()}`}
const escapeHTML=value=>String(value).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('"','&quot;');
async function load(){const r=await fetch(`/api/v1/projects/${PROJECT}/snapshot?scenario=${scenario.value}&revision=draft`);if(!r.ok)throw Error(await r.text());snapshot=await r.json();document.querySelector('#revision').textContent=snapshot.revision.code;modules.innerHTML=snapshot.modules.map(m=>`<button data-module="${escapeHTML(m.code)}">${escapeHTML(m.name)} · ${m.fields.length}</button>`).join('');fields.innerHTML=snapshot.fields.map(f=>`<article class="field" data-module="${escapeHTML(f.module_code)}"><label><span>${escapeHTML(f.code)}</span><span>${escapeHTML(f.role)}</span></label><textarea data-code="${escapeHTML(f.code)}" data-base-version="${f.base_version}" data-override-version="${f.override_version ?? ''}">${escapeHTML(f.value)}</textarea></article>`).join('');preview()}
modules.onclick=e=>{const code=e.target.dataset.module;document.querySelector(`.field[data-module="${code}"]`)?.scrollIntoView({behavior:'smooth'})};
fields.oninput=e=>{
  const el=e.target;if(el.tagName!=='TEXTAREA')return;
  const draft=snapshot.revision.code,value=el.value,scope=document.querySelector('#override').checked?snapshot.scenario.code:null;
  state.textContent='保存中';
  queue=queue.then(async()=>{
    if(saveError)throw Error('保存失败，请保留当前文本并刷新后重试');
    const key=scope?'overrideVersion':'baseVersion';
    const r=await fetch(`/api/v1/drafts/${draft}/fields/${el.dataset.code}`,{method:'PATCH',headers:{'Content-Type':'application/json','If-Match':`"${el.dataset[key] || el.dataset.baseVersion}"`},body:JSON.stringify({value,scenario:scope})});
    if(!r.ok)throw Error(r.status===412?LABELS['admin.conflict']:await r.text());
    const data=await r.json();el.dataset[key]=data.version;state.textContent=LABELS['admin.saved'];
  }).catch(error=>{saveError=true;state.textContent=error.message});
};
async function transition(action){
  const controls=[...document.querySelectorAll('textarea,header button,header input,header select')];controls.forEach(el=>el.disabled=true);
  try{await queue;if(saveError)throw Error(state.textContent);await action()}catch(error){alert(error.message)}finally{controls.forEach(el=>el.disabled=false)}
}
scenario.onchange=()=>transition(load);
document.querySelectorAll('[data-view]').forEach(b=>b.onclick=()=>{view=b.dataset.view;preview()});
document.querySelector('#publish').onclick=()=>transition(async()=>{const r=await fetch(`/api/v1/drafts/${snapshot.revision.code}/publish`,{method:'POST'});if(!r.ok)throw Error(await r.text());await load()});
addEventListener('beforeunload',e=>{if(saveError||state.textContent==='保存中'){e.preventDefault();e.returnValue=''}});
new EventSource(`/api/v1/events?project=${PROJECT}`).addEventListener('change',()=>preview());load().catch(error=>{state.textContent=error.message});
"""


class PublicFiles(StaticFiles):
    async def get_response(self, path, scope):
        parts = Path(path).parts
        roots = {"files (10)", "assets", "decks", "previews", "preview", "demos", "templates", "types", "figure-demos", "audit", "prompts"}
        files = {"index.html", "decks.json", "catalog.json", "page-types.json"}
        gallery = path == "skills/guizang-ppt/INDEX.html" or path.startswith("skills/guizang-ppt/assets/")
        if (not gallery and parts and parts[0] not in roots and path not in files and path != ".") or any(
            (part.startswith(".") and part != ".") or part in {"source", "history", "__pycache__"} for part in parts
        ) or Path(path).suffix in {".py", ".sh", ".mjs", ".backup"}:
            raise HTTPException(404)
        response = await super().get_response(path, scope)
        response.headers.setdefault("Cache-Control", "public,max-age=0,must-revalidate")
        return response


app.mount("/", PublicFiles(directory=ROOT, html=True), name="legacy-static")
