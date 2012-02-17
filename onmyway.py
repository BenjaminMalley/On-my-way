from flask import Flask, render_template, session, url_for, redirect, request
import config
import oauth2 as oauth
import redis
import urlparse
from urllib import urlencode

app = Flask(__name__)
app.secret_key = config.consumer_key
app.consumer = oauth.Consumer(key=config.consumer_key, secret=config.consumer_secret)

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

		# response is verified; remove the request token 
		# user will have to re-authenticate on next load
		session.pop('request_token', None)

		client = oauth.Client(app.consumer, auth_token)
		resp, content = client.request(config.auth_url+'access_token', 'GET')
		
		verify_response(resp)
		
		session['access_token'] = dict(urlparse.parse_qsl(content))

		if session['access_token']['screen_name'] == None:
			
			token = oauth.Token(key=session['access_token']['oauth_token'],
				secret=session['access_token']['oauth_token_secret'])
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
	verify_response(resp)

	session['request_token'] = dict(urlparse.parse_qsl(content))

	return redirect('{0}?oauth_token={1}'.format(config.auth_url+'authorize',
							session['request_token']['oauth_token']))

@app.route('/route/', methods=['POST',])
def route():
	if session['access_token'] != None:
		user = session['access_token']['screen_name']
		for key in ('lat', 'lng', 'dest', 'dur'):
			print request.form[key]
			session[key] = request.form[key]
		return 'OK'
	else:
		return make_response('You must have a valid session to complete this request.', 401)

if __name__ == '__main__':
	app.run(debug=True)
