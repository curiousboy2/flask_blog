from . import main
from datetime import datetime
from flask import render_template,flash,current_app,request
from flask import make_response,redirect,abort,session,url_for
from .forms import wtf_form,EditProfileForm,EditProfileAdminForm,PostArticle
from ..email import send_email
import os
from ..decorators import admin_required, permission_required
from ..models import Permission,Post
from flask_login import login_required,current_user
from ..models import User,Role
from app import db
from threading import Thread
import time
from PIL import Image
from io import BytesIO

@main.route('/',methods=['GET','POST'])
def index():
    form=PostArticle()
    page = request.args.get('page', 1, type=int)
    pagination = Post.query.order_by(Post.timestamp.desc()).paginate(
    page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    if form.validate_on_submit():
        p=Post(body=form.text.data,author_id=current_user.id)
        db.session.add(p)
        return redirect('/')

    return render_template('index.html',form=form,utctime=datetime.utcnow(),posts=posts,pagination=pagination)


#@main.route('/user/<name>')
#def user(name):
#    return render_template('user.html',name=name,utctime=datetime.utcnow())

@main.route('/response/01.html')
def response():
    resp=make_response('<h1>hello,response</h1>')
    resp.set_cookie('answer','12')
    return resp

@main.route('/redirect')
def direct():
    return redirect('http://www.baidu.com')

@main.route('/abort/<name>')
def abort_name(name):
    if name=='jeff':
        abort(404)
    return '<h1>hello,%s' %name

@main.route('/form',methods=['GET','POST'])
def show_form():
    form=wtf_form()
    if form.validate_on_submit():
        user=None
        if user is None:
            session['known']=False
            send_email([os.getenv('FLASK_ADMIN')],'hello','mail/user')
        else:
            session['known']=True
        session['name']=form.name.data
        form.name.data=''
        return redirect(url_for('.show_form'))
    return render_template('form.html',form=form,name=session.get('name'),known=session.get('known','False'))


@main.route('/admin')
@login_required
@admin_required
def for_admins_only():
    return render_template('admin.html'),200

@main.route('/moderator')
@login_required
@permission_required(0x08)
def for_moderators_only():
    return "For comment moderators!"

@main.route('/user/<username>')
def profile(username):
    u=User.query.filter_by(username=username).first()
    if u is None:
        abort(404)
    page = request.args.get('page', 1, type=int)
    pagination = u.posts.paginate(
    page, per_page=current_app.config['FLASKY_POSTS_PER_PAGE'],
        error_out=False)
    posts = pagination.items
    if u.upload_picture:
        filename=u.username
    else:
        filename='default'
    return render_template('user.html',user=u,utctime=datetime.utcnow(),posts=posts,filename=filename,pagination=pagination)

@main.route('/edit-profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.name =form.name.data
        current_user.location = form.location.data
        current_user.about_me = form.about_me.data
        #picture=form.picture.data
        picture=request.files[form.picture.name]
        if picture:
            save_picture(picture,current_user.username)
            #deal_it(picture,current_user.username)
            current_user.upload_picture=True
        db.session.add(current_user)
        flash('Your profile has been updated.')
        return redirect(url_for('.profile', username=current_user.username))
    form.name.data = current_user.name
    form.location.data = current_user.location
    form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', form=form)


def save_picture(picture,uid):
    filename='app\\static\\picture\\{}.jpg'.format(uid)
    tmp_p=BytesIO(picture.read())
    img=Image.open(tmp_p)
    img.thumbnail((60,80))
    img.save(filename)
    img.close()
    tmp_p.close()

#@main.route('/user/<username>')
#def user(username):
#    user = User.query.filter_by(username=username).first()
#    if user is None:
#        abort(404)
#    return render_template('user.html', user=user)

@main.route('/picture/<username>')
def picture(username):
    if os.path.isfile('app\\static\\picture\\{}.jpg'.format(username)):
        username='default'
    return redirect(url_for('static',filename='picture/{}.jpg'.format(username)))

@main.route('/edit-profile/<int:id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_profile_admin(id):
    user = User.query.get_or_404(id)
    form = EditProfileAdminForm(user=user)
    if form.validate_on_submit():
        user.email = form.email.data
        user.username = form.username.data
        user.confirmed = form.confirmed.data
        user.role = Role.query.get(form.role.data)
        user.name = form.name.data
        user.location = form.location.data
        user.about_me = form.about_me.data
        db.session.add(user)
        flash('The profile has been updated.')
        return redirect(url_for('.profile', username=user.username))
    form.email.data = user.email
    form.username.data = user.username
    form.confirmed.data = user.confirmed
    form.role.data = user.role_id
    form.name.data = user.name
    form.location.data = user.location
    form.about_me.data = user.about_me
    return render_template('edit_profile.html', form=form)

@main.route('/post/<int:id>')
def post(id):
    p=Post.query.get_or_404(id)
    return render_template('post.html',posts=[p])

@main.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit(id):
    post = Post.query.get_or_404(id)
    if current_user != post.author and \
        not current_user.can(Permission.ADMINISTER):
        abort(403)
    form = PostArticle()
    if form.validate_on_submit():
        post.body = form.text.data
        db.session.add(post)
        flash('The post has been updated.')
        return redirect(url_for('.post', id=post.id))
    form.text.data = post.body
    return render_template('edit_post.html', form=form)

@main.route('/followers/<username>')
def followers(username):
    u=User.query.filter_by(username=username).first()
    if u is None:
        flash('invalid username')
        return redirect(url_for('.index'))
    fans=u.followers.all()
    fans_dict=[{'fan_name':fan.follower,'timestamp':fan.timestamp} for fan in fans]
    return render_template('followers.html',fans_dict=fans_dict,user=u)

@main.route('/follow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def follow(username):
    u=User.query.filter_by(username=username).first()
    if u is None:
        flash('invalid username')
        return redirect(url_for('.index'))
    if current_user.is_following(u):
        flash('you have alreadly follow {}'.format(username))
    else:
        current_user.follow(u)
        flash('you have followed {}'.format(username))
    return redirect(url_for('.profile',username=username))

@main.route('/unfollow/<username>')
@login_required
@permission_required(Permission.FOLLOW)
def unfollow(username):
    u=User.query.filter_by(username=username).first()
    if u is None:
        flash('invalid username')
        return redirect(url_for('.index'))
    current_user.unfollow(u)
    flash('you unfollow {} successful'.format(username))
    return redirect(url_for('.profile',username=username))

@main.route('/following/<username>')
@login_required
def following(username):
    u=User.query.filter_by(username=username).first()
    if u is None:
        flash('invalid username')
        return redirect(url_for('.index'))
    stars=u.followed.all()
    #stars=u.followed.count()
    stars_dict=[{'name':start.followed,'timestamp':start.timestamp} for start in stars]
    return render_template('following.html',stars_dict=stars_dict)


