from flask import Flask, render_template
from config import maps_api_key

app = Flask(__name__)
app.config.from_object(__name__)

@app.route('/', methods=['GET',])
def index():
	return render_template('index.html', maps_api_key=maps_api_key)
	
if __name__ == '__main__':
	app.run(debug=True)