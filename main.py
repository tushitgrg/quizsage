from flask import Flask, redirect, url_for, render_template, request, session
from werkzeug.utils import secure_filename
import requests
import os
import random
from thefuzz import fuzz, process
from authlib.integrations.flask_client import OAuth
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import pytz
indian_timezone = pytz.timezone('Asia/Kolkata')

app = Flask(__name__)
oauth = OAuth(app)

app.secret_key = "1234"
app.config.from_object('config')
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///quizdb.sqlite3"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)
CONF_URL = 'https://accounts.google.com/.well-known/openid-configuration'
def clear_directory(directory_path):
    try:
       
        items = os.listdir(directory_path)
        for item in items:
            item_path = os.path.join(directory_path, item)
            if os.path.isfile(item_path):
                
                os.remove(item_path)
            elif os.path.isdir(item_path):
                
                clear_directory(item_path)
                
                os.rmdir(item_path)
    except Exception as e:
        print(f"Error clearing directory: {e}")
class quizdb(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  userid = db.Column(db.String(100))
  quizid = db.Column(db.String(100))
  quizname = db.Column(db.String(100))
  quizcategory = db.Column(db.String(100))
  timecreated = db.Column(db.String(100))
  def __init__(self,userid,quizid,quizname,quizcategory,timecreated):
    self.userid = userid
    self.quizid = quizid
    self.quizname = quizname
    self.quizcategory = quizcategory
    self.timecreated = timecreated

oauth.register(
    name='google',
    server_metadata_url=CONF_URL,
    client_kwargs={
        'scope': 'openid email profile'
    }
)




def split_list(lst, size):
  return [lst[i:i + size] for i in range(0, len(lst), size)]


def has_numbers(inputString):
  return any(char.isdigit() for char in inputString)

@app.route('/')
def home():
  
  
  try:
    user = session.get('user')
    name = user['name']
  
  except:
    return render_template("upl.html")
  email = user['email']
  email = email.split('@')
  userid = email[0]
  quizes = quizdb.query.filter_by(userid=userid).all()
  quizids = []
  names = []
  timecreated = []
  for quiz in quizes:
    quizids.append(quiz.quizid)
    names.append(quiz.quizname)
    timecreated.append(quiz.timecreated)
  data = zip(names,quizids)
  return render_template("dashboard.html",data=data,uname=name,timecreated=timecreated)

@app.route('/login')
def login():
    redirect_uri = url_for('authorize', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)
  
def create_folder_if_not_exists(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
        
    else:
        pass
@app.route('/check/<quizid>')
def check(quizid):
  quize = quizdb.query.filter_by(quizid=quizid).first()
  
  return redirect(url_for(quize.quizcategory, quizid=quizid))


@app.route('/authorize')
def authorize():
    token = oauth.google.authorize_access_token()
    session['user'] = token['userinfo']
    user = session.get('user')
    email = user['email']
    f = open("users.txt", "r")
    if email in f.read().lower():
      pass
    else:
      f = open("users.txt", "a")
      f.write(f"{email},")
      f.close()
    return redirect('/')


@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect('/')


@app.route('/makequiz', methods=["POST", "GET"])
def index():
  user = session.get('user')
  try:
    name = user['name']
  
  except:
    return render_template("upl.html")
  print(user)

  email = user['email']
  email = email.split('@')
  userid = email[0]
  upload = f"static/uploads/{userid}"
  create_folder_if_not_exists(upload)
  app.config['UPLOAD_FOLDER'] = upload

  if request.method == "POST":
    gensource = request.form.get("gensource")
    qno = request.form["qno"]
    qytype = request.form["qytype"]
    additions = request.form["additions"]
    if gensource == "image":
      files = request.files.getlist('source')
      imagelinks = ""
      for file in files:
        filename = secure_filename(file.filename)
        file.save(
          os.path.join(os.path.abspath(os.path.dirname(__file__)),
                       app.config['UPLOAD_FOLDER'], filename))

        imagelink = "https://quizsage.tushitgarg.com/static/uploads/" + userid + "/"+filename
        imagelinks = imagelinks + imagelink + "@@"
      url = f"https://tushitgarg.pythonanywhere.com/api/{qytype}/{qno}?url={imagelinks}"

    else:

      topic = request.form["source"] + "!!!"
      topic = topic.replace(" ", "!!!")
      url = f"https://tushitgarg.pythonanywhere.com/api/{qytype}/{qno}?url={topic}"
    response5 = requests.get(url)

    data0 = response5.json()
    global questions
    questions = data0['question']
    global answers
    answers = data0['answers']
    f = open("quizfiles/master.txt", "r")
    findquizid = True
    while findquizid == True:
      quizid = random.randint(10000000, 99999999)
      if str(quizid) in f.read():
        continue
      else:
        findquizid = False
    f = open("quizfiles/master.txt", "a")
    f.write(str(quizid) + "#")
    f.close()
    if int(qytype) == 1:
      f = open(f"quizfiles/questions/{str(quizid)}.txt", "w")
      urlpass = "questions"
    else:
      f = open(f"quizfiles/quizzes/{str(quizid)}.txt", "w")
      urlpass = "quizzes"
    f.write(questions + "%%%%" + answers)
    f.close()
    indian_time = datetime.now(indian_timezone)
    formatted_time = indian_time.strftime('%Y-%m-%d %H:%M:%S')
    qz= quizdb(userid,quizid,additions,urlpass,formatted_time)
    db.session.add(qz)
    db.session.commit()
    clear_directory(f"/static/uploads/{userid}/")
    return redirect(url_for(urlpass, quizid=quizid))

  else:
    return render_template("index.html",email=name)


@app.route('/<usr>')
def user(usr):
  return usr


@app.route('/questions/<quizid>')
def questions(quizid):
  quize = quizdb.query.filter_by(quizid=quizid).first()
  quizname = quize.quizname
  f = open(f"quizfiles/questions/{str(quizid)}.txt", "r")
  text = f.read()
  texts = text.split("%%%%")
  questions = texts[0].splitlines()
  answers = texts[1].splitlines()
  cleanquestions = []
  cleananswers = []
  for i in questions:
    if "question" not in i.lower():
      if len(i) >= 1:
        cleanquestions.append(i)
      else:
        pass
  for i in answers:
    if "answer" not in i.lower():
      if len(i) >= 1:
        cleananswers.append(i)
      else:
        pass
  data = zip(cleanquestions, cleananswers)

  return render_template('questions.html', data=data,quizname=quizname )


@app.route('/quizzes/<quizid>')
def quizzes(quizid):
  quize = quizdb.query.filter_by(quizid=quizid).first()
  quizname = quize.quizname
  f = open(f"quizfiles/quizzes/{str(quizid)}.txt", "r")
  text = f.read()
  texts = text.split("%%%%")
  questions = texts[0]
  answers = texts[1]
  cleananswers = []
  finquestions = []
  answerslist = answers.splitlines()
  onquestions = []
  onoptions = []
  for q in answerslist:
    if "answer" in q.lower():
      if has_numbers(q):

        q = q.replace("Answer:", "")
      else:
        q = ""
    else:
      pass

    if len(q) <= 1:
      pass
    else:
      cleananswers.append(q)
  for ques in questions.splitlines():
    if len(ques) < 1:
      pass
    else:
      finquestions.append(ques)
  n = 0
  for i in finquestions:
    if n % 5 == 0:
      onquestions.append(i)
    else:
      onoptions.append(i)
    n += 1
  options = split_list(onoptions, 4)
  data = list(zip(onquestions, options))
  if len(cleananswers) == len(onquestions):
    return render_template('quizzes.html', data=data, quizid=quizid,quizname=quizname)
  else:
    return render_template('error.html')


@app.route('/submitquiz/<quizid>', methods=["POST", "GET"])
def submitquiz(quizid):
  quize = quizdb.query.filter_by(quizid=quizid).first()
  quizname = quize.quizname
  if request.method == "POST":
    f = open(f"quizfiles/quizzes/{str(quizid)}.txt", "r")
    text = f.read()
    texts = text.split("%%%%")
    questions = texts[0]
    answers = texts[1]
    cleananswers = []
    finquestions = []
    answerslist = answers.splitlines()
    onquestions = []
    onoptions = []
    for q in answerslist:
      if "answer" in q.lower():
        if has_numbers(q):

          q = q.replace("Answer:", "")
        else:
          q = ""
      else:
        pass

      if len(q) <= 0:
        pass
      else:
        cleananswers.append(q)
    for ques in questions.splitlines():
      if len(ques) < 1:
        pass
      else:
        finquestions.append(ques)
    n = 0
    for i in finquestions:
      if n % 5 == 0:
        onquestions.append(i)
      else:
        onoptions.append(i)
      n += 1
    if len(cleananswers) == len(onquestions):
      options = split_list(onoptions, 4)
      score = 0
      data = list(zip(onquestions, options))
      correctoptions = []
      useroptions = []
      for i in range(len(cleananswers)):
        cop = process.extract(cleananswers[i],
                              options[i],
                              limit=1,
                              scorer=fuzz.token_sort_ratio)
        useroptions.append(request.form[str(i + 1)])
        copp = cop[0][0]
        correctoptions.append(int(options[i].index(copp)) + 1)
        print(request.form[str(i + 1)])
        if int(options[i].index(copp)) + 1 == int(request.form[str(i + 1)]):
          score += 1

      print(correctoptions)
      return render_template('submitquiz.html',
                             data=data,
                             correctoptions=correctoptions,
                             useroptions=useroptions,
                             score=score,
                             lent=len(cleananswers),quizname=quizname)
    else:
      return render_template('error.html')

if __name__ =="__main__":
  
  with app.app_context():
    db.create_all()
  app.run(host='0.0.0.0', port=81, debug=False)
