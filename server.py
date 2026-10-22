import json, os, random, secrets, socket, threading, time, urllib.parse
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path

BASE=Path(__file__).resolve().parent
PORT=int(os.environ.get('PORT',os.environ.get('BADE_PORT','8765')))
ADMIN_PASSWORD=os.environ.get('BADE_ADMIN_PASSWORD','')
if not ADMIN_PASSWORD:
 ADMIN_PASSWORD=secrets.token_urlsafe(18)
 print('UYARI: BADE_ADMIN_PASSWORD ayarlanmadı. Geçici yönetici şifresi:',ADMIN_PASSWORD,flush=True)
LOCK=threading.RLock()
QUESTIONS=[
 {'q':'Aşağıdakilerden hangisi bir isim tamlamasıdır?','a':['Güzel ev','Okul bahçesi','Çok hızlı','Yavaşça yürüdü'],'correct':1},
 {'q':'“Gözleri deniz gibiydi.” cümlesinde hangi söz sanatı vardır?','a':['Benzetme','Kişileştirme','Tezat','Abartma'],'correct':0},
 {'q':'Aşağıdakilerden hangisi bir fiilimsi türüdür?','a':['Zamir','Edat','Sıfat-fiil','Ünlem'],'correct':2},
 {'q':'“Küçük Şeyler” adlı eserin yazarı kimdir?','a':['Namık Kemal','Sami Paşazade Sezai','Halit Ziya Uşaklıgil','Recaizade Mahmut Ekrem'],'correct':1},
 {'q':'“Çalıkuşu” romanının yazarı kimdir?','a':['Reşat Nuri Güntekin','Yakup Kadri Karaosmanoğlu','Peyami Safa','Ahmet Hamdi Tanpınar'],'correct':0},
 {'q':'Aşağıdakilerden hangisi bir edebî akımdır?','a':['Realizm','Mecaz','İkileme','Redif'],'correct':0},
 {'q':'“Karabibik” adlı eserin yazarı kimdir?','a':['Ömer Seyfettin','Nabizade Nâzım','Refik Halit Karay','Hüseyin Rahmi Gürpınar'],'correct':1},
 {'q':'Aşağıdakilerden hangisi zarf görevindedir?','a':['Kırmızı','Güzellik','Dün','Masa'],'correct':2},
 {'q':'Bir şiirde dizelerin sonundaki ses benzerliğine ne denir?','a':['Ölçü','Kafiye','Tema','İmge'],'correct':1},
 {'q':'“Eyvah!” sözcüğünün türü nedir?','a':['Bağlaç','Ünlem','Zamir','Edat'],'correct':1},
]
QUESTION_FILE=BASE/'questions.json'
def load_questions():
 if QUESTION_FILE.exists():
  try:
   data=json.loads(QUESTION_FILE.read_text(encoding='utf-8'))
   if isinstance(data,list) and data:return data
  except (ValueError,OSError):pass
 return [dict(q,topic='Genel') for q in QUESTIONS]
def save_questions(items):
 temp=QUESTION_FILE.with_suffix('.tmp')
 temp.write_text(json.dumps(items,ensure_ascii=False,indent=2),encoding='utf-8')
 temp.replace(QUESTION_FILE)
QUESTIONS=load_questions()
STATE={'pin':str(random.randint(100000,999999)),'host':secrets.token_urlsafe(32),'phase':'lobby','index':-1,'ends':0,'duration':25,'players':{},'questions':QUESTIONS,'answers':{},'round':0,'limit':min(10,len(QUESTIONS))}

def clean(s,n=36):return str(s).strip()[:n]
def current():
 i=STATE['index'];return STATE['questions'][i] if 0<=i<len(STATE['questions']) else None

def snapshot(token=None,host=False,origin=''):
 q=current();phase=STATE['phase'];data={'pin':STATE['pin'],'phase':phase,'index':STATE['index'],'total':STATE['limit'],'duration':STATE['duration'],'ends':STATE['ends'],'players':[{'name':p['name'],'score':p['score'],'answered':p['id'] in STATE['answers']} for p in STATE['players'].values()],
'round':STATE['round'],'topics':sorted({q.get('topic','Genel') for q in load_questions()})}

 if q and phase in ('question','reveal','finished'):
  data['question']={'q':q['q'],'a':q['a']}
  if phase!='question':data['question']['correct']=q['correct']
 if host:
  data['host']=True
  data['joinUrl']=origin or ('http://'+lan_ip()+':'+str(PORT))
  data['answersCount']=len(STATE['answers'])
  data['questionCount']=len(STATE['questions'])
  data['results']=[{'name':p['name'],'choice':STATE['answers'].get(p['id'],{}).get('choice'), 'score':p['score']} for p in STATE['players'].values()]
 if token in STATE['players']:
  p=STATE['players'][token];data['me']={'name':p['name'],'score':p['score'],'answered':token in STATE['answers'],'choice':STATE['answers'].get(token,{}).get('choice')}
 return data

def score_round():
 q=current()
 if not q:return
 for token,ans in STATE['answers'].items():
  if ans['choice']==q['correct'] and token in STATE['players']:
   elapsed=max(0,STATE['duration']-(STATE['ends']-ans['at']))
   points=500+round(500*max(0,1-elapsed/max(1,STATE['duration'])))
   STATE['players'][token]['score']+=points

class Handler(BaseHTTPRequestHandler):
 def public_origin(self):
  # Render reverse proxy provides HTTPS via X-Forwarded-Proto.
  host=self.headers.get('Host','').strip()
  if not host or any(c in host for c in '/\\\r\n'):
   return ''
  proto=self.headers.get('X-Forwarded-Proto','http').split(',')[0].strip()
  return ('https' if proto=='https' else 'http')+'://'+host
 def log_message(self,fmt,*args):pass
 def send(self,obj,code=200):
  body=json.dumps(obj,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Access-Control-Allow-Origin','same-origin');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
 def do_GET(self):
  path=urllib.parse.urlsplit(self.path).path
  if path=='/api/state':
   args=urllib.parse.parse_qs(urllib.parse.urlsplit(self.path).query);token=args.get('token',[''])[0]
   with LOCK:self.send(snapshot(token,token==STATE['host'],self.public_origin()))
   return
  if path in ('/','/index.html'):
   body=(BASE/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Cache-Control','no-store');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
  if path=='/Eski_Tahta_Modu_v1.html':
   body=(BASE/'Eski_Tahta_Modu_v1.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body);return
  self.send({'error':'Bulunamadı'},404)
 def do_POST(self):
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>150000:raise ValueError('İstek çok büyük')
   payload=json.loads(self.rfile.read(n) or b'{}')
   path=urllib.parse.urlsplit(self.path).path
   with LOCK:
    if path=='/api/admin-login':
     if not secrets.compare_digest(str(payload.get('password','')),ADMIN_PASSWORD):raise ValueError('Yönetici şifresi yanlış')
     self.send({'token':STATE['host']});return
    if path=='/api/join':
     if str(payload.get('pin',''))!=STATE['pin']:raise ValueError('Oda kodu yanlış')
     if STATE['phase']!='lobby':raise ValueError('Yarışma başladı, katılım kapalı')
     name=clean(payload.get('name',''))
     if len(name)<2:raise ValueError('En az iki karakterli isim gir')
     if len(STATE['players'])>=150:raise ValueError('Oda dolu')
     if any(p['name'].casefold()==name.casefold() for p in STATE['players'].values()):raise ValueError('Bu isim kullanılıyor')
     token=secrets.token_urlsafe(22);STATE['players'][token]={'id':token,'name':name,'score':0};self.send({'token':token,'name':name});return
    token=payload.get('token','')
    if path=='/api/answer':
     if token not in STATE['players']:raise ValueError('Önce yarışmaya katıl')
     if STATE['phase']!='question' or time.time()>=STATE['ends']:raise ValueError('Cevap süresi doldu')
     if token in STATE['answers']:raise ValueError('Zaten cevapladın')
     choice=payload.get('choice')
     if type(choice)!=int or choice not in range(len(current()['a'])):raise ValueError('Geçersiz seçenek')
     STATE['answers'][token]={'choice':choice,'at':time.time()};self.send({'ok':True});return
    if token!=STATE['host']:raise ValueError('Öğretmen yetkisi gerekli')
    if path=='/api/start':
     if STATE['phase']!='lobby':raise ValueError('Yarışma zaten başladı')
     if not STATE['players']:raise ValueError('Önce en az bir öğrenci katılsın')
     STATE['duration']=max(10,min(120,int(payload.get('duration',60))))
     requested=max(10,min(120,int(payload.get('count',10))))
     topics=payload.get('topics',[])
     if not isinstance(topics,list) or not topics:raise ValueError('En az bir konu seçin')
     pool=[q for q in STATE['questions'] if q.get('topic','Genel') in topics]
     if len(pool)<requested:raise ValueError(f'Seçilen konularda yalnızca {len(pool)} soru var; {requested} soru seçilemez')
     STATE['questions']=random.sample(pool,requested);STATE['selected_topics']=topics;STATE['limit']=requested;STATE['index']=0;STATE['round']+=1;STATE['phase']='question';STATE['ends']=time.time()+STATE['duration'];STATE['answers']={};self.send({'ok':True});return
    if path=='/api/reveal':
     if STATE['phase']!='question':raise ValueError('Açık soru yok')
     STATE['phase']='reveal';score_round();self.send({'ok':True});return
    if path=='/api/next':
     if STATE['phase']!='reveal':raise ValueError('Önce doğru cevabı göster')
     STATE['index']+=1;STATE['answers']={};STATE['round']+=1
     if STATE['index']>=STATE['limit']:STATE['phase']='finished'
     else:STATE['phase']='question';STATE['ends']=time.time()+STATE['duration']
     self.send({'ok':True});return
    if path=='/api/set-count':
     if STATE['phase'] not in ('question','reveal'):raise ValueError('Yarışma devam etmiyor')
     requested=int(payload.get('count',STATE['limit']))
     if requested<10 or requested>120:raise ValueError('Soru sayısı 10–120 arasında olmalı')
     already=STATE['index']+1
     if requested<already:raise ValueError(f'En az {already} soru seçmelisiniz')
     if requested>STATE['limit']:
      used={q.get('source',q['q']) for q in STATE['questions']}
      topics=STATE.get('selected_topics',[])
      pool=[q for q in load_questions() if q.get('topic','Genel') in topics and q.get('source',q['q']) not in used]
      extra=requested-STATE['limit']
      if len(pool)<extra:raise ValueError(f'Yalnızca {len(pool)} ek soru var')
      STATE['questions'].extend(random.sample(pool,extra))
     else:STATE['questions']=STATE['questions'][:requested]
     STATE['limit']=requested;self.send({'ok':True,'count':requested});return
    if path=='/api/reset':
     STATE['phase']='lobby';STATE['index']=-1;STATE['ends']=0;STATE['answers']={};STATE['round']+=1
     STATE['questions']=load_questions();STATE['limit']=min(10,len(STATE['questions']))
     for p in STATE['players'].values():p['score']=0
     self.send({'ok':True});return
    if path=='/api/questions':
     if STATE['phase']!='lobby':raise ValueError('Soruları düzenlemek için lobide ol')
     questions=payload.get('questions')
     if not isinstance(questions,list) or not 1<=len(questions)<=5000:raise ValueError('1–5000 soru yüklenebilir')
     cleaned=[]
     for q in questions:
      opts=q.get('a',q.get('options',[]));correct=q.get('correct')
      if not isinstance(opts,list) or len(opts) not in (4,5) or type(correct)!=int or correct not in range(len(opts)):raise ValueError('Her soru dört veya beş seçenek ve geçerli doğru cevap indeksi içermeli')
      title=clean(q.get('q',q.get('question','')),2500);opts=[clean(x,1000) for x in opts]
      if not title or any(not x for x in opts):raise ValueError('Boş soru veya seçenek olamaz')
      cleaned.append({'q':title,'a':opts,'correct':correct,'topic':clean(q.get('topic','Genel'),100) or 'Genel'})
     STATE['questions']=cleaned;save_questions(cleaned);STATE['limit']=min(10,len(cleaned));self.send({'ok':True,'count':len(cleaned)});return
    raise ValueError('Bilinmeyen işlem')
  except (ValueError,TypeError,KeyError,json.JSONDecodeError) as e:self.send({'error':str(e)},400)
  except Exception as e:self.send({'error':'Sunucu hatası'},500)

def lan_ip():
 try:
  s=socket.socket(socket.AF_INET,socket.SOCK_DGRAM);s.connect(('8.8.8.8',80));ip=s.getsockname()[0];s.close();return ip
 except OSError:return 'BILGISAYAR_IP_ADRESI'
if __name__=='__main__':
 print('\n'+'='*60+'\n BaDe Quiz Arena — CANLI KATILIM\n'+'='*60)
 print('OGRETMEN: http://localhost:%s/?admin=1'%(PORT))
 print('OGRENCILER: http://%s:%s'%(lan_ip(),PORT))
 print('ODA PIN: '+STATE['pin'])
 print('\nBulut sunucuda yayina alindiginda ogrenciler farkli internetlerden baglanabilir.\n')
 ThreadingHTTPServer(('0.0.0.0',PORT),Handler).serve_forever()
