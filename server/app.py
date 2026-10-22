#!/usr/bin/env python3
"""Same-origin static + API server. SQLite persists outside the public content tree."""
from __future__ import annotations
import argparse,base64,contextlib,getpass,hashlib,hmac,io,json,os,re,secrets,sqlite3,time,warnings
from pathlib import Path
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from urllib.parse import urlsplit,parse_qs,unquote
from PIL import Image,ImageOps

ROOT=Path(__file__).resolve().parents[1]
DB=Path(os.environ.get('APP_DB',ROOT/'var/drunken-guide.sqlite3'))
DEV=os.environ.get('APP_ENV','development')=='development'
ORIGIN=os.environ.get('APP_ORIGIN','http://127.0.0.1:8001').rstrip('/')
COOKIE='dg_session'
MAX_BODY=5*1024*1024

class ApiError(Exception):
 def __init__(self,message,status=400):self.message,self.status=message,status

@contextlib.contextmanager
def connection():
 c=sqlite3.connect(DB,timeout=20);c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON')
 try:
  with c:yield c
 finally:c.close()

def init_db():
 DB.parent.mkdir(parents=True,exist_ok=True)
 with connection() as c:
  c.executescript('''PRAGMA journal_mode=WAL;
  CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,name TEXT NOT NULL,password TEXT NOT NULL,role TEXT NOT NULL DEFAULT 'user',blocked INTEGER NOT NULL DEFAULT 0,avatar TEXT,created_at INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS sessions(token TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,expires INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS state(user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,data TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS media(id TEXT PRIMARY KEY,user_id TEXT REFERENCES users(id) ON DELETE CASCADE,kind TEXT NOT NULL,mime TEXT NOT NULL,data BLOB NOT NULL);
  CREATE TABLE IF NOT EXISTS reviews(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,recipe_id TEXT NOT NULL,rating INTEGER NOT NULL CHECK(rating BETWEEN 1 AND 5),text TEXT NOT NULL,image TEXT REFERENCES media(id),status TEXT NOT NULL DEFAULT 'pending',created_at INTEGER NOT NULL,UNIQUE(user_id,recipe_id));
  CREATE TABLE IF NOT EXISTS settings(key TEXT PRIMARY KEY,data TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS custom_recipes(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,data TEXT NOT NULL,status TEXT NOT NULL DEFAULT 'pending',created_at INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS attempts(key TEXT NOT NULL,at INTEGER NOT NULL);
  ''')
 if DB.exists():DB.chmod(0o600)

def digest(value):return hashlib.sha256(value.encode()).hexdigest()
def password_hash(password):
 salt=secrets.token_bytes(16);return salt.hex()+':'+hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1).hex()
def check_password(password,encoded):
 if not isinstance(password,str):return False
 try:
  salt,expected=encoded.split(':');actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1).hex();return hmac.compare_digest(actual,expected)
 except (ValueError,TypeError):return False

def text(value,name,limit,minimum=1):
 if not isinstance(value,str) or not minimum<=len(value.strip())<=limit:raise ApiError(f'{name}: допустимо от {minimum} до {limit} символов.')
 return value.strip()
def email(value):
 value=text(value,'Email',254).lower()
 if not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',value):raise ApiError('Некорректный email.')
 return value
def validate_password(value):
 if not isinstance(value,str) or not 10<=len(value)<=128:raise ApiError('Пароль должен содержать 10–128 символов.')
 return value

def public_user(row):return {k:row[k] for k in ('id','email','name','role','avatar')}

def catalog(c):
 row=c.execute("SELECT data FROM settings WHERE key='catalog'").fetchone();data=json.loads(row['data']) if row else json.loads((ROOT/'content/platform-data.json').read_text())
 published={('community-'+r['id'][:12]) for r in c.execute("SELECT id FROM custom_recipes WHERE status='published'")}
 data['recipes']=[r for r in data['recipes'] if not r['id'].startswith('community-') or r['id'] in published]
 ingredients={i['id']:i for i in data['ingredients']};existing={r['id'] for r in data['recipes']}
 for custom in c.execute("SELECT id,data FROM custom_recipes WHERE status='published'"):
  raw=json.loads(custom['data']);id='community-'+custom['id'][:12]
  if id in existing or any(p['id'] not in ingredients for p in raw['parts']):continue
  alcoholic=any(ingredients[p['id']]['abv']>0 for p in raw['parts']);bases=[ingredients[p['id']]['name'] for p in raw['parts'] if ingredients[p['id']]['abv']>0]
  data['recipes'].append(dict(id=id,name=raw['name'],ru=raw['name'],intro=raw['description'],base=bases[0] if bases else 'Без алкоголя',taste='Авторский',color='Разный',complexity='Средний',method=raw['method'],type='Авторский',minutes=10,alcoholic=alcoholic,parts=raw['parts'],occasions=['other'] if 'other' in {o['id'] for o in data['occasions']} else [],steps=[raw['description']],tools='Мерный стаканчик и инструменты по способу приготовления',garnish='По авторскому рецепту',tile=None,photoLabel='Схематичная иллюстрация авторского рецепта',substitutions=[]))
 return data

def validate_catalog(data):
 if not isinstance(data,dict):raise ApiError('Каталог должен быть объектом JSON.')
 ingredients=data.get('ingredients');recipes=data.get('recipes');occasions=data.get('occasions')
 if not isinstance(ingredients,list) or not 1<=len(ingredients)<=1000 or not isinstance(recipes,list) or not 1<=len(recipes)<=1000 or not isinstance(occasions,list):raise ApiError('Некорректные списки каталога.')
 def ident(v):
  if not isinstance(v,str) or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,79}',v):raise ApiError('Идентификаторы: латиница, цифры и дефис, до 80 символов.')
  return v
 ids=set();occ=set()
 for i in ingredients:
  if not isinstance(i,dict):raise ApiError('Ингредиент должен быть объектом.')
  id=ident(i.get('id'))
  if id in ids:raise ApiError('Идентификаторы ингредиентов повторяются.')
  ids.add(id);text(i.get('name'),'Название ингредиента',100)
  if i.get('unit') not in ['мл','г','шт']:raise ApiError('Единица: мл, г или шт.')
  if isinstance(i.get('abv'),bool) or not isinstance(i.get('abv'),(int,float)) or not 0<=i['abv']<=100:raise ApiError('Крепость ингредиента: 0–100%.')
 for o in occasions:
  if not isinstance(o,dict):raise ApiError('Повод должен быть объектом.')
  oid=ident(o.get('id'));text(o.get('name'),'Название повода',100)
  if oid in occ:raise ApiError('Повторяющийся повод.')
  occ.add(oid)
 rids=set()
 for r in recipes:
  if not isinstance(r,dict):raise ApiError('Рецепт должен быть объектом.')
  rid=ident(r.get('id'))
  if rid in rids:raise ApiError('Идентификаторы рецептов повторяются.')
  rids.add(rid)
  for field in ['name','ru','base','taste','color','complexity','method','intro','type','garnish','tools']:text(r.get(field),field,2000)
  if not isinstance(r.get('alcoholic'),bool):raise ApiError('alcoholic должен быть true или false.')
  if not isinstance(r.get('minutes'),int) or not 1<=r['minutes']<=240:raise ApiError('Время: 1–240 минут.')
  if not isinstance(r.get('steps'),list) or not 1<=len(r['steps'])<=30:raise ApiError('Нужны шаги приготовления.')
  for step in r['steps']:text(step,'Шаг',2000)
  if not isinstance(r.get('parts'),list) or not 1<=len(r['parts'])<=50:raise ApiError('Некорректные ингредиенты рецепта.')
  for part in r['parts']:
   if not isinstance(part,dict) or part.get('id') not in ids or isinstance(part.get('amount'),bool) or not isinstance(part.get('amount'),(int,float)) or not 0<part['amount']<=10000:raise ApiError('Некорректная дозировка или ссылка на ингредиент.')
  if not isinstance(r.get('occasions'),list) or not all(o in occ for o in r['occasions']):raise ApiError('Неизвестный повод.')
  if r.get('tile') is not None and (not isinstance(r['tile'],list) or len(r['tile'])!=2 or r['tile'][0] not in [0,384,768,1152] or r['tile'][1] not in [0,512]):raise ApiError('Недопустимая область изображения.')
  if r.get('photo') is not None and not re.fullmatch(r'[a-f0-9]{32}',str(r['photo'])):raise ApiError('Некорректный идентификатор фотографии.')
  if r.get('stepPhotos') is not None and (not isinstance(r['stepPhotos'],list) or len(r['stepPhotos'])>len(r['steps']) or any(not isinstance(v,str) or not re.fullmatch(r'[a-f0-9]{32}',v) for v in r['stepPhotos'])):raise ApiError('Некорректные фотографии этапов.')
  for s in r.get('substitutions',[]):
   if not isinstance(s,dict) or s.get('fromId') not in {p['id'] for p in r['parts']} or s.get('toId') not in ids or not isinstance(s.get('ratio'),(int,float)) or not 0<s['ratio']<=10:raise ApiError('Некорректная замена.')
   text(s.get('note'),'Описание замены',2000)
 encyclopedia=data.get('encyclopedia',[])
 if not isinstance(encyclopedia,list) or len(encyclopedia)>100:raise ApiError('Некорректная энциклопедия.')
 seen=set()
 for item in encyclopedia:
  if not isinstance(item,dict):raise ApiError('Категория должна быть объектом.')
  eid=ident(item.get('id'))
  if eid in seen:raise ApiError('Повторяющаяся категория энциклопедии.')
  seen.add(eid)
  for field in ['name','summary','production','types','profile','brands','fact','base']:text(item.get(field),field,3000)
 return data

def validate_state(value,data):
 if not isinstance(value,dict):raise ApiError('Данные должны быть объектом.')
 if len(json.dumps(value,allow_nan=False).encode())>500000:raise ApiError('Слишком большой объём данных.')
 allowed={'favorites','compare','party','pantry','adjustments','bought','plans','custom','preferences'}
 if set(value)-allowed:raise ApiError('Неизвестные поля персональных данных.')
 ids={r['id'] for r in data['recipes']};ingredients={i['id'] for i in data['ingredients']}
 for field in ['favorites','compare']:
  v=value.get(field,[])
  if not isinstance(v,list) or len(v)>(4 if field=='compare' else 1000) or any(not isinstance(i,str) or i not in ids for i in v):raise ApiError('Некорректная коллекция.')
 def amounts(obj,valid,maxval,integer=False):
  if not isinstance(obj,dict) or len(obj)>1000:raise ApiError('Некорректный список количеств.')
  for id,n in obj.items():
   if id not in valid or isinstance(n,bool) or not isinstance(n,(int,float)) or not 0<=n<=maxval or (integer and (n<1 or int(n)!=n)):raise ApiError('Некорректное количество.')
 for field in ['pantry','adjustments']:amounts(value.get(field,{}),ingredients,100000)
 amounts(value.get('party',{}),ids,100,True)
 bought=value.get('bought',{})
 if not isinstance(bought,dict) or any(k not in ingredients or not isinstance(v,bool) for k,v in bought.items()):raise ApiError('Некорректные отметки покупок.')
 plans=value.get('plans',[])
 if not isinstance(plans,list) or len(plans)>20:raise ApiError('Можно хранить до 20 планов.')
 for p in plans:
  if not isinstance(p,dict):raise ApiError('Некорректный план.')
  text(p.get('name'),'Название плана',100);amounts(p.get('party'),ids,100,True)
  for field in ['pantry','adjustments']:amounts(p.get(field,{}),ingredients,100000)
  if not isinstance(p.get('bought',{}),dict) or any(k not in ingredients or not isinstance(v,bool) for k,v in p.get('bought',{}).items()):raise ApiError('Некорректный сохранённый список покупок.')
 custom=value.get('custom',[])
 if not isinstance(custom,list) or len(custom)>50:raise ApiError('Можно хранить до 50 своих рецептов.')
 for r in custom:
  if not isinstance(r,dict):raise ApiError('Некорректный свой рецепт.')
  text(r.get('name'),'Название рецепта',100);text(r.get('description'),'Описание',2000);text(r.get('method'),'Способ',100)
  if not isinstance(r.get('parts'),list) or not 1<=len(r['parts'])<=50:raise ApiError('Нужны ингредиенты.')
  for p in r['parts']:amounts({p.get('id'):p.get('amount')},ingredients,10000)
 preferences=value.get('preferences',{})
 if not isinstance(preferences,dict) or set(preferences)-{'taste','base','ingredient','type','public_name'}:raise ApiError('Некорректные предпочтения.')
 for k,v in preferences.items():
  if k=='public_name' and not isinstance(v,bool):raise ApiError('Некорректная настройка приватности.')
  if k!='public_name' and (not isinstance(v,str) or len(v)>100):raise ApiError('Некорректное предпочтение.')
 return value

def image_data(value):
 if not isinstance(value,str) or len(value)>4500000:raise ApiError('Фото слишком большое.')
 match=re.fullmatch(r'data:image/(jpeg|png|webp);base64,([A-Za-z0-9+/=\r\n]+)',value)
 if not match:raise ApiError('Разрешены JPEG, PNG и WebP.')
 try:
  raw=base64.b64decode(match[2],validate=True)
  if len(raw)>3*1024*1024:raise ApiError('Фото должно быть не больше 3 МБ.')
  with warnings.catch_warnings():
   warnings.simplefilter('error',Image.DecompressionBombWarning)
   with Image.open(io.BytesIO(raw)) as image:
    if image.width*image.height>20000000:raise ApiError('Слишком большое разрешение фото.')
    image.load();image=ImageOps.exif_transpose(image).convert('RGB');image.thumbnail((1600,1600));out=io.BytesIO();image.save(out,'JPEG',quality=85)
  return out.getvalue()
 except ApiError:raise
 except Exception:raise ApiError('Не удалось прочитать изображение.')

def store_image(c,user_id,kind,value):
 blob=image_data(value);id=secrets.token_hex(16);c.execute('INSERT INTO media VALUES(?,?,?,?,?)',(id,user_id,kind,'image/jpeg',blob));return id

class Handler(SimpleHTTPRequestHandler):
 server_version='DrunkenGuide'
 def __init__(self,*args,**kwargs):super().__init__(*args,directory=str(ROOT),**kwargs)
 def log_message(self,format,*args):
  # Do not log request bodies, cookie values, or emails.
  print(f'{self.command} {urlsplit(self.path).path} {args[1] if len(args)>1 else ""}',flush=True)
 def end_headers(self):
  self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','DENY')
  self.send_header('Content-Security-Policy',"default-src 'self'; media-src 'self' blob:; img-src 'self' data:; style-src 'self'; script-src 'self'; connect-src 'self'; font-src 'self'; object-src 'none'; base-uri 'self'; frame-ancestors 'none'; form-action 'self'")
  super().end_headers()
 def json(self,value,status=200,cookie=None):
  body=json.dumps(value,ensure_ascii=False,allow_nan=False).encode();
  if status<400 and self.command!='GET' and getattr(self,'_active_db',None) is not None:self._active_db.commit()
  self.send_response(status);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store')
  if cookie:self.send_header('Set-Cookie',cookie)
  self.end_headers();self.wfile.write(body)
 def body(self):
  try:length=int(self.headers.get('Content-Length','0'))
  except ValueError:raise ApiError('Некорректная длина запроса.')
  if not 0<length<=MAX_BODY:raise ApiError('Недопустимый размер запроса.',413)
  if self.headers.get_content_type()!='application/json':raise ApiError('Нужен JSON.',415)
  try:value=json.loads(self.rfile.read(length),parse_constant=lambda _:(_ for _ in ()).throw(ValueError()))
  except (ValueError,UnicodeDecodeError):raise ApiError('Неверный JSON.')
  if not isinstance(value,dict):raise ApiError('Тело запроса должно быть объектом.')
  return value
 def auth(self,c,required=True,admin=False):
  token=None
  for item in self.headers.get('Cookie','').split(';'):
   k,_,v=item.strip().partition('=')
   if k==COOKIE:token=v
  row=c.execute('SELECT u.* FROM users u JOIN sessions s ON u.id=s.user_id WHERE s.token=? AND s.expires>? AND u.blocked=0',(digest(token),int(time.time()))).fetchone() if token else None
  if required and row is None:raise ApiError('Войдите в аккаунт.',401)
  if admin and (row is None or row['role']!='admin'):raise ApiError('Недостаточно прав.',403)
  return row
 def session_cookie(self,c,user):
  token=secrets.token_urlsafe(32);c.execute('INSERT INTO sessions VALUES(?,?,?)',(digest(token),user['id'],int(time.time())+7*86400));return f'{COOKIE}={token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800'+('' if DEV else '; Secure')
 def rate(self,c,route):
  now=int(time.time());key=digest(self.client_address[0]+'|'+route);c.execute('DELETE FROM attempts WHERE at<?',(now-600,))
  if c.execute('SELECT count(*) FROM attempts WHERE key=?',(key,)).fetchone()[0]>=20:raise ApiError('Слишком много попыток. Повторите через 10 минут.',429)
  c.execute('INSERT INTO attempts VALUES(?,?)',(key,now));c.commit()
 def do_GET(self):
  path=urlsplit(self.path).path
  if path.startswith('/api/'):
   self.handle_api();return
  if path=='/site-config.js':
   body=b'window.DG_CONFIG={apiBase:"/api"};';self.send_response(200);self.send_header('Content-Type','text/javascript');self.send_header('Content-Length',str(len(body)));self.send_header('Cache-Control','no-store');self.end_headers();self.wfile.write(body);return
  decoded=unquote(path);candidate=(ROOT/decoded.lstrip('/')).resolve()
  if any(part.startswith('.') for part in Path(decoded).parts) or not candidate.is_relative_to(ROOT) or (candidate.is_dir() and path!='/') or any(part in {'server','tests','scripts','var'} for part in Path(decoded).parts):self.send_error(404);return
  if path!='/' and candidate.suffix.lower() not in {'.html','.css','.js','.json','.png','.jpg','.jpeg','.svg','.webp','.ttf','.woff2','.txt','.ico'}:self.send_error(404);return
  super().do_GET()
 def do_HEAD(self):
  self.send_error(405)
 def do_POST(self):self.handle_api()
 def do_PUT(self):self.handle_api()
 def do_DELETE(self):self.handle_api()
 def handle_api(self):
  try:
   if self.command!='GET':
    if self.headers.get('X-Requested-With')!='DrunkenGuide':raise ApiError('Запрос должен отправляться с сайта.',403)
    origin=self.headers.get('Origin')
    if origin and origin!=ORIGIN:raise ApiError('Недопустимый источник запроса.',403)
    if self.headers.get('Sec-Fetch-Site')=='cross-site':raise ApiError('Межсайтовый запрос отклонён.',403)
   with connection() as c:
    self._active_db=c
    try:self.dispatch(c)
    finally:self._active_db=None
  except ApiError as error:self.json({'error':error.message},error.status)
  except sqlite3.IntegrityError:self.json({'error':'Такая запись уже существует или нарушает ограничения.'},409)
  except (KeyError,TypeError,ValueError) as error:self.json({'error':'Некорректные данные запроса.'},400)
  except Exception as error:
   print('API internal error:',type(error).__name__,flush=True);self.json({'error':'Внутренняя ошибка сервера.'},500)
 def dispatch(self,c):
  path=urlsplit(self.path).path;query=parse_qs(urlsplit(self.path).query);method=self.command
  if path=='/api/status' and method=='GET':self.json({'available':True,'passwordReset':False,'emailVerification':False,'oauthGoogle':False,'oauthApple':False});return
  if path=='/api/catalog' and method=='GET':self.json(catalog(c));return
  if path=='/api/ratings' and method=='GET':
   rows=c.execute("SELECT recipe_id,AVG(rating) average,COUNT(*) count FROM reviews WHERE status='published' GROUP BY recipe_id").fetchall();self.json({'ratings':{r['recipe_id']:dict(average=r['average'],count=r['count']) for r in rows}});return
  if path in ['/api/login','/api/register'] and method=='POST':
   self.rate(c,path);body=self.body();mail=email(body.get('email'));password=validate_password(body.get('password'))
   if path=='/api/register':
    name=text(body.get('name'),'Имя',80);id=secrets.token_hex(16)
    if c.execute('SELECT 1 FROM users WHERE email=?',(mail,)).fetchone():raise ApiError('Не удалось зарегистрироваться с этим email. Попробуйте вход.',409)
    c.execute('INSERT INTO users(id,email,name,password,created_at) VALUES(?,?,?,?,?)',(id,mail,name,password_hash(password),int(time.time())));user=c.execute('SELECT * FROM users WHERE id=?',(id,)).fetchone()
   else:
    user=c.execute('SELECT * FROM users WHERE email=?',(mail,)).fetchone()
    valid=check_password(password,user['password'] if user else '00'*16+':'+'00'*64)
    if not user or not valid or user['blocked']:raise ApiError('Неверный email или пароль.',401)
   cookie=self.session_cookie(c,user);self.json({'user':public_user(user)},201 if path.endswith('register') else 200,cookie);return
  if path=='/api/logout' and method=='POST':
   for item in self.headers.get('Cookie','').split(';'):
    k,_,v=item.strip().partition('=')
    if k==COOKIE:c.execute('DELETE FROM sessions WHERE token=?',(digest(v),))
   self.json({'ok':True},cookie=f'{COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0'+('' if DEV else '; Secure'));return
  if path=='/api/me' and method=='GET':self.json({'user':public_user(self.auth(c))});return
  if path=='/api/profile' and method=='PUT':
   u=self.auth(c);body=self.body();name=text(body.get('name'),'Имя',80);mail=email(body.get('email'));newpass=body.get('new_password')
   if mail!=u['email'] or newpass:
    if not check_password(body.get('current_password',''),u['password']):raise ApiError('Укажите текущий пароль.',403)
   password=password_hash(validate_password(newpass)) if newpass else u['password'];c.execute('UPDATE users SET name=?,email=?,password=? WHERE id=?',(name,mail,password,u['id']))
   if newpass:c.execute('DELETE FROM sessions WHERE user_id=?',(u['id'],))
   updated=c.execute('SELECT * FROM users WHERE id=?',(u['id'],)).fetchone();cookie=self.session_cookie(c,updated) if newpass else None;self.json({'user':public_user(updated)},cookie=cookie);return
  if path=='/api/avatar' and method=='POST':
   u=self.auth(c);body=self.body();id=store_image(c,u['id'],'avatar',body.get('image'));c.execute('UPDATE users SET avatar=? WHERE id=?',(id,u['id']));self.json({'id':id});return
  if path=='/api/account' and method=='DELETE':
   u=self.auth(c);body=self.body()
   if not check_password(body.get('password',''),u['password']):raise ApiError('Неверный пароль.',403)
   self.delete_user(c,u['id']);self.json({'ok':True},cookie=f'{COOKIE}=; HttpOnly; SameSite=Lax; Path=/; Max-Age=0');return
  if path=='/api/state':
   u=self.auth(c)
   if method=='GET':
    row=c.execute('SELECT data FROM state WHERE user_id=?',(u['id'],)).fetchone();self.json({'state':json.loads(row['data']) if row else {}});return
   if method=='PUT':
    value=validate_state(self.body().get('state'),catalog(c));c.execute('INSERT INTO state VALUES(?,?) ON CONFLICT(user_id) DO UPDATE SET data=excluded.data',(u['id'],json.dumps(value)));self.json({'ok':True});return
  if path=='/api/custom-recipes' and method=='POST':
   u=self.auth(c);b=self.body();r=b.get('recipe');validate_state({'custom':[r]},catalog(c))
   if c.execute("SELECT count(*) FROM custom_recipes WHERE user_id=? AND status='pending'",(u['id'],)).fetchone()[0]>=10:raise ApiError('Можно отправить до 10 рецептов на проверку.')
   c.execute('INSERT INTO custom_recipes VALUES(?,?,?,?,?)',(secrets.token_hex(16),u['id'],json.dumps(r), 'pending',int(time.time())));self.json({'ok':True,'status':'pending'},201);return
  if path=='/api/my-recipes' and method=='GET':
   u=self.auth(c);rows=c.execute('SELECT id,data,status FROM custom_recipes WHERE user_id=?',(u['id'],)).fetchall();self.json({'recipes':[dict(id=r['id'],recipe=json.loads(r['data']),status=r['status']) for r in rows]});return
  if path=='/api/my-reviews' and method=='GET':
   u=self.auth(c);self.json({'reviews':[dict(r) for r in c.execute('SELECT id,recipe_id,rating,text,status,created_at FROM reviews WHERE user_id=? ORDER BY created_at DESC',(u['id'],))]});return
  if path=='/api/reviews' and method=='GET':
   u=self.auth(c,False);recipe=query.get('recipe',[''])[0];uid=u['id'] if u else '';rows=c.execute("SELECT r.*,u.name author,s.data user_state FROM reviews r JOIN users u ON u.id=r.user_id LEFT JOIN state s ON s.user_id=u.id WHERE r.recipe_id=? AND (r.status='published' OR r.user_id=?) ORDER BY r.created_at DESC",(recipe,uid)).fetchall();items=[]
   for r in rows:
    item={k:r[k] for k in ['id','recipe_id','rating','text','image','status','created_at']};prefs=json.loads(r['user_state']) if r['user_state'] else {};item['author']=r['author'] if prefs.get('preferences',{}).get('public_name',True) else 'Пользователь';item['can_edit']=r['user_id']==uid;items.append(item)
   public=[r for r in items if r['status']=='published'];self.json({'reviews':items,'count':len(public),'average':sum(r['rating'] for r in public)/len(public) if public else 0});return
  if path=='/api/reviews' and method=='POST':
   u=self.auth(c);body=self.body();rid=body.get('recipe_id')
   if rid not in {r['id'] for r in catalog(c)['recipes']}:raise ApiError('Рецепт не найден.',404)
   rating=body.get('rating');review=text(body.get('text'),'Отзыв',2000)
   if type(rating) is not int or not 1<=rating<=5:raise ApiError('Оценка: от 1 до 5.')
   image=store_image(c,u['id'],'review',body['image']) if body.get('image') else None
   c.execute('INSERT INTO reviews VALUES(?,?,?,?,?,?,?,?)',(secrets.token_hex(16),u['id'],rid,rating,review,image,'pending',int(time.time())));self.json({'ok':True,'status':'pending'},201);return
  match=re.fullmatch(r'/api/reviews/([a-f0-9]{32})',path)
  if match:
   u=self.auth(c);r=c.execute('SELECT * FROM reviews WHERE id=?',(match[1],)).fetchone()
   if not r:raise ApiError('Отзыв не найден.',404)
   if r['user_id']!=u['id'] and u['role']!='admin':raise ApiError('Нельзя изменять чужой отзыв.',403)
   if method=='DELETE':
    c.execute('DELETE FROM reviews WHERE id=?',(r['id'],))
    if r['image']:c.execute('DELETE FROM media WHERE id=?',(r['image'],))
    self.json({'ok':True});return
   if method=='PUT':
    b=self.body();rating=b.get('rating');review=text(b.get('text'),'Отзыв',2000)
    if type(rating) is not int or not 1<=rating<=5:raise ApiError('Оценка: от 1 до 5.')
    c.execute("UPDATE reviews SET rating=?,text=?,status='pending' WHERE id=?",(rating,review,r['id']));self.json({'ok':True});return
  match=re.fullmatch(r'/api/media/([a-f0-9]{32})',path)
  if match and method=='GET':
   media=c.execute('SELECT * FROM media WHERE id=?',(match[1],)).fetchone()
   if not media:raise ApiError('Изображение не найдено.',404)
   if media['kind']=='review':
    r=c.execute('SELECT * FROM reviews WHERE image=?',(media['id'],)).fetchone();u=self.auth(c,False)
    if not r or (r['status']!='published' and (not u or (u['role']!='admin' and r['user_id']!=u['id']))):raise ApiError('Изображение недоступно.',404)
   self.send_response(200);self.send_header('Content-Type',media['mime']);self.send_header('Content-Length',str(len(media['data'])));self.send_header('Cache-Control','private, max-age=300');self.end_headers();self.wfile.write(media['data']);return
  if path.startswith('/api/admin/'):
   u=self.auth(c,admin=True)
   if path=='/api/admin/summary' and method=='GET':
    reviews=c.execute("SELECT r.*,u.name author FROM reviews r JOIN users u ON u.id=r.user_id WHERE status='pending' ORDER BY created_at").fetchall();users=c.execute('SELECT id,email,name,role,blocked FROM users ORDER BY created_at').fetchall();custom=c.execute("SELECT r.id,r.data,u.name author FROM custom_recipes r JOIN users u ON u.id=r.user_id WHERE r.status='pending'").fetchall();self.json({'custom':[dict(id=r['id'],recipe=json.loads(r['data']),author=r['author']) for r in custom],'users':[dict(x) for x in users],'reviews':[{k:r[k] for k in ['id','recipe_id','rating','text','image','author']} for r in reviews]});return
   if path=='/api/admin/catalog' and method=='PUT':
    value=validate_catalog(self.body());
    retained={r['id'] for r in value['recipes']}
    for custom in c.execute("SELECT id FROM custom_recipes WHERE status='published'").fetchall():
     if 'community-'+custom['id'][:12] not in retained:c.execute("UPDATE custom_recipes SET status='rejected' WHERE id=?",(custom['id'],))
    for r in value['recipes']:
     for mid in ([r['photo']] if r.get('photo') else [])+r.get('stepPhotos',[]):
      if not c.execute("SELECT 1 FROM media WHERE id=? AND kind='content'",(mid,)).fetchone():raise ApiError('Фотография каталога не найдена.')
    c.execute("INSERT INTO settings VALUES('catalog',?) ON CONFLICT(key) DO UPDATE SET data=excluded.data",(json.dumps(value,allow_nan=False),));self.json({'ok':True});return
   if path=='/api/admin/uploads' and method=='POST':
    b=self.body();id=store_image(c,u['id'],'content',b.get('image'));self.json({'id':id},201);return
   m=re.fullmatch(r'/api/admin/custom-recipes/([a-f0-9]{32})',path)
   if m and method=='PUT':
    status=self.body().get('status')
    if status not in ['published','rejected']:raise ApiError('Неизвестный статус рецепта.')
    c.execute('UPDATE custom_recipes SET status=? WHERE id=?',(status,m[1]));self.json({'ok':True});return
   m=re.fullmatch(r'/api/admin/reviews/([a-f0-9]{32})',path)
   if m and method=='PUT':
    b=self.body()
    if b.get('status') not in ['published','pending']:raise ApiError('Неизвестный статус.')
    c.execute('UPDATE reviews SET status=? WHERE id=?',(b['status'],m[1]));self.json({'ok':True});return
   m=re.fullmatch(r'/api/admin/users/([a-f0-9]{32})',path)
   if m:
    target=c.execute('SELECT * FROM users WHERE id=?',(m[1],)).fetchone()
    if not target:raise ApiError('Пользователь не найден.',404)
    if target['role']=='admin':raise ApiError('Операция над администратором недоступна через сайт.',403)
    if method=='PUT':
     blocked=self.body().get('blocked')
     if type(blocked) is not bool:raise ApiError('Неверный статус блокировки.')
     c.execute('UPDATE users SET blocked=? WHERE id=?',(int(blocked),target['id']));c.execute('DELETE FROM sessions WHERE user_id=?',(target['id'],));self.json({'ok':True});return
    if method=='DELETE':self.delete_user(c,target['id']);self.json({'ok':True});return
  raise ApiError('Маршрут не найден.',404)
 def delete_user(self,c,uid):
  # Delete review rows before their linked media, then sessions/state cascade.
  c.execute('DELETE FROM reviews WHERE user_id=?',(uid,));c.execute('DELETE FROM users WHERE id=?',(uid,))

def main():
 parser=argparse.ArgumentParser(description=__doc__);sub=parser.add_subparsers(dest='command');serve=sub.add_parser('serve');serve.add_argument('--host',default='127.0.0.1');serve.add_argument('--port',type=int,default=8001);admin=sub.add_parser('create-admin');admin.add_argument('--email',required=True);admin.add_argument('--name',default='Администратор');args=parser.parse_args();init_db()
 if args.command=='create-admin':
  password=getpass.getpass('Admin password (10–128 chars): ');validate_password(password);mail=email(args.email)
  with connection() as c:
   if c.execute('SELECT 1 FROM users WHERE email=?',(mail,)).fetchone():raise SystemExit('Email already exists; role changes require an explicit database maintenance operation.')
   c.execute('INSERT INTO users(id,email,name,password,role,created_at) VALUES(?,?,?,?,?,?)',(secrets.token_hex(16),mail,args.name,password_hash(password),'admin',int(time.time())))
  print('Administrator created.');return
 if not DEV and (not ORIGIN.startswith('https://') or os.environ.get('APP_ORIGIN') is None):raise SystemExit('Production requires APP_ORIGIN=https://your-domain and HTTPS reverse proxy.')
 host=args.host if args.command=='serve' else '127.0.0.1';port=args.port if args.command=='serve' else 8001
 print(f'Drunken Guide listening on {host}:{port}; mode={"development" if DEV else "production"}',flush=True);ThreadingHTTPServer((host,port),Handler).serve_forever()
if __name__=='__main__':main()
