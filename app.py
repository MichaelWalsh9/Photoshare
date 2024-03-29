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

def getCurrentName():
	return getFullNameFromEmail(flask_login.current_user.id)

###########################################################################################################################################

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

def delAttributeByKey(table, key, id):
	cursor = conn.cursor()
	cursor.execute("DELETE FROM {0} WHERE {1} = '{2}'".format(table, key, id))
	conn.commit()

# Function for taking a 2d list and putting all elements in a single list
def D2D(list2):
	return_list = []
	for list in list2:
		for element in list:
			return_list.append(element)
	return return_list

# Takes a list and returns a sorted list of tuples consisting of each unique element of the list and the number of its appearances
def Reduce(list):
	tuplelist = []
	for unique in list:
		tally = 0
		for element in list:
			if element == unique:
				tally += 1
		tuplelist.append((tally, unique))
	tuplelist = [*set(tuplelist)]
	tuplelist = descendSortTuples(tuplelist)
	return tuplelist

# Removes all occurences of a value in a list
def RemoveValue(list, value):
	return [i for i in list if i != value]

###########################################################################################################################################

# Returns a list of all tags
def getAllTags():
	cursor = conn.cursor()
	cursor.execute("SELECT Word FROM Tags")
	tagtuples = cursor.fetchall()
	taglist = []
	for tuple in tagtuples:
		tag = tuple[0]
		taglist.append(tag)
	return taglist

# Returns a list of all photo ids with a given tag
def getAllPhotosbyTag(tag):
	return getAttributesByKey('p_id', 'TaggedWith', 'tag', tag)

# Returns a list of all photo ids with a given tag owned by a user with a given uid
def getUserPhotosbyTag(tag, uid):
	allphotos = getAllPhotosbyTag(tag)
	userphotos = []
	for pid in allphotos:
		cursor = conn.cursor()
		cursor.execute("SELECT picture_id FROM Pictures WHERE picture_id = '{0}' AND user_id = '{1}'".format(pid, uid))
		result = cursor.fetchone()
		if result != None:
			userphotos.append(result[0])
	return userphotos

def getTagScore(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(tag) FROM TaggedWith WHERE tag = '{0}'".format(tag))
	tagscore = cursor.fetchone()[0]
	return tagscore

def getSuggestedTags(uid):
	pids = getUsersPhotos(uid)
	rawtags = []
	for pid in pids:
		tags = getAttributesByKey('tag', 'TaggedWith', 'p_id', pid)
		rawtags.append(tags)
	rankedtags = Rank(rawtags)
	return rankedtags[:3]

# Returns the number of tags associated with a particular photo
def getNumTags(pid):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(tag) FROM TaggedWith WHERE p_id = '{0}'".format(pid))
	numtags = cursor.fetchone()[0]
	return numtags

def getTagsonPhoto(pid):
	return getAttributesByKey('tag', 'TaggedWith', 'p_id', pid)

###########################################################################################################################################

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT picture_id FROM Pictures WHERE user_id = '{0}'".format(uid))
	return D2D(cursor.fetchall()) 

def getPhotosByIDs(pids):
	photo_list = []
	for pid in pids:
		cursor = conn.cursor()
		cursor.execute("SELECT imgdata, picture_id, caption FROM Pictures WHERE picture_id = '{0}'".format(pid))
		photo_list.append(cursor.fetchall())
	photo_list = D2D(photo_list)
	photoswithlikes = []
	for tuple in photo_list:
		cursor = conn.cursor()
		cursor.execute("SELECT COUNT(u_id) FROM LikesPhoto WHERE p_id = '{0}'".format(tuple[1]))
		newtuple = tuple + (str(cursor.fetchone()[0]),)
		photoswithlikes.append(newtuple)
	return photoswithlikes

def getAlbumPhotos(aid):
	pids = getAttributesByKey('P_id', 'AlbumPhotos', 'A_id', aid)
	return getPhotosByIDs(pids)

def purgePhoto(pid):
	delAttributeByKey('Comments', 'p_id', pid)
	delAttributeByKey('Pictures', 'picture_id', pid)

###########################################################################################################################################


def getUserAlbums(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT A_id, Name FROM Albums WHERE owner_id = '{0}'".format(uid))
	tuples = cursor.fetchall()
	return tuples

def getAllAlbums():
	cursor = conn.cursor()
	cursor.execute("SELECT A_id, Name, owner_id FROM Albums")
	tuples = cursor.fetchall()
	return tuples

def getAlbumIDFromName(aname, uid):
	cursor=conn.cursor()
	cursor.execute("SELECT A_id FROM Albums WHERE Name = '{0}' AND Owner_id = '{1}'".format(aname, uid))
	return cursor.fetchone()[0]

def getAlbumNameFromID(aid):
	return getAttributesByKey('Name', 'Albums', 'A_id', aid)

def purgeAlbum(aid):
	# First find all photos associated with this album
	pids = getAttributesByKey('P_id', 'AlbumPhotos', 'A_id', aid)
	# Then, delete all of these photos
	for pid in pids:
		delAttributeByKey('AlbumPhotos', 'P_id', pid)
		purgePhoto(pid)
	# Finally, detele the album itself
	delAttributeByKey('Albums', 'A_id', aid)

###########################################################################################################################################

def getCommentsbyPhoto(pid):
	cursor = conn.cursor()
	cursor.execute("SELECT c_id, text, owner_id FROM Comments WHERE p_id = '{0}'".format(pid))
	return cursor.fetchall()

def getCommentListwithNames(commentslist):
	commentemaillist = []
	for comment in commentslist:
		if comment[2] == None:
			commentemaillist.append(['Guest'])
		else:
			commentemaillist.append(getEmailFromUserID(comment[2]))
	commentemaillist = D2D(commentemaillist)

	commentslistfinal = []	
	for i in range(len(commentemaillist)):
		newtuple = (commentslist[i][0], commentslist[i][1], commentemaillist[i])
		commentslistfinal.append(newtuple)
	return commentslistfinal

# Return a list of uids associated with each comment that shares the specified text
def getCommentUsersbyText(text):
	return getAttributesByKey('owner_id', 'Comments', 'text', text)


def getLikesOnPhoto(pid):
	uids = getAttributesByKey('u_id', 'LikesPhoto', 'p_id', pid)
	names = []
	for uid in uids:
		name = getFullNameFromEmail(getEmailFromUserID(uid)[0])
		names.append(name)
	names = names
	return names

###########################################################################################################################################

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

def getEmailFromUserID(uid):
	return getAttributesByKey('email', 'Users', 'user_id', uid)

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

def getAllUIDs():
	cursor = conn.cursor()
	cursor.execute("SELECT user_id FROM Users")
	uids = cursor.fetchall()
	return uids

def getUserScore(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(picture_id) FROM Pictures WHERE user_id = '{0}'".format(uid))
	pscore = cursor.fetchone()[0]
	cursor.execute("SELECT COUNT(c_id) FROM Comments WHERE owner_id = '{0}'".format(uid))
	cscore = cursor.fetchone()[0]
	pids = getUsersPhotos(uid)
	dock = 0
	for pid in pids:
		cursor.execute("SELECT COUNT(c_id) FROM Comments WHERE owner_id = '{0}' AND p_id = '{1}'".format(uid, pid))
		dock = dock + (cursor.fetchone()[0])
	return pscore + (cscore - dock)

def getTopUserListInfo(uids):
	alluscores = []
	for uid in uids:
		alluscores.append(getUserScore(uid))
	alluemails = []
	for uid in uids:
		alluemails.append(getEmailFromUserID(uid))
	alluemails = D2D(alluemails)
	allunames = []
	for email in alluemails:
		allunames.append(getFullNameFromEmail(email))
	userlist = []
	for i in range(len(uids)):
		usertuple = (alluscores[i], uids[i], alluemails[i], allunames[i])
		userlist.append(usertuple)
	return userlist

def getCommentUserListInfo(inputtuples):
	uscores = []
	uids = []
	for tuple in inputtuples:
		uscores.append(tuple[0])
		uids.append(tuple[1])
	uemails = []
	for uid in uids:
		uemails.append(getEmailFromUserID(uid))
	uemails = D2D(uemails)
	unames = []
	for email in uemails:
		unames.append(getFullNameFromEmail(email))
	userlist = []
	for i in range(len(inputtuples)):
		usertuple = (uscores[i], uids[i], uemails[i], unames[i])
		userlist.append(usertuple)
	return userlist

###########################################################################################################################################

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
	
def doesMyAlbumExist(album_name, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Albums WHERE Name = '{0}' AND Owner_id = '{1}'".format(album_name, uid)):
		return True
	else:
		return False
	
def hasUserLikedPhoto(pid, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM LikesPhoto WHERE p_id = '{0}' AND u_id = '{1}'".format(pid, uid)):
		return True
	else:
		return False 

def tagExists(tag):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Tags WHERE Word = '{0}'".format(tag)):
		return True
	else:
		return False
	
###########################################################################################################################################

# Function for sorting tuples or lists by value of their first element in descending order
def descendSortTuples(list):
	if len(list) < 2:
		return list
	low, same, high = [], [], []
	pivot = list[1][0]
	for element in list:
		if element[0] > pivot:
			low.append(element)
		elif element[0] == pivot:
			same.append(element)
		elif element[0] < pivot:
			high.append(element)
	return descendSortTuples(low) + same + descendSortTuples(high)

# Function for sorting tuples or lists by value of their first element in descending order
def ascendSortTuples(list):
	if len(list) < 2:
		return list
	low, same, high = [], [], []
	pivot = list[1][0]
	for element in list:
		if element[0] < pivot:
			low.append(element)
		elif element[0] == pivot:
			same.append(element)
		elif element[0] > pivot:
			high.append(element)
	return ascendSortTuples(low) + same + ascendSortTuples(high)

# Takes a 2D-list, returns a sorted list of tuples (r, e) where r is the number of times e appears across the entire 2D list for each element e
def Rank(list):
	return descendSortTuples(Reduce(D2D(list)))

def ReverseRank(list):
	return ascendSortTuples(Reduce(D2D(list)))

# Takes a tuple list generated by Rank() and returns the maximum rank score 
def getMaxRank(tuplelist):
	return (tuplelist[0][0])

############################################################################################################################################
# 	NAVIGATION AND FUNCTIONAL CODE	 #######################################################################################################
############################################################################################################################################

@app.route('/login', methods=['GET', 'POST'])
def login():
	if flask.request.method == 'GET':
		return '''
				<style>
					form  { display: table;      }
					p     { display: table-row;  }
					label { display: table-cell; }
					input { display: table-cell; }
					body {
						background-color: rgb(60, 60, 60);
					}
					h1, h2, h3, h4, li, b, p, label {
						color: antiquewhite;
					}
					a {
						color: orange;
					}
					input[type=button], input[type=submit] {
						background-color: orange;
						color: antiquewhite;
						border: antiquewhite;
						padding: 10px 10px;
						text-shadow: 0 0 2px rgb(60, 60, 60);
					}
					img {
					border : 4px solid antiquewhite;
					max-width: 20%;
					max-height: 20%;
					}
				</style>
			   <form action='login' method='POST'>
			   	<p>
				   <label for="email">Enter your email:</label>
					<input type='text' name='email' id='email' placeholder='email'></input>
				</p>
				<p>
					<label for="password">Enter your password:</label>
					<input type='password' name='password' id='password' placeholder='password'></input>
				</p>
				<p>
					<input type='submit' name='submit'></input>
				</p>
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
		dob = request.form.get('dob')
		hometown = request.form.get('hometown')
		gender = request.form.get('gender')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('register'))
	cursor = conn.cursor()
	test =  isEmailUnique(email)
	if test:
		print(cursor.execute("INSERT INTO Users (email, password, fname, lname, dob, hometown, gender) VALUES ('{0}', '{1}', '{2}', '{3}', '{4}', '{5}', '{6}')".format(email, 
																				  sha256(password), fname, lname, dob, hometown, gender)))
		conn.commit()
		#log user in
		user = User()
		user.id = email
		flask_login.login_user(user)
		return render_template('hello.html', name=getCurrentName(), message='Account Created!')
	else:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('register'))
	
###########################################################################################################################################

@app.route('/albums')
@flask_login.login_required
def myalbums():
	uid = getCurrentUid()
	return render_template('albums.html', name=getCurrentName(),
			albums=getUserAlbums(uid))

@app.route('/albums', methods=['POST'])
@flask_login.login_required
def my_albums():
	uid = getCurrentUid()
	try:
		target_album = request.form.get('album_edit')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	return render_template('photos.html', name=getCurrentName(), photos=getAlbumPhotos(target_album), 
			base64=base64, album_name = getAlbumNameFromID(target_album), can_edit=True)

# Add album route
@app.route('/addalbum')
@flask_login.login_required
def addalbum():
	return render_template('addalbum.html', name=getCurrentName(), message="Create a new album!")

@app.route("/addalbum", methods=['POST'])
def add_album():
	try:
		new_album_name = request.form.get('album_name')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('hello'))
	cursor = conn.cursor()
	uid = getCurrentUid()
	test = doesMyAlbumExist(new_album_name, uid)
	if test == False:
		print(cursor.execute("INSERT INTO Albums (Name, Owner_id) VALUES ('{0}', '{1}')".format(new_album_name, uid)))
		conn.commit()
		return render_template('albums.html', name=getCurrentName(), 
				message='Album Created!', albums=getUserAlbums(uid))
	else:
		print("couldn't find all tokens")
		return render_template('addalbum.html', name=getCurrentName(), 
				message="Please input a unique album name!", albums=getUserAlbums(uid))
	
# Remove album route
@app.route('/remalbum')
@flask_login.login_required
def remalbum():
	return render_template('remalbum.html', name=getCurrentName())

@app.route("/remalbum", methods=['POST'])
def rem_album():
	try:
		targeted_album_name = request.form.get('remove_album_name')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('hello'))
	uid = getCurrentUid()
	test = doesMyAlbumExist(targeted_album_name, uid)
	if test:
		aid = getAlbumIDFromName(targeted_album_name, uid)
		purgeAlbum(aid)
		return render_template('albums.html', name=getCurrentName(), 
				message='Album Deleted!', albums=getUserAlbums(uid))
	else:
		print("couldn't find all tokens")
		return render_template('remalbum.html', name=getCurrentName(), 
				message="Please input a valid album name!", albums=getUserAlbums(uid))

###########################################################################################################################################

# Deprecated
@app.route('/photos')
@flask_login.login_required
def photos():
	return render_template('photos.html', name=getCurrentName(), 
			photos=getUsersPhotos(getCurrentUid()), base64=base64)

@app.route('/photos', methods=['POST'])
def view_comments():
	try:
		target_photo = request.form.get('photoid')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	try:
		iscomments = request.form.get('iscomments')
	except:
		iscomments = "False"
	try:
		delete = request.form.get('delphoto')
	except:
		delete = "False"
	if (iscomments == "True"):
		commentslist = getCommentListwithNames(getCommentsbyPhoto(target_photo))
		photodata = getPhotosByIDs([target_photo])[0]
		return render_template('comments.html', comments=commentslist, likes=getLikesOnPhoto(target_photo), tags=getTagsonPhoto(target_photo) ,photo=photodata, base64=base64)
	elif (delete == "True"):
		AlbumList = getAllAlbums()
		AlbumNameList = []
		for album in AlbumList:
			email = getEmailFromUserID(album[2])
			email = email[0]
			AlbumNameList.append(album + (getFullNameFromEmail(email),))
		purgePhoto(target_photo)
		return render_template('allalbums.html', albums=AlbumNameList)
	else:
		AlbumList = getAllAlbums()
		AlbumNameList = []
		for album in AlbumList:
			email = getEmailFromUserID(album[2])
			email = email[0]
			AlbumNameList.append(album + (getFullNameFromEmail(email),))
		try: 
			uid = getCurrentUid()
		except:
			return render_template('register.html', supress='True', message="You must create an account to like photos")
		
		owner = getAttributesByKey('user_id', 'Pictures', 'picture_id', target_photo)[0]
		print("owner: ", owner)
		print("uid: ", uid)
		if (uid == owner):
			return render_template('allalbums.html', albums=AlbumNameList, message="You cannot like your own photos, narcissist")			
		if (hasUserLikedPhoto(target_photo, uid) == False):
			# User likes photo
			cursor = conn.cursor()
			print(cursor.execute("INSERT INTO LikesPhoto (p_id, u_id) VALUES ('{0}', '{1}')".format(target_photo, uid)))
			conn.commit()
			return render_template('allalbums.html', albums=AlbumNameList)
		else:
			# User unlikes photo
			cursor = conn.cursor()
			print(cursor.execute("DELETE FROM LikesPhoto WHERE p_id = '{0}' AND u_id = '{1}'".format(target_photo, uid)))
			conn.commit()
			return render_template('allalbums.html', albums=AlbumNameList)

@app.route('/photos', methods=['POST'])
@flask_login.login_required
def like_photo():
	try:
		target_photo = request.form.get('like_photo')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	AlbumList = getAllAlbums()
	AlbumNameList = []
	for album in AlbumList:
		email = getEmailFromUserID(album[2])
		email = email[0]
		AlbumNameList.append(album + (getFullNameFromEmail(email),))
	uid = getCurrentUid()
	owner = getAttributesByKey('user_id', 'Pictures', 'picture_id', target_photo)
	print("owner: ", owner)
	print("uid: ", uid)
	if (uid == owner):
		return render_template('allalbums.html', albums=AlbumNameList) 
	if hasUserLikedPhoto():
		# User likes photo
		cursor = conn.cursor()
		print(cursor.execute("INSERT INTO LikesPhoto (p_id, u_id) VALUES ('{0}', '{1}')".format(target_photo, uid)))
		conn.commit()
		return render_template('allalbums.html', albums=AlbumNameList)
	else:
		# User unlikes photo
		cursor = conn.cursor()
		print(cursor.execute("DETEL FROM LikesPhoto WHERE u_id = '{0}' AND p_id = '{1}'".format(target_photo, uid)))
		conn.commit()
		return render_template('allalbums.html', albums=AlbumNameList)


###########################################################################################################################################

# Deprecated
@app.route('/comments')
def comments():
	return render_template('comments.html', name=getCurrentName())

@app.route('/comments', methods=['POST'])
def leave_comments():
	try:
		usercomment = request.form.get('leave_comment')
		commentphoto = request.form.get('comment_photo')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	cursor = conn.cursor()
	message = "You cannot comment on your own photos"
	try:
		# For logged in Users
		uid = getCurrentUid()
		owner = getAttributesByKey('user_id', 'Pictures', 'picture_id', commentphoto)[0]
		print("owner: ", owner)
		print("uid: ", uid)
		if (uid != owner):
			print(cursor.execute("INSERT INTO Comments (text, p_id, owner_id) VALUES ('{0}', '{1}', '{2}')".format(usercomment, commentphoto, uid)))
			message = "Your comment has been added to the thread"
	except:
		# For guests
		print(cursor.execute("INSERT INTO Comments (text, p_id) VALUES ('{0}', '{1}')".format(usercomment, commentphoto)))
		message = "Your comment has been added to the thread"
		
	conn.commit()

	commentslist = getCommentListwithNames(getCommentsbyPhoto(commentphoto)) 	
	
	photodata = getPhotosByIDs([commentphoto])[0]

	return render_template('comments.html', comments=commentslist, likes=getLikesOnPhoto(commentphoto), 
			photo=photodata, message=message, base64=base64)


###########################################################################################################################################

@app.route('/allalbums')
def allalbums():
	AlbumList = getAllAlbums()
	AlbumNameList = []
	for album in AlbumList:
		email = getEmailFromUserID(album[2])
		email = email[0]
		AlbumNameList.append(album + (getFullNameFromEmail(email),))
	return render_template('allalbums.html', albums=AlbumNameList)

@app.route('/allalbums', methods=['POST'])
def all_albums():
	try:
		target_album = request.form.get('album_view')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	target_name = getAlbumNameFromID(target_album)
	return render_template('photos.html', photos=getAlbumPhotos(target_album), 
			base64=base64, album_name = target_name)

###########################################################################################################################################

@app.route("/toptags")
def toptags():
	alltags = getAllTags()
	scoredtags = []
	for tag in alltags:
		score = getTagScore(tag)
		scoredtags.append((score, tag))
	sortedscores = descendSortTuples(scoredtags)
	topscores = sortedscores[:3]
	return render_template('toptags.html', taglist=topscores)

@app.route('/alltagsearch')
def alltagsearch():
	alltags = getAllTags()
	return render_template('alltagsearch.html', taglist=alltags)

@app.route('/alltagsearch', methods=['POST'])
def alltag_search():
	try:
		tag = request.form.get('tag')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	pids = getAllPhotosbyTag(tag)
	photolist = getPhotosByIDs(pids)	
	return render_template('photos.html', photos=photolist, album_name = [tag], base64=base64)

@app.route('/privatetagsearch')
@flask_login.login_required
def privatetagsearch():
	alltags = getAllTags()
	return render_template('privatetagsearch.html', taglist=alltags)

@app.route('/privatetagsearch', methods=['POST'])
def privatetag_search():
	try:
		tag = request.form.get('ptag')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	pids = getUserPhotosbyTag(tag, getCurrentUid())
	photolist = getPhotosByIDs(pids)	
	return render_template('photos.html', photos=photolist, album_name = [tag], base64=base64)

@app.route('/photosearch')
def photosearch():
	tags = getAllTags()
	return render_template('photosearch.html', taglist=tags)

@app.route('/photosearch', methods=['POST'])
def photo_search():
	try:
		search = request.form.get('search_photo')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	tags = (search.lower()).split()
	photo_ids = []
	for tag in tags:
		photo_ids.append(getAllPhotosbyTag(tag))
	reduced = Rank(photo_ids)
	pids = []
	for tuple in reduced:
		if tuple[0] == len(tags):
			pids.append(tuple[1])
	photolist = getPhotosByIDs(pids)
	return render_template('photos.html', name=getCurrentName(), photos=photolist, 
			 base64=base64, album_name = [search])

@app.route('/suggestedphotos')
def suggestedphotos():
	uid = getCurrentUid()
	tags = getSuggestedTags(uid)
	allphoto_ids = []
	userphoto_ids = []
	for tag in tags:
		allphoto_ids.append(getAllPhotosbyTag(tag[1]))
		userphoto_ids.append(getUserPhotosbyTag(tag[1], uid))
	allphoto_ids = D2D(allphoto_ids)
	userphoto_ids = D2D(userphoto_ids)
	for pid in userphoto_ids:
		allphoto_ids = RemoveValue(allphoto_ids, pid)
	reduced = Rank([allphoto_ids])
	pids = []
	print("reduced: ", reduced)
	print("MaxRank: ", getMaxRank(reduced))
	for i in range(getMaxRank(reduced) + 1):
		cohort = [] # Contains a list of all tuples of all pids of the same rank, preceded by the number of tags associated with them
		for tuple in reduced:
			if tuple[0] == i:
				cohort.append((getNumTags(tuple[1]), tuple[1]))
		print("cohort: ", cohort)
		sorted = ascendSortTuples(cohort)
		print("sorted: ", sorted)
		for tuple in sorted:
			pids.append(tuple[1])
	print("pids: ", pids)
	photolist = getPhotosByIDs(pids)
	return render_template('photos.html', name=getCurrentName(), photos=photolist, 
			 base64=base64, album_name = ["you!"])


###########################################################################################################################################

@app.route('/profile')
@flask_login.login_required
def protected():
	return render_template('hello.html', name=getCurrentName(), message="Here's your profile")

###########################################################################################################################################

# Friends page route
@app.route('/friends')
@flask_login.login_required
def friend():
	friend_emails = getFriendsEmails(getCurrentUid())
	friend_names = []
	for email in friend_emails:
		friend_names.append(getFullNameFromEmail(email))
	friendlist = []
	for i in range(len(friend_emails)):
		friendlist.append((friend_names[i], friend_emails[i]))
	return render_template('friends.html', name=getCurrentName(), friends=friendlist)

# Add friend route
@app.route('/addfriend')
@flask_login.login_required
def addfriend():
	uid = getCurrentUid()
	friendslist = getUsersFriends(uid)
	fof = []
	for friend in friendslist:
		friendoffriend = getUsersFriends(friend)
		fof.append(friendoffriend)
	reduced = Rank(fof)
	userlist = []
	for tuple in reduced: 
		userlist.append((tuple[0], tuple[1], getEmailFromUserID(tuple[1])[0], getFullNameFromEmail(getEmailFromUserID(tuple[1])[0])))
	return render_template('addfriend.html', name=getCurrentName(), users=userlist, 
			listwording=" is reccomended because you have this many mutual friends: ")

@app.route("/addfriend", methods=['POST'])
@flask_login.login_required
def add_friend():
	try:
		friend_email=request.form.get('friend_email')
	except:
		print("couldn't find all tokens") #this prints to shell, end users will not see this (all print statements go to shell)
		return flask.redirect(flask.url_for('hello'))
	test =  isEmailRegistered(friend_email)	
	if test:
		fid = getUserIdFromEmail(friend_email)
		uid = getCurrentUid()
		friends = getUsersFriends(uid)
		if fid not in friends:
			cursor = conn.cursor() 
			print(cursor.execute("INSERT INTO Friends (user_id, frnd_id) VALUES ('{0}', '{1}')".format(uid, fid)))
			conn.commit()
		friend_emails = getFriendsEmails(getCurrentUid())
		friend_names = []
		for email in friend_emails:
			friend_names.append(getFullNameFromEmail(email))
		friendlist = []
		for i in range(len(friend_emails)):
			friendlist.append((friend_names[i], friend_emails[i]))
		return render_template('friends.html', name=getCurrentName(), friends=friendlist)
	else:
		print("couldn't find all tokens")
		return render_template('addfriend.html', name=getCurrentName(), message="User not found, please try again.")
	
###########################################################################################################################################

@app.route("/topusers")
def topusers():
	alluids = getAllUIDs()
	alluids = alluids[:9]
	alluids = D2D(alluids)
	top_users = getTopUserListInfo(alluids)
	top_users = descendSortTuples(top_users)
	return render_template('userlist.html', users=top_users, listwording=" has a contribution score of ")

@app.route("/searchcomments")
def searchcomments():
	return render_template('searchcomments.html')

@app.route("/searchcomments", methods=['POST'])
def search_comments():
	try:
		searchterm = request.form.get('search_comments')
	except:
		print("couldn't find all tokens")
		return flask.redirect(flask.url_for('hello'))
	cuids = getCommentUsersbyText(searchterm)
	cuids = RemoveValue(cuids, None)
	reduced = Reduce(cuids)
	userlist = getCommentUserListInfo(reduced)
	return render_template('userlist.html', users=userlist, listwording=", number of times commented: ", term=searchterm)

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
		target_album_name = request.form.get('asalbum')
		if doesMyAlbumExist(target_album_name, uid) == False:
			return render_template('upload.html', message="Please input a valid album name.")
		aid = getAlbumIDFromName(target_album_name, uid)
		photo_data =imgfile.read()
		cursor = conn.cursor()
		cursor.execute('''INSERT INTO Pictures (imgdata, user_id, caption) VALUES (%s, %s, %s )''', (photo_data, uid, caption))
		conn.commit()
		pid = cursor.lastrowid
		cursor.execute('''INSERT INTO AlbumPhotos (A_id, P_id) VALUES (%s, %s)''', (aid, pid))
		conn.commit()
		try:
			tags = request.form.get('tags')
		except:
			return render_template('photos.html', name=getCurrentName(), photos=getAlbumPhotos(aid), 
			 base64=base64, album_name = [target_album_name], can_edit=True)
		tags = tags.lower()
		taglist = tags.split()
		for tag in taglist:
			if tagExists(tag):
				print('''INSERT INTO TaggedWith (tag, p_id) VALUES (%s, %s)''', (tag, pid))
				cursor.execute('''INSERT INTO TaggedWith (tag, p_id) VALUES (%s, %s)''', (tag, pid))
				conn.commit()
			else:
				cursor.execute('''INSERT INTO Tags (Word) VALUES (%s)''', (tag))
				conn.commit()
				cursor.execute('''INSERT INTO TaggedWith (tag, p_id) VALUES (%s, %s)''', (tag, pid))
				conn.commit()
		return render_template('photos.html', name=getCurrentName(), photos=getAlbumPhotos(aid), 
			 base64=base64, album_name = [target_album_name], can_edit=True)
	#The method is GET so we return a  HTML form to upload the a photo.
	else:
		return render_template('upload.html')
#end photo uploading code

###########################################################################################################################################

#default page
@app.route("/", methods=['GET'])
def hello():
	try:
		return render_template('hello.html', message='Welecome to Photoshare', name=getCurrentName())
	except:
		return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
	#this is invoked when in the shell  you run
	#$ python app.py
	app.run(port=5000, debug=True)
