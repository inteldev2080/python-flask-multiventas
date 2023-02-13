from flask import g, jsonify
from __init__ import create_app
from models.models import init_DB, User, dateV
from flask_jwt_extended import JWTManager, jwt_required, current_user
from flask_cors import CORS

from libs.forms import init_CSRF

# APP
app, environment = create_app()
db = init_DB(app)
jwt = JWTManager(app)
# csrf = init_CSRF(app=app)
CORS(app)



from controller.api import api
from controller.assets import assets

app.register_blueprint(api, url_prefix='/api')
app.register_blueprint(assets, url_prefix='/assets')
 
def get_dollar_price():
    from libs.money_change import MoneyChange
    try:
        if not g.dollarPrice:
            g.dollarPrice = MoneyChange.get_dollar()
    except:
        g.dollarPrice = MoneyChange.get_dollar()
    
    return g.dollarPrice

def ErrorResponse(error, errors=[]):
    return jsonify({ "status":False, "error":error, "errors":errors })

def SuccessResponse(response):
    return jsonify({ "status":True, **response })
    
@app.before_request
def app_before_request():
    from flask import request
    g.get_dollar = get_dollar_price
    g.TZ_INFO = app.config["TZ_INFO"]
    g.today = dateV.date_today()
    g.now = dateV.datetime_now()

    valid = False
    url = request.path[1:].lower()
    valid_start = ["api", "static", "assets"]
    for end_point in valid_start:
        if url.startswith(end_point):
            valid = True
            break

    if not valid: return index()

@app.route("/")
@jwt_required(optional=True)
def index():
    from flask import render_template
    return render_template("index.html")
# Register a callback function that takes whatever object is passed in as the
# identity when creating JWTs and converts it to a JSON serializable format.
@jwt.user_identity_loader
def user_identity_lookup(user):
    return user.id


# Register a callback function that loads a user from your database whenever
# a protected route is accessed. This should return any python object on a
# successful lookup, or None if the lookup failed for any reason (for example
# if the user has been deleted from the database).
@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data):
    identity = jwt_data["sub"]

    return User.query.filter(User.id==identity).first()


if __name__ == '__main__':
    app.run(port=4000, debug=True, host="0.0.0.0")