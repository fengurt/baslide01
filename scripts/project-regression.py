"""Run only against a disposable seeded database: BASLIDE_TEST_DB=1."""
import os
from pathlib import Path
from platform_app.store import Store, Conflict
from platform_app.render import build

assert os.environ.get('BASLIDE_TEST_DB') == '1', 'Disposable test database required'
root=Path('/app')
s=Store(os.environ['DATABASE_URL'],root,root/'var/assets')
try:
    try:s.snapshot('P009','P009.SCN.SALES','missing')
    except KeyError:pass
    else:raise AssertionError('missing revision accepted')
    snap=s.snapshot('P009','P009.SCN.SALES','draft');draft=snap['revision']['code'];field=snap['fields'][0]
    try:s.update_field(draft,field['code'],'invalid',field['version'],'invalid-scenario')
    except KeyError:pass
    else:raise AssertionError('invalid scenario accepted')
    rendered={v['code']:build(s.snapshot('P009',v['code'],'draft'),s.system_strings(),s.asset_store) for v in s.scenarios('P009')}
    result=s.update_field(draft,field['code'],field['value'],field['base_version'])
    try:s.update_field(draft,field['code'],'stale',field['base_version'],'P009.SCN.SALES')
    except Conflict:pass
    else:raise AssertionError('stale first override accepted')
    try:s.publish(draft,rendered)
    except Conflict:pass
    else:raise AssertionError('stale rendered artifacts published')
    print('PASS missing revision, invalid scenario, stale override, concurrent publish')
finally:s.close()
