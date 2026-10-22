import base64,contextlib,importlib.util,io,json,os,tempfile,threading,unittest,urllib.request,urllib.error,http.cookiejar,sqlite3,time
from pathlib import Path
from http.server import ThreadingHTTPServer
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('dg_app',ROOT/'server/app.py');app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)

class ApiTests(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  cls.temp=tempfile.TemporaryDirectory();app.DB=Path(cls.temp.name)/'test.sqlite3';app.DEV=True;app.init_db();cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.Handler);cls.base='http://127.0.0.1:'+str(cls.server.server_port);app.ORIGIN=cls.base;cls.thread=threading.Thread(target=cls.server.serve_forever,daemon=True);cls.thread.start()
 @classmethod
 def tearDownClass(cls):cls.server.shutdown();cls.server.server_close();cls.temp.cleanup()
 def client(self):return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
 def call(self,client,path,method='GET',body=None,headers=None):
  data=json.dumps(body).encode() if body is not None else None;h={'X-Requested-With':'DrunkenGuide','Content-Type':'application/json','Origin':self.base};h.update(headers or {});r=urllib.request.Request(self.base+path,data=data,method=method,headers=h)
  try:
   response=client.open(r);status=response.status;content=response.read();contenttype=response.headers.get_content_type()
  except urllib.error.HTTPError as e:status=e.code;content=e.read();contenttype=e.headers.get_content_type()
  return status,json.loads(content) if contenttype=='application/json' else content
 def register(self,client,name='Tester'):
  email=name.lower()+'@example.test';status,value=self.call(client,'/api/register','POST',{'email':email,'password':'Test-password-123','name':name});self.assertEqual(status,201,value);return value['user']
 def test_complete_lifecycle_and_authorization(self):
  alice,bob,admin=self.client(),self.client(),self.client();a=self.register(alice,'Alice');b=self.register(bob,'Bob');ad=self.register(admin,'Administrator')
  with app.connection() as c:c.execute("UPDATE users SET role='admin' WHERE id=?",(ad['id'],))
  self.assertEqual(self.call(bob,'/api/admin/summary')[0],403)
  self.assertEqual(self.call(self.client(),'/api/state')[0],401)
  self.assertEqual(self.call(alice,'/api/state','PUT',{'state':{'favorites':['negroni'],'party':{'mojito':6},'pantry':{'lime':100},'preferences':{'public_name':False}}})[0],200)
  self.assertEqual(self.call(alice,'/api/state')[1]['state']['party'],{'mojito':6})
  self.assertEqual(self.call(bob,'/api/state')[1]['state'],{})
  self.assertEqual(self.call(alice,'/api/state','PUT',{'state':{'party':{'mojito':-1}}})[0],400)
  image=io.BytesIO();Image.new('RGB',(20,20),'red').save(image,'PNG');encoded='data:image/png;base64,'+base64.b64encode(image.getvalue()).decode()
  status,reply=self.call(alice,'/api/reviews','POST',{'recipe_id':'negroni','rating':5,'text':'Excellent <script>alert(1)</script>','image':encoded});self.assertEqual(status,201,reply)
  own=self.call(alice,'/api/reviews?recipe=negroni')[1];rid=own['reviews'][0]['id'];mid=own['reviews'][0]['image'];self.assertEqual(own['count'],0)
  self.assertEqual(self.call(bob,'/api/reviews?recipe=negroni')[1]['reviews'],[])
  self.assertEqual(self.call(bob,'/api/media/'+mid)[0],404)
  self.assertEqual(self.call(bob,'/api/reviews/'+rid,'DELETE')[0],403)
  self.assertEqual(self.call(admin,'/api/admin/reviews/'+rid,'PUT',{'status':'published'})[0],200)
  public=self.call(self.client(),'/api/reviews?recipe=negroni')[1];self.assertEqual(public['count'],1);self.assertEqual(public['average'],5);self.assertEqual(public['reviews'][0]['author'],'Пользователь');self.assertNotIn('email',public['reviews'][0]);self.assertEqual(self.call(self.client(),'/api/media/'+mid)[0],200)
  self.assertEqual(self.call(alice,'/api/reviews/'+rid,'PUT',{'text':'Updated review','rating':3})[0],200);self.assertEqual(self.call(self.client(),'/api/ratings')[1]['ratings'],{})
  self.assertEqual(self.call(alice,'/api/avatar','POST',{'image':encoded})[0],200)
  self.assertEqual(self.call(admin,'/api/admin/uploads','POST',{'image':'data:image/png;base64,'+base64.b64encode(b'<script>').decode()})[0],400)
  self.assertEqual(self.call(admin,'/api/admin/users/'+b['id'],'PUT',{'blocked':True})[0],200);self.assertEqual(self.call(bob,'/api/me')[0],401)
  catalog=self.call(admin,'/api/catalog')[1];self.assertEqual(self.call(admin,'/api/admin/catalog','PUT',catalog)[0],200)
  catalog['recipes'][0]['parts'][0]['amount']=-1;self.assertEqual(self.call(admin,'/api/admin/catalog','PUT',catalog)[0],400)
  self.assertEqual(self.call(alice,'/api/profile','PUT',{'name':'Alice New','email':'newalice@example.test','current_password':'wrong'})[0],403)
  self.assertEqual(self.call(alice,'/api/profile','PUT',{'name':'Alice New','email':'newalice@example.test','current_password':'Test-password-123','new_password':'Another-password-123'})[0],200)
  self.assertEqual(self.call(alice,'/api/logout','POST',{})[0],200);self.assertEqual(self.call(alice,'/api/me')[0],401)
  self.assertEqual(self.call(alice,'/api/login','POST',{'email':'newalice@example.test','password':'Another-password-123'})[0],200)
  self.assertEqual(self.call(alice,'/api/account','DELETE',{'password':'Another-password-123'})[0],200);self.assertEqual(self.call(alice,'/api/me')[0],401)
  self.assertEqual(self.call(admin,'/api/admin/users/'+b['id'],'DELETE')[0],200)
 def test_custom_recipe_moderation_and_catalog_photos(self):
  author,admin=self.client(),self.client();a=self.register(author,'RecipeAuthor');ad=self.register(admin,'RecipeEditor')
  with app.connection() as c:c.execute("UPDATE users SET role='admin' WHERE id=?",(ad['id'],))
  custom={'name':'My Lemon','description':'Mix lemon and soda in a tall glass.','method':'Сборка в бокале','parts':[{'id':'lemon','amount':30},{'id':'soda','amount':120}]}
  self.assertEqual(self.call(author,'/api/custom-recipes','POST',{'recipe':custom})[0],201)
  rid=self.call(admin,'/api/admin/summary')[1]['custom'][0]['id']
  self.assertEqual(self.call(author,'/api/admin/custom-recipes/'+rid,'PUT',{'status':'published'})[0],403)
  self.assertEqual(self.call(admin,'/api/admin/custom-recipes/'+rid,'PUT',{'status':'published'})[0],200)
  items=self.call(author,'/api/catalog')[1]['recipes'];published=[r for r in items if r['id']=='community-'+rid[:12]];self.assertEqual(len(published),1);self.assertFalse(published[0]['alcoholic'])
  image=io.BytesIO();Image.new('RGB',(10,10),'green').save(image,'PNG');encoded='data:image/png;base64,'+base64.b64encode(image.getvalue()).decode()
  status,upload=self.call(admin,'/api/admin/uploads','POST',{'image':encoded});self.assertEqual(status,201);mid=upload['id']
  value=self.call(admin,'/api/catalog')[1];value['recipes'][0]['photo']=mid;value['recipes'][0]['stepPhotos']=[mid];self.assertEqual(self.call(admin,'/api/admin/catalog','PUT',value)[0],200)
  self.assertEqual(self.call(self.client(),'/api/media/'+mid)[0],200)
  app.init_db();self.assertEqual(self.call(admin,'/api/catalog')[1]['recipes'][0]['photo'],mid)
  self.assertEqual(self.call(author,'/api/state','PUT',{'state':{'plans':[{'name':'Party','party':{'mojito':6},'pantry':{'lime':20},'adjustments':{'lime':130},'bought':{'lime':True}}]}})[0],200)
  self.assertEqual(self.call(author,'/api/state')[1]['state']['plans'][0]['bought'],{'lime':True})
 def test_csrf_private_files_and_validation(self):
  client=self.client();self.assertEqual(self.call(client,'/api/register','POST',{'email':'hacker@example.test','name':'Hack','password':'Test-password-123'},headers={'Origin':'https://evil.example'})[0],403)
  self.assertEqual(self.call(client,'/api/register','POST',{'email':'bad','name':'Bad','password':'Test-password-123'})[0],400)
  for path in ['/server/app.py','/.git/config','/var/drunken-guide.sqlite3','/tests/test_api.py']:
   self.assertEqual(self.call(client,path)[0],404,path)
  self.assertIn(b'apiBase:"/api"',self.call(client,'/site-config.js')[1])
  self.assertEqual(self.call(client,'/api/status')[1]['passwordReset'],False)
if __name__=='__main__':unittest.main()
