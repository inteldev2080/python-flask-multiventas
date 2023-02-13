from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, current_user
from main import db, ErrorResponse, SuccessResponse
from models.models import SupportProducts, dateV
from werkzeug.utils import secure_filename
import os

# BLUEPRINTS
support_bp = Blueprint('support_bp', __name__)
support_img_path = os.path.join(os.getcwd(), "assets\support_img")

@support_bp.route("/", methods=["GET", "POST"])
@jwt_required()
def index():
    if request.method == "POST":
        try:
            subject = request.form["subject"]
            description = request.form["description"]
            type_p = request.form["type_p"]
            type_id = request.form["type_id"]
            file = request.files['file']
            name, ext = file.filename.rsplit(".", 1)

            if ext not in ["jpg", "jpeg", "png", ""]:
                raise Exception("Formato de archivo invalido, debe ser una imagen valida")
            filename =secure_filename(f"{dateV.datetime_now().strftime('%Y%m%d_%H%M%S')}_{type_p}_{type_id}.{ext}")
            path = os.path.join(support_img_path, filename)
            file.save(path)

            data = {
                "user_id" : current_user.id,
                "subject" : subject,
                "file_path" : filename,
                "description" : description,
                "type" : type_p,
                "type_id" : type_id,
                "status" : 1
            }
            ticket = SupportProducts(**data)
            ticket.save_me()
            return SuccessResponse({"msg":"Este caso de soporte ha sido iniciado"})
        except KeyError as e:
            return ErrorResponse(error="faltaron campos por rellenar")
        except Exception as e:
            return ErrorResponse(error=str(e))
    return "Ok"