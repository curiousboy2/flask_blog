from flask import Blueprint,redirect,url_for
from flask_login import current_user,request

auth=Blueprint('auth',__name__)

@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
    if current_user.is_authenticated and not current_user.confirmed and request.endpoint[:5]!='auth.':
        return redirect(url_for('auth.unconfirm',username=current_user.username))

from . import views