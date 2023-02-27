######################################
# author ben lawson <balawson@bu.edu>
# Edited bdy: Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
############################################################################################################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask_login
import hashlib
# Short function to simplify hashing of passwords
def sha256(string): return hashlib.sha256(string.encode()).hexdigest()

#for image uploading
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

#These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'baTQv9$pEd6y*5'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

############################################################################################################################################
#	    LOGIN CODE		 ###################################################################################################################
############################################################################################################################################

login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email from Users")
users = cursor.fetchall()

def getUserList():
	cursor = conn.cursor()
	cursor.execute("SELECT email from Users")
	return cursor.fetchall()

class User(flask_login.UserMixin):
	pass

@login_manager.user_loader
def user_loader(email):
	users = getUserList()
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	return user

@login_manager.request_loader
def request_loader(request):
	users = getUserList()
	email = request.form.get('email')
	if not(email) or email not in str(users):
		return
	user = User()
	user.id = email
	cursor = mysql.connect().cursor()
	cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
	data = cursor.fetchall()
	pwd = str(data[0][0] )
	user.is_authenticated = sha256(request.form['password']) == pwd
	return user


############################################################################################################################################
# HELPER FUNCTIONS FOR GETTING ATTRIBUTES AND OTHER INFO ###################################################################################
############################################################################################################################################

def getCurrentUid():
	return getUserIdFromEmail(flask_login.current_user.id)

# General purpose function that returns all attributes of a specified type in a table relation to a key
def getAttributesByKey(attribute, table, key, id):
	cursor = conn.cursor()
	cursor.execute("SELECT {0} FROM {1} WHERE {2} = '{3}'".format(attribute, table, key, id))
	tuple_list = cursor.fetchall()
	attribute_list = []
	for tuple in tuple_list:
		query = tuple[0]
		attribute_list.append(query)
	return attribute_list

# General purpose function that returns all lists of attributes of a specified type in a table in relation to a series of keys, returns 2d list
def getAttributeByKeylist(attribute, table, key, id_list):
	attribute_list = []
	for id in id_list:
		query = getAttributesByKey(attribute, table, key, id)
		attribute_list.append(query[0])
	return attribute_list

# Function for taking a 2d list and putting all elements in a single list
def D2D(list2):
	return_list = []
	for list in list2:
		for element in list:
			return_list.append(element)
	return return_list

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE user_id = '{0}'".format(uid))
	return cursor.fetchall() #NOTE return a list of tuples, [(imgdata, pid, caption), ...]

def getPhotosByIDs(pids):
	photo_list = []
	for pid in pids:
		cursor = conn.cursor()
		cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id = '{0}'".format(pid))
		photo_list.append(cursor.fetchall)
	photo_list = D2D(photo_list)
	return photo_list

def getAlbumPhotos(aid):
	pids = getAttributesByKey('P_id', 'AlbumPhotos', 'A_id', aid)
	return getPhotosByIDs(pids)	

def getUserAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT A_id, Name FROM Albums WHERE owner_id = '{0}'".format(uid))
	tuples = cursor.fetchall()
	return tuples

def getUsersFriends(uid):
	return getAttributesByKey('frnd_id', 'Friends', 'user_id', uid)

def getUserEmails(uid_list):
	return getAttributeByKeylist('email', 'Users', 'user_id', uid_list)

def getFriendsEmails(uid):
	fids = getUsersFriends(uid)
	friend_emails = getUserEmails(fids)
	return friend_emails

def getUserIdFromEmail(email):
	cursor = conn.cursor()
	cursor.execute("SELECT user_id  FROM Users WHERE email = '{0}'".format(email))
	return cursor.fetchone()[0]

def getFirstNameFromEmail(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT fname  FROM Users WHERE email = '{0}'".format(uid))
	return cursor.fetchone()[0]

def getLastNameFromEmail(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT lname  FROM Users WHERE email = '{0}'".format(uid))
	return cursor.fetchone()[0]

def getFullNameFromEmail(uid):
	return getFirstNameFromEmail(uid) + ' ' + getLastNameFromEmail(uid)

def getAlbumsFromID(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT A_id FROM Albums WHERE Owner_id = '{0}'".format(uid))
	tuple_list = cursor.fetchall
	attribute_list = []
	for tuple in tuple_list:
		attribute = tuple[0]
		attribute_list.append(attribute)
	return attribute_list

def isEmailUnique(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return False
	else:
		return True
	
def isEmailRegistered(email):
	#use this to check if a email has already been registered
	cursor = conn.cursor()
	if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
		#this means there are greater than zero entries with that email
		return True
	else:
		return False
	
def doesAlbumExist(album_name, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Albums WHERE Name = '{0}' AND Owner_id = '{1}'".format(album_name, uid)):
		return True
	else:
		return False

############################################################################################################################################
# 	NAVIGATION AND FUNCTIONAL CODE	 #######################################################################################################
############################################################################################################################################

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
			   <form action='login' method='POST'>
				<input type='text' name='email' id='email' placeholder='email'></input>
				<input type='password' name='password' id='password' placeholder='password'></input>
				<input type='submit' name='submit'></input>
			   </form></br>
		   <a href='/'>Home</a>
			   '''
	#The request method is POST (page is recieving data)
	email = flask.request.form['email']
	cursor = conn.cursor()
	#check if email is registered
	if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
		data = cursor.fetchall()
		pwd = str(data[0][0] )
		if sha256(flask.request.form['password']) == pwd:
			user = User()
			user.id = email
			flask_login.login_user(user) #okay login in user
			return flask.redirect(flask.url_for('protected')) #protected is a function defined in this file

	#information did not match
	return "<a href='/login'>Try again</a>\
			</br><a href='/register'>or make an account</a>"

@app.route('/logout')
def logout():
	flask_login.logout_user()
	return render_template('hello.html', message='Logged out')

@login_manager.unauthorized_handler
def unauthorized_handler():
	return render_template('unauth.html')

############################################################################################################################################

@app.route("/register", methods=['GET'])
def register():
	return render_template('register.html', supress='True')

@app.route("/register", methods=['POST'])
def register_user():
	try:
		email = request.form.get('email')
		password = request.form.get('password')
		fname = request.form.get('fname')
		lname = request.form.get('lname')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, fname, lname) VALUES ('{0}', '{1}', '{2}', '{3}')".format(email, sha256(password), fname, lname)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=getFullNameFromEmail(flask_login.current_user.id), message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))
	
###########################################################################################################################################

@app.route('/albums')
@flask_login.login_required
def myalbums():
	uid = getCurrentUid()
	return render_template('albums.html', name=getFullNameFromEmail(flask_login.current_user.id),
			albums=getUserAlbums(uid))

# Add album route
@app.route('/addalbum')
@flask_login.login_required
def addalbum():
	return render_template('addalbum.html', name=getFullNameFromEmail(flask_login.current_user.id), message="Create a new album!")

@app.route("/addalbum", methods=['POST'])
def add_album():
	try:
		new_album_name = request.form.get('album_name')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('hello'))
	cursor = conn.cursor()
	uid = getCurrentUid()
	test = doesAlbumExist(new_album_name, uid)
	if test == False:
		print(cursor.execute("INSERT INTO Albums (Name, Owner_id) VALUES ('{0}', '{1}')".format(new_album_name, uid)))
		conn.commit()
		return render_template('albums.html', name=getFullNameFromEmail(flask_login.current_user.id), 
				message='Album Created!', albums=getUserAlbums(uid))
	else:
		print("couldn't find all tokens")
		return render_template('addalbum.html', name=getFullNameFromEmail(flask_login.current_user.id), 
				message="Please input a unique album name!")

###########################################################################################################################################

@app.route('/photos')
@flask_login.login_required
def photos():
	return render_template('photos.html', name=getFullNameFromEmail(flask_login.current_user.id), 
			photos=getUsersPhotos(getCurrentUid()), base64=base64)

###########################################################################################################################################

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=getFullNameFromEmail(flask_login.current_user.id), message="Here's your profile")

###########################################################################################################################################

# Friends page route
@app.route('/friends')
@flask_login.login_required
def friend():
	friend_emails = getFriendsEmails(getCurrentUid())
	return render_template('friends.html', name=getFullNameFromEmail(flask_login.current_user.id), friends=friend_emails)

# Add friend route
@app.route('/addfriend')
@flask_login.login_required
def addfriend():
	return render_template('addfriend.html', name=getFullNameFromEmail(flask_login.current_user.id), message="Add a friend!")

@app.route("/addfriend", methods=['POST'])
def add_friend():
	try:
		friend_email=request.form.get('friend_email')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('hello'))
	cursor = conn.cursor() 
	test =  isEmailRegistered(friend_email)	
	if test:
		fid = getUserIdFromEmail(friend_email)
		uid = getCurrentUid()
		print(cursor.execute("INSERT INTO Friends (user_id, frnd_id) VALUES ('{0}', '{1}')".format(uid, fid)))
		conn.commit()
		friend_emails = getFriendsEmails(getCurrentUid())
		return render_template('friends.html', name=getFullNameFromEmail(flask_login.current_user.id), message='Friend Added!', friends=friend_emails)
	else:
		print("couldn't find all tokens")
		return render_template('addfriend.html', name=getFullNameFromEmail(flask_login.current_user.id), message="User not found, please try again.")

###########################################################################################################################################

# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])
def allowed_file(filename):
	return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
	if request.method == 'POST':
		uid = getCurrentUid()
		imgfile = request.files['photo']
		caption = request.form.get('caption')
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption) VALUES (%s, %s, %s )''', (photo_data, uid, caption))
		conn.commit()
		return render_template('hello.html', name=getFullNameFromEmail(flask_login.current_user.id), message='Photo uploaded!', photos=getUsersPhotos(uid), base64=base64)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

###########################################################################################################################################

#default page
@app.route("/", methods=['GET'])
def hello():
	return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
