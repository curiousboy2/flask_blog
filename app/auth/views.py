from . import auth
from flask import render_template,redirect,request,url_for,flash
from flask_login import login_required,login_user,logout_user
from .forms import LoginForm,RegistrationForm,ChangePasswordForm,PasswordResetForm,PasswordResetRequestForm
from ..models import User
from .. import db
from ..email import send_email
from flask_login import current_user

@auth.route('/login',methods=['GET','POST'])
def login():
    login_form=LoginForm()
    if login_form.validate_on_submit():
        user=User.query.filter_by(email=login_form.email.data).first()
        if user is not None and user.verify_password(login_form.password.data):
            login_user(user,login_form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('invalid username or password')
    return render_template('auth/login.html',form=login_form)

@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('you have logout')
    return redirect(url_for('main.index'))

@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data,username=form.username.data,password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'Confirm Your Account',
'auth/email/confirm', user=user, token=token)
        flash('A confirmation email has been sent to you by email.')

        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash('You have confirmed your account. Thanks!')
    else:
        flash('The confirmation link is invalid or has expired.')
    return redirect(url_for('main.index'))

@auth.route('/reconfirm/<username>')
@login_required
def reconfirm(username):
    user=User.query.filter_by(username=username).first()
    token = user.generate_confirmation_token()
    send_email(user.email, 'Confirm Your Account',
'auth/email/confirm', user=user, token=token)
    flash('A confirmation email has been sent to you by email.')
    return redirect(url_for('auth.login'))

@auth.route('/unconfirm/<username>')
def unconfirm(username):
    return render_template('unconfirm.html',username=username)

@auth.route('/ChangePassword',methods=['GET','POST'])
@login_required
def ChangePassword():
    form=ChangePasswordForm()
    if form.validate_on_submit():
        u=current_user
        u.password=form.password.data
        db.session.add(u)
        flash('password have changed')
        return redirect(url_for('main.index'))
    return render_template('auth/ChangePassword.html',form=form)

@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'Reset Your Password',
                       'auth/email/reset_password',
                       user=user, token=token,
                       next=request.args.get('next'))
        flash('An email with instructions to reset your password has been '
              'sent to you.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is None:
            return redirect(url_for('main.index'))
        if user.reset_password(token, form.password.data):
            flash('Your password has been updated.')
            return redirect(url_for('auth.login'))
        else:
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)

