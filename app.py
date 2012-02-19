from flask import Flask, render_template, session, url_for, redirect, request, flash, make_response
import config
import oauth2 as oauth
import redis
import urlparse
from urllib import urlencode
import redis
import json

app = Flask(__name__)
app.secret_key = config.consumer_key
app.consumer = oauth.Consumer(key=config.consumer_key, secret=config.consumer_secret)
app.cache = redis.StrictRedis(
	host='localhost',
	port=6379,
	db=0)


def verify_response(resp):
	if resp['status'] != '200':
		session.pop('request_token', None)
		flash('Bad response from Twitter: {0}'.format(resp))
		return redirect(url_for('index'))
	else:
		return None


@app.route('/', methods=['GET',])
def index():
	if 'request_token' in session:
		auth_token = oauth.Token(session['request_token']['oauth_token'],
			session['request_token']['oauth_token_secret'])

		client = oauth.Client(app.consumer, auth_token)
		resp, content = client.request(config.auth_url+'access_token', 'GET')
		
		verify_response(resp)
		
		session['access_token'] = dict(urlparse.parse_qsl(content))

		session.pop('request_token', None)
		return render_template('route.html', maps_api_key=config.maps_api_key)

	else:
		return render_template('index.html')

@app.route('/authorize/')
def authorize():
	'''Redirects user to Twitter OAuth authorization page.
	Redirects back to /'''

	client = oauth.Client(app.consumer)
	resp, content = client.request(config.auth_url+'request_token', 'POST',
							body=urlencode({'oauth_callback': config.site_url+url_for('index')}))
	print '/authorize/'
	print content
	verify_response(resp)

	session['request_token'] = dict(urlparse.parse_qsl(content))

	return redirect('{0}?oauth_token={1}'.format(config.auth_url+'authorize',
							session['request_token']['oauth_token']))

	

@app.route('/route/', methods=['POST',])
def route():
	try:
		user = session['access_token']['screen_name']
	except KeyError:
		# not authorized
		return make_response('You must have a valid session to complete this request.', 401)
	
	if not app.cache.exists(':'.join([user,'dur'])):	
		
		# this is the first server push, generate a tweet
		client = oauth.Client(app.consumer,
			oauth.Token(key=session['access_token']['oauth_token'],
			secret=session['access_token']['oauth_token_secret']))
		resp, content = client.request(config.tweet_url, 'POST', body=urlencode({
			'status': 'Hello http://google.com',
			#'status': "I started a trip! Track my progress at {0}track/{1}".format(
			#config.site_url, user),
		}))

		print 'access token'
		print content
		verify_response(resp)


	with app.cache.pipeline() as pipe:
		for key in ('lat', 'lng', 'dest', 'dur'):
			pipe.set(':'.join([user,key]), request.form[key])
			# set to expire ten minutes after arrival
			pipe.expire(':'.join([user,key]), int(request.form['dur'])+600)
		pipe.execute()
	return 'OK'

@app.route('/track/<user>/')
def track_user(user):
	if not app.cache.exists(':'.join([user,'dur'])):
		return make_response('nothing here', 404)
	return render_template('track.html', maps_api_key=config.maps_api_key, user=user)

@app.route('/loc/<user>/')
def get_location(user):
	d = dict([(i,app.cache.get(':'.join([user,i])))
		for i in ('lat','lng','dest','dur')])
	print d
	print json.dumps(d)
	return json.dumps(d)


if __name__ == '__main__':
	app.run(debug=True)
