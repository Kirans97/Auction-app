from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class Tournament(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    logo = db.Column(db.String(200)) # Logo file name sathi
    city = db.Column(db.String(100), nullable=False)
    organiser = db.Column(db.String(100), nullable=False)
    mobile = db.Column(db.String(15), nullable=True)
    start_date = db.Column(db.String(20))
    end_date = db.Column(db.String(20))
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(50), nullable=False)
    total_purse = db.Column(db.Integer, default=0)
    batter_price = db.Column(db.Integer, default=0)
    bowler_price = db.Column(db.Integer, default=0)
    allrounder_price = db.Column(db.Integer, default=0)
    is_approved = db.Column(db.Boolean, default=False)
    status = db.Column(db.String(20), default="Pending")


class Team(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    short_name = db.Column(db.String(10), nullable=True)
    logo = db.Column(db.String(200))
    captain = db.Column(db.String(100))
    Team_Owner = db.Column(db.String(100))
    purse = db.Column(db.Integer)
    username = db.Column(db.String(100))
    password = db.Column(db.String(100))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    theme_color = db.Column(db.String(20), default="#0284c7")


class Player(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    role = db.Column(db.String(50))
    batting_style = db.Column(db.String(50))
    bowling_style = db.Column(db.String(50))
    base_price = db.Column(db.Integer)
    image = db.Column(db.String(200))
    current_price = db.Column(db.Integer, default=0)
    sold_price = db.Column(db.Integer)
    sold_to = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending")
    last_bid_team = db.Column(db.String(50))
    tournament_id = db.Column(db.Integer, db.ForeignKey('tournament.id'))
    category = db.Column(db.String(10), default='A')  # 'A' kiwa 'B' save hoil
    round = db.Column(db.Integer, default=1)
    updated_at = db.Column(db.DateTime, default=db.func.now(), onupdate=db.func.now())
    
    
class Registration(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    contact = db.Column(db.String(15))
    role = db.Column(db.String(50))      # Category
    batting_style = db.Column(db.String(50))
    bowling_style = db.Column(db.String(50))
    ts_name = db.Column(db.String(50))   # Name on T-shirt
    ts_no = db.Column(db.String(10))     # Choice No
    ts_size = db.Column(db.String(10))   # Manual Entry
    transaction_id = db.Column(db.String(100), nullable=False)
    payment_ss = db.Column(db.String(200)) # File name
    tournament_id = db.Column(db.Integer)
    status = db.Column(db.String(20), default="pending")
    photo = db.Column(db.String(200)) # Player cha photo
    status = db.Column(db.String(20), default="pending")
    
    
class AuctionSettings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Limits
    limit1 = db.Column(db.Integer, default=500)
    limit2 = db.Column(db.Integer, default=1000)
    limit3 = db.Column(db.Integer, default=2000)
    limit4 = db.Column(db.Integer, default=5000)
    # Values (Increments)
    val1 = db.Column(db.Integer, default=20)
    val2 = db.Column(db.Integer, default=50)
    val3 = db.Column(db.Integer, default=100)
    val4 = db.Column(db.Integer, default=200)