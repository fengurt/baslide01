import urllib.request,urllib.error
import sys
base=sys.argv[1].rstrip('/')
for path,expected in [('/',200),('/decks.json',200),('/platform_app/app.py',404),('/projects/P009/no-scenario/landing',404),('/.git/config',404),('/decks/youyuan-skp/source/manifest.json',404),('/admin/projects/P009',403),('/api/v1/projects/P009/snapshot?scenario=P009.SCN.SALES&revision=draft',403),('/projects/P009/sales-landing/landing?revision=P009.DRAFT.R003',403)]:
 try:r=urllib.request.urlopen(base+path); status=r.status
 except urllib.error.HTTPError as e:status=e.code
 assert status==expected,(path,status)
print('PASS public routes, internal file isolation, draft/editor isolation')
