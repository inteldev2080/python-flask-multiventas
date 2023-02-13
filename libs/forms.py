from flask_wtf.csrf import CSRFProtect
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField
from wtforms.validators import DataRequired
import wtforms.validators as v

stringVal = [
    v.Length(min=3, max=64, message="Debe tener entre 3 a 64 catacteres"),
    DataRequired()
]

csrf = CSRFProtect()

def init_CSRF(app):
    csrf.init_app(app=app)
    return csrf

user_render_kw={"class":"form"}
class UserSingUp(FlaskForm):
    username = StringField("Nombre y Apellido", render_kw=user_render_kw)
    email = EmailField("Correo", render_kw=user_render_kw)
    password = StringField("Contraseña", render_kw=user_render_kw)

    def generate_user(self):
        from models.models import User
        username = self.username.data
        email = self.email.data
        password = self.password.data

        if User.query.filter_by(email=email).first():
            return False
        user = User( username = username, email = email, password = password)
        return user