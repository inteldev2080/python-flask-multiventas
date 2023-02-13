from flask import Blueprint, send_from_directory
import os

# BLUEPRINTS
assets = Blueprint('assets_Bp', __name__)

@assets.route("/img/<filename>/")
def image_manager(filename):
    print(filename)
    return send_from_directory(os.path.join(os.getcwd(), "static/img"), path=filename, as_attachment=False)

@assets.route("/support_img/<filename>/")
def sup_image_manager(filename):
    return send_from_directory(os.path.join(os.getcwd(), "assets/support_img"), path=filename, as_attachment=False)