from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
import random

# Flask uygulamasını oluştur
app = Flask(__name__)
app.secret_key = 'alsanakeloglan1'

# Veritabanı bağlantı ayarları (AWS RDS kullanılarak güncellendi)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://admin:alsanakeloglan1@database-1.c9gucmq8ub13.eu-north-1.rds.amazonaws.com/blogsitesi'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Mail ayarları
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'rotenarbe@gmail.com'
app.config['MAIL_PASSWORD'] = 'pnkdjlqhtxeibkcl'
mail = Mail(app)


class Customer(db.Model):
    __tablename__ = 'customers'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    surname = db.Column(db.String(100), nullable=False)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    bio = db.Column(db.Text)
    profile_picture_url = db.Column(db.Text)
    join_date = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())
    followers = db.Column(db.Integer, default=0)
    following = db.Column(db.Integer, default=0)
    role = db.Column(db.Enum('admin', 'author', 'reader'), default='reader')
    status = db.Column(db.Enum('active', 'inactive', 'banned'), default='active')

class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    contents = db.Column(db.Text, nullable=False)
    likes = db.Column(db.Integer, default=0)
    comments = db.relationship('Comment', back_populates='post', cascade="all, delete-orphan")
    views = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100))
    tags = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())
    last_updated = db.Column(db.TIMESTAMP, default=db.func.current_timestamp(), onupdate=db.func.current_timestamp())
    customer = db.relationship('Customer', backref=db.backref('posts', lazy=True))

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())
    post = db.relationship('Post', back_populates='comments')
    customer = db.relationship('Customer', backref=db.backref('comments', lazy=True))

class Follow(db.Model):
    __tablename__ = 'follows'
    id = db.Column(db.Integer, primary_key=True)
    follower_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)  # Takip eden kullanıcı
    following_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)  # Takip edilen kullanıcı
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())

    # İlişkilere benzersiz backref'ler ekleniyor
    follower = db.relationship(
        'Customer',
        foreign_keys=[follower_id],
        backref=db.backref('following_customers', lazy='dynamic')  # Takip ettiği kullanıcılar
    )
    following = db.relationship(
        'Customer',
        foreign_keys=[following_id],
        backref=db.backref('followers_customers', lazy='dynamic')  # Takip eden kullanıcılar
    )

class Like(db.Model):
    __tablename__ = 'likes'
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)  # Beğenen kullanıcı
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id'), nullable=False)  # Beğenilen gönderi
    created_at = db.Column(db.TIMESTAMP, default=db.func.current_timestamp())

    customer = db.relationship('Customer', backref=db.backref('liked_posts', lazy=True))  # Kullanıcının beğendiği gönderiler
    post = db.relationship('Post', backref=db.backref('post_likes', lazy=True))  # Gönderiye ait beğeniler


@app.route('/')
def start():
    return render_template('start.html')


@app.route('/home')
def home():
    posts = Post.query.order_by(db.func.rand()).limit(20).all()
    return render_template('home.html', posts=posts)


@app.route('/post/<int:post_id>')
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', post=post)


@app.route('/add', methods=['GET', 'POST'])
def add_post():
    if 'user_id' not in session:  # Kullanıcı giriş yapmamışsa
        return redirect(url_for('login'))  # Giriş sayfasına yönlendir

    if request.method == 'POST':
        customer_id = session['user_id']  # Oturumdaki kullanıcıyı alın
        contents = request.form['contents']
        category = request.form['category']
        tags = request.form['tags']
        
        new_post = Post(customer_id=customer_id, contents=contents, category=category, tags=tags)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('home'))
    
    return render_template('add_post.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Kullanıcı adı veya e-posta girişini alın
        identifier = request.form.get('username')  # Formdaki input adıyla eşleşmeli
        password = request.form.get('password')  # Şifre

        # Kullanıcıyı e-posta veya kullanıcı adıyla bul
        user = Customer.query.filter(
            (Customer.email == identifier) | (Customer.username == identifier)
        ).first()

        # Kullanıcı bulunduğunda şifre doğrulama
        if user and user.password == password:  # Şifre hashleme ekleyebilirsiniz
            session['user_id'] = user.id  # Kullanıcıyı oturuma ekle
            return redirect(url_for('home'))
        else:
            return 'Giriş başarısız. Kullanıcı adı/e-posta veya şifre yanlış.'
    
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Doğrulama kodu oluştur ve e-posta gönder
        verification_code = str(random.randint(100000, 999999))
        session['temp_user'] = {
            'name': name,
            'surname': surname,
            'username': username,
            'email': email,
            'password': password,
            'verification_code': verification_code
        }

        # E-posta gönderimi
        msg = Message('Blog - E-posta Doğrulama Kodu',
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[email])
        msg.body = f"Merhaba {name},\n\nDoğrulama kodunuz: {verification_code}\n\nBlog sitesine hoş geldiniz!"
        mail.send(msg)

        return redirect(url_for('verify_email'))

    return render_template('register.html')


@app.route('/verify_email', methods=['GET', 'POST'])
def verify_email():
    if request.method == 'POST':
        entered_code = request.form['verification_code']
        temp_user = session.get('temp_user')

        # Geçici kullanıcı verisini kontrol et
        if temp_user is None:
            return 'Doğrulama işlemi sırasında hata oluştu. Lütfen tekrar deneyin.'

        if entered_code == temp_user['verification_code']:
            try:
                # Kullanıcıyı oluştur
                new_user = Customer(
                    name=temp_user['name'],
                    surname=temp_user['surname'],
                    username=temp_user['username'],
                    email=temp_user['email'],
                    password=temp_user['password']  # Şifreleme eklenmeli!
                )
                db.session.add(new_user)
                db.session.commit()

                # Geçici veriyi temizle
                session.pop('temp_user', None)

                return redirect(url_for('start'))
            except Exception as e:
                return f'Kullanıcı oluşturulurken hata oluştu: {str(e)}'

        return 'Doğrulama kodu yanlış. Lütfen tekrar deneyin.'

    return render_template('verify_email.html')


@app.route('/logout')
def logout():
    session.pop('user_id', None)  # Kullanıcı oturumunu sonlandır
    return redirect(url_for('start'))  # Ana sayfaya yönlendir


@app.route('/follow/<int:customer_id>', methods=['POST'])
def follow(customer_id):
    current_user_id = 1  # Örneğin: Şu an oturum açmış kullanıcı (oturum sistemi ile değiştirilebilir)
    follow = Follow(follower_id=current_user_id, following_id=customer_id)
    db.session.add(follow)
    db.session.commit()
    return redirect(url_for('home'))


@app.route('/followers/<int:customer_id>')
def followers(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    followers = customer.followers.all()  # Kullanıcının takipçileri
    return render_template('followers.html', followers=followers)


@app.route('/following/<int:customer_id>')
def following(customer_id):
    customer = Customer.query.get_or_404(customer_id)
    following = customer.following.all()  # Kullanıcının takip ettiği kişiler
    return render_template('following.html', following=following)


@app.route('/like/<int:post_id>', methods=['POST'])
def like_post(post_id):
    current_user_id = 1  # Örneğin: Şu an oturum açmış kullanıcı
    like = Like(customer_id=current_user_id, post_id=post_id)
    db.session.add(like)
    db.session.commit()
    return redirect(url_for('home'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Veritabanı tablolarını oluştur
    app.run(debug=True)
