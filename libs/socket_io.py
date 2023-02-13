from flask_socketio import SocketIO, emit
from models.models import dateV
        
def time_stamp():
    return dateV.datetime_now().strftime("%d-%m-%Y %H:%M:%S")