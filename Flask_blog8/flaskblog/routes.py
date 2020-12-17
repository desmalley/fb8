import os
import secrets
from PIL import Image
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog import app, db, bcrypt
from flaskblog.forms import RegistrationForm, LoginForm, UpdateAccountForm, PostForm, BidForm
from flaskblog.models import User, Post
from flask_login import login_user, current_user, logout_user, login_required

import csv
import pprint as pp

#turns csv into a list of dictionaries (one for each row)
'''
with open('items.csv') as csvfile:
    reader = csv.DictReader(csvfile)
    items = [row for row in reader]
print(items[1])
'''

with open("items.csv", "r") as fp:
    item_reader = csv.DictReader(fp, skipinitialspace=True)
    items = [row for row in item_reader]
    item_header = item_reader.fieldnames 

with open("ledger.csv", "r") as fp:
    ledger_reader = csv.DictReader(fp, skipinitialspace=True)
    scouts = [row for row in ledger_reader]
    ledger_header = ledger_reader.fieldnames 

names=[scout['codename'] for scout in scouts]


def update_items(items, header=item_header):
    with open("items.csv", "w") as fp:
        writer = csv.DictWriter(fp, header)
        writer.writeheader()
        for row in items:
            writer.writerow(row)

def update_ledger(ledger, header=ledger_header):
    with open("ledger.csv", "w") as fp:
        writer = csv.DictWriter(fp, header)
        writer.writeheader()
        for row in ledger:
            writer.writerow(row)

def name_check(name, names=names):
    return name.lower() in names            



@app.route("/")
@app.route("/home")
def home():
    posts = Post.query.all()
    return render_template('home.html', posts=posts, items=items)


@app.route('/scoutbay/<item_num>')
def item_page(item_num):
    item=items[int(item_num)]
    #print(item)
    return render_template('item.html', item=item)#could send each key as a variable by using item**


@app.route("/about")
def about():
    return render_template('about.html', title='About')
 


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You are now able to log in', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


def save_picture(form_picture):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn


@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', title='Account',
                           image_file=image_file, form=form)

@app.route("/bid/<int:item_id>", methods=['GET', 'POST'])
def bid(item_id):
    item=items[item_id]
    high_bidder=item['bidder']
    bid_amt=int(item['bid'])

    form = BidForm()
    if form.validate_on_submit():
        print(f"the current high bid is {bid_amt}")
        print(f"You bid: {form.bid.data}")
        if form.bidder.data not in names:
            flash(f'Be sure you spell the name correctly you entered {form.bidder.data} but you need to enter a name on the list: {names}', 'danger')
            return redirect(url_for('bid', item_id=item_id))
        codename=form.bidder.data
        code_index=names.index(codename)
        scout=scouts[code_index]
        bucks=int(scout['bucks'])

        if int(form.bid.data) > bucks:
            flash(f"Sorry, you only have {bucks} bucks--not enough to make that bid.", 'danger')
            return redirect(url_for('bid', item_id=item_id))

        if int(form.bid.data) > bid_amt:
            flash('Your bid has been recorded. You are the highest bidder!', 'success')
            items[item_id]['bid']=form.bid.data
            items[item_id]['bidder']=form.bidder.data
            update_items(items)
        else:
            flash(f'Your bid is too low. You must bid higher than {bid_amt} to beat {high_bidder}', 'danger')
            return redirect(url_for('bid', item_id=item_id))
        return redirect(url_for('home'))
    return render_template('bid.html', title='New Post',
                           form=form, legend='New Bid', item=item)    

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data, author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created!', 'success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',
                           form=form, legend='New Post')


@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)


@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def update_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form = PostForm()
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        db.session.commit()
        flash('Your post has been updated!', 'success')
        return redirect(url_for('post', post_id=post.id))
    elif request.method == 'GET':
        form.title.data = post.title
        form.content.data = post.content
    return render_template('create_post.html', title='Update Post',
                           form=form, legend='Update Post')


@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post has been deleted!', 'success')
    return redirect(url_for('home'))
