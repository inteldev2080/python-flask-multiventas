from flask import Blueprint
from models.models import Admin
# BLUEPRINTS
admin_bp = Blueprint('admin_bp', __name__)

@admin_bp.route('/')
def index():
    return Admin.query.all()
    return render_template("admin.html")