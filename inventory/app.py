from flask import Flask, render_template, jsonify
from flask_redis import Redis
from flask_bootstrap import Bootstrap
from flask_debugtoolbar import DebugToolbarExtension

app = Flask(__name__)
#REDIS_URL = "redis://localhost:6379/0"
redis_store = Redis(app)
Bootstrap(app)
app.debug = True
app.config['SECRET_KEY'] = 'inventorykey'
app.config['DEBUG_TB_PROFILER_ENABLED'] = True
app.config['REDIS_URL'] = "redis://localhost:6379/0"
toolbar = DebugToolbarExtension(app)

@app.route("/")
def index():
    data = []
    output = redis_store.smembers('all')
    for x in output:
        data.append(redis_store.hgetall(x))
    return render_template('index.html', output=data)

@app.route("/json")
def index_json():
    data = []
    output = redis_store.smembers('all')
    for x in output:
        data.append(redis_store.hgetall(x))

    return jsonify({"results": data, "length": len(data)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)
