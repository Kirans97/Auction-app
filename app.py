import os
import random
import io
from datetime import timedelta
from flask import Flask, render_template, request, redirect, session, send_file , url_for , jsonify , flash
from werkzeug.utils import secure_filename
from openpyxl import Workbook
from datetime import datetime
from PIL import Image
from functools import wraps
from models import db, Tournament, Team, Player, Registration, AuctionSettings

#===================================================================
app = Flask(__name__)
app.secret_key = "auction_secret_key"
app.permanent_session_lifetime = timedelta(minutes=15)
#====================================================================


# ही पद्धत (Decorator) लॉगिन चेक करण्यासाठी वापरली जाते
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        t_id = kwargs.get('t_id') or kwargs.get('id')
        if not session.get("tournament") or (t_id and int(session.get("tournament")) != int(t_id)):
            flash("Session logout, Please login again")
            return redirect(url_for('login', id=t_id if t_id else 0))
        return f(*args, **kwargs)
    return decorated_function
#===================================================================

#==============================================
# admin login decorator
#===============================================
def super_admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # सेशनमध्ये 'is_admin' नावाची की आहे का आणि ती True आहे का ते चेक करा
        if not session.get("is_admin"):
            flash("Only Admin is allowed")
            return redirect("/admin-login") # तुझ्या मेन ॲडमिन लॉगिन पेजचा पाथ
        return f(*args, **kwargs)
    return decorated_function
#-----------------===================================================
@app.route("/admin-logout")
def admin_logout():
    # १. ॲडमिनचं सेशन रिकामं करा
    session.pop('is_admin', None) 
    
    # २. होम पेजला पाठवा
    flash("session logout ")
    resp = make_response(redirect("/"))
    
    # ३. ब्राउझरला सांगा की आता जुनं पेज दाखवू नको (Security Headers)
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp
#=========================================


# =================================================
# PATH + DB
# =================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DB_PATH = os.path.join(BASE_DIR, "auction.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_PATH
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

db.init_app(app)

#===============================
@app.after_request
def add_header(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response
#============================================

with app.app_context():
##    db.drop_all()
    db.create_all()

# =================================================
# HOME
# =================================================
@app.route("/")
def home():
    return render_template("home.html")
#====================NAVBAR========================
@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/pricing')
def pricing():
    return render_template('pricing.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/join')
def join():
    return render_template('join.html')
# =================================================
# TOURNAMENTS
# =================================================
@app.route("/tournaments")
def tournaments():
    tournaments = Tournament.query.filter_by(status="Approved").all()
    return render_template("tournaments.html", tournaments=tournaments)


@app.route("/add-tournament", methods=["POST"])
def add_tournament():

    file = request.files.get("logo")
    filename = None

    if file and file.filename != "":
        filename = secure_filename(file.filename)
        path = os.path.join("static/uploads/logos", filename)
        file.save(path)

    start_date = request.form.get("start_date")
    end_date = request.form.get("end_date")

    if start_date:
        start_date = datetime.strptime(start_date,"%Y-%m-%d")

    if end_date:
        end_date = datetime.strptime(end_date,"%Y-%m-%d")

    new_t = Tournament(
        name=request.form.get("name"),
        logo=filename,
        city=request.form.get("city"),
        organiser=request.form.get("organiser"),
        mobile=request.form.get("mobile"),
        start_date=start_date,
        end_date=end_date,
        username=request.form.get("username"),
        password=request.form.get("password"),
        total_purse=request.form.get("purse"),
        batter_price=request.form.get("bat_p"),
        bowler_price=request.form.get("bowl_p"),
        allrounder_price=request.form.get("ar_p"),
        is_approved=False
    )

    db.session.add(new_t)
    db.session.commit()
    
    #flash("Tournament submitted successfully. Admin approval pending.")-->
    return render_template("success.html")
#====================================================
# approve tournament
#===================================================
# ॲडमिन डॅशबोर्ड - सर्व पेंडिंग टूर्नामेंट्स पाहण्यासाठी
@app.route('/admin/dashboard')
@super_admin_required
def admin_dashboard():
    # ज्या टूर्नामेंट्स अजून अप्रूव झालेल्या नाहीत (is_approved=False) त्या मिळवा
    pending_tournaments = Tournament.query.filter_by(is_approved=False).all()
    return render_template('admin_dashboard.html', tournaments=pending_tournaments)

# टूर्नामेंट अप्रूव करण्यासाठीचा मार्ग
@app.route("/approve/<int:t_id>", methods=["POST"])
@super_admin_required
def approve_tournament(t_id): # हे नाव 'approve_tournament' च पाहिजे
    tournament = Tournament.query.get_or_404(t_id)
    if tournament:
        tournament.status = "Approved"  # इथे फक्त स्टेटस बदला
        db.session.commit()
    db.session.commit()
    return redirect("/admin/dashboard")
#================================================
# DELETE TOURNAMENT
#=================================================  
@app.route("/delete-tournament/<int:id>")
@super_admin_required
def delete_tournament(id): # हे नाव 'delete_tournament' च पाहिजे
    t = Tournament.query.get_or_404(id)
    db.session.add(t) # आधी ॲड नाही केलं तरी चालतं पण डिलीट महत्वाचं
    db.session.delete(t)
    db.session.commit()
    return redirect("/admin/dashboard")
#=================================================
# ADMIN LOGIN
#=================================================
@app.route("/admin-login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        user = request.form.get("username")
        pwd = request.form.get("password")
        
        # तुझे क्रेडेंशियल्स इथे सेट कर (हे फक्त तुला माहीत हवेत)
        if user == "superadmin" and pwd == "admin@123":
            session["is_admin"] = True
            session.permanent = True
            return redirect("/admin/dashboard")
        else:
            flash("चुकीचा पासवर्ड किंवा युजरनेम!")
            return redirect("/admin-login")

    return render_template("admin_login.html")
#=================================================
# EDIT TOURNAMENT
#=================================================
@app.route("/edit-tournament/<int:id>", methods=["GET", "POST"])
@login_required
def edit_tournament(id):
    t = Tournament.query.get_or_404(id)
    
    if request.method == "POST":
        t.name = request.form["name"]
        t.city = request.form["city"]
        t.organiser = request.form["organiser"]
        t.mobile = request.form["mobile"]
        t.start_date = request.form["start_date"]
        t.end_date = request.form["end_date"]
        t.username = request.form["username"]
        t.password = request.form["password"]
        t.total_purse = request.form["purse"]
        
        # नवीन किमती अपडेट करा
        t.batter_price = request.form["bat_p"]
        t.bowler_price = request.form["bowl_p"]
        t.allrounder_price = request.form["ar_p"]

        # --- AUTO UPDATE PLAYERS PRICE START ---
        # या टूर्नामेंटचे फक्त 'pending' प्लेयर्स शोधा
        from app import Player # जर वर इम्पोर्ट नसेल तर
        pending_players = Player.query.filter_by(tournament_id=id, status="pending").all()
        
        for p in pending_players:
            if p.role == 'Batter':
                p.base_price = t.batter_price
            elif p.role == 'Bowler':
                p.base_price = t.bowler_price
            elif p.role == 'All-Rounder':
                p.base_price = t.allrounder_price
            
            # करंट प्राईस पण बेस प्राईस एवढीच ठेवा
            p.current_price = p.base_price
        # --- AUTO UPDATE PLAYERS PRICE END ---

        # Logo update logic
        file = request.files.get("logo")
        if file and file.filename:
            filename = secure_filename(file.filename)
            file.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            t.logo = filename

        db.session.commit()
        return redirect(f"/dashboard/{id}")
        
    return render_template("edit_tournament.html", tournament=t)
# =================================================
# LOGIN
# =================================================
@app.route("/login/<int:id>", methods=["GET", "POST"])
def login(id):
    t = Tournament.query.get_or_404(id)
    if request.method == "POST":
        if request.form["username"] == t.username and request.form["password"] == t.password:
            session["tournament"] = id
            session.permanent = True  # लॉगिन टिकवून ठेवण्यासाठी
            return redirect(url_for('dashboard', t_id=id))
    return render_template("login.html", t=t)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/tournaments")
#================================================
# logout from bidding page
#===================================================
@app.route("/team-logout/<int:t_id>")
def t_logout(t_id):
    session.clear()
    return redirect(f"/team-login/{t_id}")

# =================================================
# DASHBOARD
# =================================================
@app.route("/dashboard/<int:t_id>")
@login_required
def dashboard(t_id):

    if session.get("tournament") != t_id:
        return redirect(f"/login/{t_id}")

    tournament = Tournament.query.get_or_404(t_id)
    return render_template("dashboard.html", tournament=tournament)

# =================================================
# TEAMS
# =================================================
import os
from flask import Flask, request, render_template, redirect, session
from werkzeug.utils import secure_filename

# 1. Path Configuration (Add this at the top)
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, 'static', 'uploads', 'logos')
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

# Folder nasel tar banva
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@app.route("/teams/<int:t_id>")
@login_required
def teams(t_id):
    if session.get("tournament") != t_id:
        return redirect(f"/login/{t_id}")

    teams = Team.query.filter_by(tournament_id=t_id).all()
    tournament = Tournament.query.get_or_404(t_id)
    return render_template("teams.html", teams=teams, tournament=tournament)

@app.route("/add-team/<int:t_id>", methods=["POST"])
@login_required
def add_team(t_id):
    # 1. Logo file handle kara
    file = request.files.get("logo")
    
    # default name theva jar file upload nahi jhali tar
    filename = "default_team.png" 

    if file and file.filename != '':
        filename = secure_filename(file.filename)
        # Full path banva
        save_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        
        # Debugging sathi terminal madhe path disel
        print(f"DEBUG: Saving image to -> {save_path}")
        file.save(save_path)

    # 2. Tournament object fetch kara
    t = Tournament.query.get_or_404(t_id)
    
    selected_color = request.form.get("theme_color", "#4fc3f7")

    # 3. Navin Team object banva
    try:
        team = Team(
            name=request.form["name"],
            short_name=request.form["short_name"],
            captain=request.form["captain"],
            Team_Owner=request.form["Team_Owner"],
            logo=filename,  # Ithe empty string nako, filename pahije
            purse=t.total_purse, 
            username=request.form["username"],  
            password=request.form["password"],
            theme_color=selected_color,
            tournament_id=t_id
        )

        db.session.add(team)
        db.session.commit()
        print("DEBUG: Team added successfully!")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG ERROR: {e}")
        return f"Error: {e}"

    return redirect(f"/teams/{t_id}")
#=================================================
#  TEAM EDIT AND DELETE 
#================================================
# Delete Team
@app.route("/delete-team/<int:id>")
@login_required
def delete_team(id):
    team = Team.query.get_or_404(id)
    t_id = team.tournament_id # Redirect sathi tournament id pahije
    db.session.delete(team)
    db.session.commit()
    return redirect(f"/teams/{t_id}")

# Edit Team (Brief)
#===================================================
@app.route("/edit-team/<int:id>", methods=["GET", "POST"])
@login_required
def edit_team(id):
    team = Team.query.get_or_404(id)
    
    if request.method == "POST":
        # 1. Basic Fields Update kara
        team.name = request.form.get("name")
        team.short_name=request.form.get("short_name")
        team.captain = request.form.get("captain")
        team.Team_Owner = request.form.get("Team_Owner")
        team.username = request.form.get("username")
        team.password = request.form.get("password")
        team.theme_color = request.form.get("theme_color")

        # 2. File (Logo) update logic
        file = request.files.get("logo")
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            # Absolute path vapra (jasa add_team madhe kela hota)
            file_path = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(file_path)
            team.logo = filename  # Database madhe navin naav save kara

        # 3. Save Changes
        try:
            db.session.commit()
            return redirect(f"/teams/{team.tournament_id}")
        except Exception as e:
            db.session.rollback()
            print(f"Update Error: {e}")
            return f"Error: {e}"

    # GET request sathi edit page dakhva
    return render_template("edit_team.html", team=team)
# =================================================
# PLAYERS
# =================================================
@app.route("/players/<int:t_id>")
@login_required
def players(t_id):
    if session.get("tournament") != t_id:
        return redirect(f"/login/{t_id}")

    # 1. FIX: Tournament object fetch kara (Jinja template sathi)
    tournament = Tournament.query.get_or_404(t_id)

    # 2. FIX: Fakt ya tournament che players dakhva
    players = Player.query.filter_by(tournament_id=t_id).all()
    
    return render_template("players.html", players=players, tournament=tournament, t_id=t_id)


# =================================================
# AUCTION CONTROL
# =================================================

from flask import make_response # He top la import asu dya

@app.route("/auction-control/<int:t_id>")
@login_required
def auction_control(t_id):
    # 1. Database Fresh Refresh (SQLite Force Sync)
    db.session.commit()
    db.session.expire_all()
    
    # 2. Logout Issue Fix: Strict Integer Comparison
    # Session madhla ID ani URL madhla ID dohi int karun check kara
    s_t_id = session.get("tournament")
    if s_t_id is None or int(s_t_id) != int(t_id):
        print(f"DEBUG: Session mismatch. Expected {t_id}, got {s_t_id}")
        return redirect(f"/login/{t_id}")

    # 3. Current Player Shoda (Status 'Bidding' aslele)
    player = Player.query.filter_by(tournament_id=t_id, status='Bidding').first()
    
    last_team = None
    if player:
        # Player cha last bidder fresh DB madhun uchatla
        if player.last_bid_team:
            last_team = Team.query.get(player.last_bid_team)
            # Bidder name fresh set kara
            player.last_bid_team_name = last_team.name if last_team else "None"
        else:
            player.last_bid_team_name = "None"

    asold_count = Player.query.filter(Player.tournament_id == t_id, func.lower(Player.status) == 'sold').count()
    unsold_count = Player.query.filter(Player.tournament_id == t_id, func.lower(Player.status) == 'unsold').count()
    pending_count = Player.query.filter(Player.tournament_id == t_id, func.lower(Player.status) == 'pending').count()
    
    # 4. Stats Calculation
    last_sold_p = Player.query.filter_by(tournament_id=t_id, status="sold").order_by(Player.updated_at.desc()).first()
    last_sold_team_name = ""
    if last_sold_p and last_sold_p.sold_to:
        t_obj = Team.query.get(last_sold_p.sold_to)
        last_sold_team_name = t_obj.name if t_obj else "---"
    
    last_sold_price = last_sold_p.sold_price if last_sold_p else "-"
# Expensive Player शोधण्यासाठी (फक्त त्याच टूर्नामेंटचा आणि 'sold' असलेला)
    expensive_p = Player.query.filter(Player.tournament_id == t_id, Player.status == 'sold' ).order_by(Player.sold_price.desc()).first()
    expensive_price = expensive_p.sold_price if expensive_p else "-"

    expensive_team_name = ""
    if expensive_p and expensive_p.sold_to:
        e_obj = Team.query.get(expensive_p.sold_to)
        expensive_team_name = e_obj.name if e_obj else "---"
    # 5. Team List ani Purse Calculation
    teams = Team.query.filter_by(tournament_id=t_id).all()
    
    current_base_price = player.base_price if player and player.base_price else 100
    
    for t in teams:
        total_slots = 15
        sold_count = Player.query.filter_by(sold_to=t.id, tournament_id=t_id).count()
        remaining_slots = total_slots - sold_count
        
        
    
# ----------------------

# ... baki loop ...
        
        
        # Max Bid Logic: Pratyek urlelya player sathi 100/- reserve
        if remaining_slots > 1:
            reserve = (remaining_slots - 1) * current_base_price
            t.max_allowed = t.purse - reserve
        else:
            t.max_allowed = t.purse

    # 6. Browser Caching Fix (IMPORTANT)
    # response madhe Headers taka jyamule browser junach data dakhvnar nahi
    resp = make_response(render_template(
        "auction_control.html",
        player=player,
        teams=teams,
        last_team=last_team,
        t_id=t_id,
        last_sold_price=last_sold_price,
        expensive_price=expensive_price,
        msold_count=asold_count,        
        unsold_count=unsold_count,    
        pending_count=pending_count
        
    ))
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    return resp

# =================================================
# START / NEXT PLAYER
# =================================================
@app.route("/create-bid/<int:t_id>")
def create_bid(t_id):
    if session.get("tournament") != t_id:
        return redirect(f"/login/{t_id}")

    # Check 1: Category A Pending
    eligible_players = Player.query.filter_by(tournament_id=t_id, status='pending', category='A').all()

    # Check 2: Category B Pending
    if not eligible_players:
        eligible_players = Player.query.filter_by(tournament_id=t_id, status='pending', category='B').all()

    # --- ROUND 2 TRANSITION LOGIC ---
    if not eligible_players:
        # Check kara ki Unsold players aahet ka?
        unsold_exists = Player.query.filter_by(tournament_id=t_id, status='unsold').all()
        
        # Jar session madhe 'round_2_started' nasel, tar thaamba!
        if unsold_exists and not session.get("round_2_confirmed"):
            if not session.get("current_player"):
                session["current_player"] = None
                return render_template("auction_control.html", 
                                 t_id=t_id, 
                                 player=None, 
                                 show_round_2_button=True, # He html la sangel
                                 teams=Team.query.filter_by(tournament_id=t_id).all())

        # Jar confirmed asel, tar unsold players uchatla
        eligible_players = unsold_exists

    # --- SELECTION ---
    if eligible_players:
        player = random.choice(eligible_players)
        player.round = 2 if player.status == 'unsold' else 1
        player.current_price = player.base_price
        player.last_bid_team = None
        
        player.status = 'Bidding'
        
        db.session.commit()
        
        session["current_player"] = player.id
        session.modified = True
        return redirect(f"/auction-control/{t_id}")
    else:
        return redirect(f"/dashboard/{t_id}")

# Round 2 Confirm karnyathi navin route
@app.route("/start-round-2/<int:t_id>")
def start_round_2(t_id):
    session["round_2_confirmed"] = True
    session.modified = True
    return redirect(url_for('create_bid', t_id=t_id))
# =================================================
# UNSOLD PLAYER
# =================================================
@app.route("/unsold/<int:p_id>/<int:t_id>")
@login_required
def unsold_player(p_id, t_id):
    # 1. Jo player screen var hota tyala database madhun shodha
    player = Player.query.get_or_404(p_id)
    
    # 2. Tyacha status 'unsold' kara (Mhanje to Round 2 sathi eligible hoil)
    player.status = "unsold"
    
    # 3. Bidder details clear kara
    player.last_bid_team = None 
    player.current_price = player.base_price
    
    if player.category in ['A', 'B']: 
            session["round_2_confirmed"] = False
            session["current_player"] = None
    
    # 4. Changes save kara
    db.session.commit()

    # --- AUTO NEXT LOGIC ---
    # Parat logic lihinyasathi 'create_bid' la call dya, 
    # to automatic priority (A->B->Unsold) nusar next player uchatel.
    return redirect(url_for('create_bid', t_id=t_id))
# =================================================
# SELL PLAYER
# =================================================

@app.route("/sell-player/<int:p_id>/<int:t_id>", methods=["GET", "POST"]) # GET पण ॲड केलंय कारण तू href वापरतोयस
@login_required
def sell_player(p_id, t_id):
    # १. डेटाबेस रिफ्रेश करा
    db.session.expire_all()
    
    player = Player.query.get_or_404(p_id)

    # जर बिडच लागली नसेल तर परत पाठवा
    if not player.last_bid_team:
        return redirect(f"/auction-control/{t_id}")

    # शेवटची बिड ज्या टीमने लावली आहे (Admin कडून असो किंवा Team कडून) ती मिळवा
    team = Team.query.get(player.last_bid_team)
    price = player.current_price or player.base_price

    if team:
        # २. प्लेयर अपडेट्स
        player.status = "sold"
        player.team_id = team.id        # Foreign Key साठी
        player.sold_to = team.id        # तुझ्या डॅशबोर्ड टेबलसाठी
        player.sold_price = price       # फायनल सोल्ड प्राईस
        
        # ३. टीमचा पर्स कमी करा
        team.purse -= price
        
        # ४. राऊंड २ आणि सेशन मॅनेजमेंट (तुझं मूळ लॉजिक)
        if player.category in ['A', 'B']: 
            session["round_2_confirmed"] = False
            session["current_player"] = None
        
        try:
            db.session.commit()
            # बदल सर्वत्र दिसण्यासाठी फ्रेश करा
            db.session.expire_all()
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}", 500

    # ५. नवीन प्लेयर जनरेट करण्यासाठी 'create_bid' कडे पाठवा
    return redirect(url_for('create_bid', t_id=t_id))
# =================================================
# RESET AUCTION
# =================================================
@app.route("/reset-auction/<int:t_id>")
@login_required
def reset_auction(t_id):
    # Session check
    if session.get("tournament") != t_id:
        return redirect(f"/login/{t_id}")

    tournament = Tournament.query.get_or_404(t_id)

    # 1. Players reset kara
    players = Player.query.filter_by(tournament_id=t_id).all()
    for p in players:
        p.sold_to = None
        p.sold_price = None
        p.status = "pending"
        # Jar current_price column asel tar to base_price la reset kara
        if hasattr(p, 'current_price'):
            p.current_price = p.base_price

    # 2. Teams chi amount reset kara (ITHE 'purse' VAPRA)
    teams = Team.query.filter_by(tournament_id=t_id).all()
    for team in teams:
        # team.purse vapra karan tu sangitlyasarkha column naav 'purse' aahe
        team.purse = tournament.total_purse 

    session["current_player"] = None
    
    try:
        db.session.commit()
        print("DEBUG: Auction Reset Successfully with Purse Update")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG ERROR: {e}")

    return redirect(f"/auction-control/{t_id}")

# =================================================
# UNDO LAST AUCTION
# =================================================
@app.route("/undo-auction/<int:t_id>")
@login_required
def undo_auction(t_id):
    # १. सर्वात शेवटी विकला गेलेला (Sold) किंवा अनसोल्ड (Unsold) झालेला प्लेयर शोधा
    # इथे आपण status != 'pending' असेलेल प्लेयर्स फिल्टर करतोय
    last_action_player = Player.query.filter(
        Player.tournament_id == t_id, 
        Player.status != 'pending'
    ).order_by(Player.id.desc()).first() 

    if last_action_player:
        # २. जर प्लेयर 'Sold' होता, तर त्या टीमला पैसे परत द्या (Purse Refund)
        if last_action_player.status == 'sold' and last_action_player.sold_to:
            team = Team.query.get(last_action_player.sold_to)
            if team:
                # प्लेयरची जी किंमत होती ती टीमच्या पर्समध्ये परत मिळवा
                team.purse += last_action_player.current_price
        
        # ३. प्लेयरचा डेटा पूर्णपणे रिसेट करा
        last_action_player.status = "pending"
        last_action_player.sold_to = None        # टीमचा आयडी काढून टाका
        last_action_player.last_bid_team = None  # शेवटची बिड काढली
        last_action_player.last_bid_team_name = None 
        last_action_player.current_price = last_action_player.base_price # प्राईस बेस प्राईस केली
        
        # ४. ऑक्शन पेजवर याच प्लेयरला पुन्हा दाखवण्यासाठी सेशन अपडेट करा
        session["current_player"] = last_action_player.id
        session.modified = True
        
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}", 500
    
    return redirect(f"/auction-control/{t_id}")
# =================================================
# EXPORT EXCEL
# =================================================
@app.route("/export-results/<int:t_id>")
@login_required
def export_results(t_id):

    wb = Workbook()
    ws = wb.active

    ws.append(["Name", "Role", "Status", "Sold To", "Price"])

    teams = {t.id: t.name for t in Team.query.all()}

    for p in Player.query.all():
        ws.append([
            p.name,
            p.role,
            p.status,
            teams.get(p.sold_to, "-"),
            p.sold_price or "-"
        ])

    file_stream = io.BytesIO()
    wb.save(file_stream)
    file_stream.seek(0)

    return send_file(file_stream, as_attachment=True, download_name="auction.xlsx")

#=======================================================
# RESULT PAGE
#===============================================
# --- Ha navin code add kar (Browser madhe result baghnyasathi) ---
@app.route("/results/<int:t_id>")
@login_required
def results_page(t_id):
    if session.get("tournament") != t_id:
        return redirect(f"/login/{t_id}")

    # Filters (Jar HTML madhun filter vaprayche astil tar)
    status_filter = request.args.get('status')
    team_filter = request.args.get('team')

    query = Player.query #.filter_by(tournament_id=t_id) # Fakt ya tournament che players
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if team_filter and team_filter != 'all':
        query = query.filter_by(sold_to=team_filter)

    players = query.all()
    teams = Team.query.filter_by(tournament_id=t_id).all()

    return render_template("results.html", 
                           players=players, 
                           teams=teams, 
                           t_id=t_id)

#================================================
# ADD PLAYER MANUALLY 
#=====================================================
@app.route("/manual-register/<int:t_id>", methods=["POST"])
@login_required
def manual_register(t_id):
    # 1. Image handling
    file = request.files.get("photo")
    filename = "default.png"
    if file and file.filename:
        filename = secure_filename(file.filename)
        # Khatri kara ha folder exist karto
        file.save(os.path.join("static/uploads/players", filename))
        

    # 2. Save in Registration Table
    try:
        new_reg = Registration(
            full_name=request.form.get("name"),
            photo=filename,
            address=request.form.get("address"),
            contact=request.form.get("contact"),
            role=request.form.get("role"),
            batting_style=request.form.get("bat_style"),
            bowling_style=request.form.get("bowl_style"),
            ts_name=request.form.get("ts_name"),
            ts_no=request.form.get("ts_no"),
            ts_size=request.form.get("ts_size"),
            transaction_id="MANUAL_ADMIN", 
            payment_ss="manual.png",        
            tournament_id=t_id,
            status="pending"               
        )

        db.session.add(new_reg)
        db.session.commit()
        print(f"DEBUG: Manual registration success for {new_reg.full_name}")
        
        # FIX: Redirect cha path tujhya 'pending_registrations' route la match pahije
        return redirect(f"/admin/pending/{t_id}")

    except Exception as e:
        db.session.rollback()
        print(f"DEBUG ERROR: {e}")
        return f"Database Error: {e}"
# =================================================
# Team login
# =================================================	
@app.route("/team-login/<int:t_id>", methods=["GET","POST"])
def team_login(t_id):
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        team = Team.query.filter_by(
            username=username,
            password=password,
            tournament_id=t_id
        ).first()

        if team:
            session["team"] = team.id
            return redirect(f"/bidding/{t_id}")

    return render_template("team_login.html", t_id=t_id)

# =================================================
# BIDDING
# =================================================	
@app.route("/bidding/<int:t_id>")
def bidding(t_id):
    if "team" not in session:
        return redirect(f"/team-login/{t_id}")

    # Team chi purn mahiti ghyaychi (Theme Color sathi)
    team = Team.query.get(session["team"])
    
    team_players_count = Player.query.filter_by(sold_to=team.id, tournament_id=t_id).count()
    
    # जर १५ प्लेयर पूर्ण झाले असतील, तर त्यांना एक वेगळं पेज किंवा मेसेज दाखवा
    team_is_full = False
    if team_players_count >= 15:
        team_is_full = True
        # तुम्ही इथे "squad.html" कडे रिडायरेक्ट करू शकता किंवा मेसेज देऊ शकता
       
    
    
    # --- ISSUE FIX: Session madhun nahi, Database madhun current player shodha ---
    player = Player.query.filter_by(tournament_id=t_id, status='Bidding').first()

    # Dynamic Settings
    auction_settings = {
        'val1': 20, 'limit1': 200,
        'val2': 50, 'limit2': 1000,
        'val3': 100, 'limit3': 2000,
        'val4': 200, 'limit4': 5000
    }

    # Max bid sathi default value
    max_allowed = team.purse 
    
    
    

    # Player asel tarach team name ani max_allowed check kara
    if player:
        # 1. Bidder Name Logic
        if player.last_bid_team:
            bidder = Team.query.get(player.last_bid_team)
            player.last_bid_team_name = bidder.name if bidder else "None"
        else:
            player.last_bid_team_name = "None"
            
        current_base_price = player.base_price if player and player.base_price else 100
        
        # Team list fetch karnyachi garaj aahe loop sathi
        teams = Team.query.filter_by(tournament_id=t_id).all()
        
        for t in teams:
            total_slots = 15
            sold_count = Player.query.filter_by(sold_to=t.id, tournament_id=t_id).count()
            remaining_slots = total_slots - sold_count
        
            # Max Bid Logic: Pratyek urlelya player sathi dynamic base price reserve
            if remaining_slots > 1:
                reserve = (remaining_slots - 1) * current_base_price
                t.max_allowed = t.purse - reserve
            else:
                t.max_allowed = t.purse
        
        # Current team sathi max_allowed update kara (template sathi)
        max_allowed = team.max_allowed if hasattr(team, 'max_allowed') else team.purse

    t = Tournament.query.get(t_id)  #last add error ala tr check
    return render_template(
        "bidding.html",
        player=player,
        team=team,
        t_id=t_id,
        settings=auction_settings,
        max_allowed=max_allowed,
        tournament=t
    )
# =================================================
# PLACE BID
# =================================================	
@app.route("/place-bid/<int:p_id>", methods=["POST"])
def place_bid(p_id):
    # 1. Login Check
    if "team" not in session:
        return redirect("/")

    # 2. Database Fresh करा
    db.session.expire_all()
    
    player = Player.query.get_or_404(p_id)
    
    raw_team_id = session.get('team') or session.get('team_id')
    if not raw_team_id:
        return "Please Login First", 401
    
    current_team_id = int(raw_team_id)
    team = Team.query.get(current_team_id)
    
    if not team:
        return "Team not found", 404

    # --- १५ प्लेयरची लिमिट चेक ---
    current_players_count = Player.query.filter_by(sold_to=team.id, tournament_id=player.tournament_id).count()
    
    if current_players_count >= 15:
        return "Limit Full: Your team is full", 400
    
    # 3. Back-to-Back Bid Check
    if player.last_bid_team and int(player.last_bid_team) == current_team_id:
        return "Wait for other teams to bid!", 400

    # 4. Price Calculation Logic
    settings = AuctionSettings.query.first()
    current_val = player.current_price or 0
    
    if not player.last_bid_team:
        next_bid_value = player.base_price
    else:
        if current_val < settings.limit1: inc = settings.val1
        elif current_val < settings.limit2: inc = settings.val2
        elif current_val < settings.limit3: inc = settings.val3
        else: inc = settings.val4
        
        next_bid_value = current_val + inc

    # 5. Purse and Max Allowed Check (इथे बदल केला आहे)
    required_slots = 15 - current_players_count
    
    # प्रत्येक उरलेल्या जागेसाठी १०० रुपये राखीव ठेवावे लागतात
    reserve_for_others = (required_slots - 1) * 100 if required_slots > 1 else 0
    
    # टीम जास्तीत जास्त कितीची बोली लावू शकते?
    max_allowed = team.purse - reserve_for_others

    # जर पुढची बोली टीमच्या बजेटबाहेर असेल तर "Insufficient Funds" एरर द्या
    if next_bid_value > max_allowed:
        return "Insufficient Funds: You don't have enough budget for next players", 400

    # जर पैसे शिल्लक असतील, तरच डेटाबेस अपडेट करा
    if next_bid_value <= max_allowed and team.purse >= next_bid_value:
        # 6. Database Update
        player.last_bid_team = team.id
        player.last_bid_team_name = team.name
        player.current_price = next_bid_value
        
        try:
            db.session.commit()
            db.session.expire_all() 
        except Exception as e:
            db.session.rollback()
            return f"Error: {str(e)}", 500

    return redirect(request.referrer)
#=================================================
#   REGISTRATION
#==================================================
@app.route("/register/<int:t_id>", methods=["GET", "POST"])
@login_required
def register_player(t_id):
    tournament = Tournament.query.get_or_404(t_id)
    if request.method == "POST":
        # 1. Handle Payment Screenshot
        pay_file = request.files.get('payment_ss')
        pay_filename = None
        if pay_file:
            pay_filename = secure_filename(pay_file.filename)
            pay_path = os.path.join('static/uploads/payments', pay_filename)
            
            img = Image.open(pay_file)
            img = img.convert("RGB") # PNG ला JPG सारखं ट्रिट करण्यासाठी
            img.save(pay_path, optimize=True, quality=10)

        # 2. Handle Player Photo (Auction sathi)
        photo_file = request.files.get('photo')
        photo_filename = None
        if photo_file:
            photo_filename = secure_filename(photo_file.filename)
            photo_path = os.path.join('static/uploads/players', photo_filename)
            
            img = Image.open(photo_file)
            img = img.convert("RGB")
            
            img.thumbnail((800, 800))
            
            img.save(photo_path, optimize=True, quality=10)

        # 3. Save to Registration Table
        new_reg = Registration(
            full_name=request.form.get('name'),
            address=request.form.get('address'),
            contact=request.form.get('contact'),
            role=request.form.get('role'),
            batting_style=request.form.get('bat_style'),
            bowling_style=request.form.get('bowl_style'),
            ts_name=request.form.get('ts_name'),
            ts_no=request.form.get('ts_no'),
            ts_size=request.form.get('ts_size'),
            transaction_id=request.form.get('tx_id'),
            payment_ss=pay_filename,
            photo=photo_filename, # Navin field
            tournament_id=t_id,
            status="pending"      # Default status
        )
        db.session.add(new_reg)
        db.session.commit()
        return "<h1>Registration Done! Admin will verify your payment.</h1>"
    
    return render_template("register.html", tournament=tournament)
# ====================================================
# PENDING REGISTRATIONS & APPROVAL SYSTEM
# ====================================================

# 1. Pending players chi list dakhvnyasathi
@app.route("/admin/pending/<int:t_id>")
@login_required
def pending_registrations(t_id):
    
    tournament = Tournament.query.get_or_404(t_id) 
    # Fakt 'pending' status aslele players dakhva
    pending_list = Registration.query.filter_by(tournament_id=t_id, status="pending").all()
    # FIX: Ithe t_id pathvava lagel, jyamule Modal cha URL barobar tayar hoil
    return render_template("pending_requests.html", pending_list=pending_list, t_id=t_id,tournament=tournament)

#=========================Approve button====================
# 2. Player Approve karun main table madhe pathvnyasathi

@app.route("/approve-player/<int:reg_id>", methods=['POST'])
@login_required
def approve_player(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    t_id = reg.tournament_id
    tournament = Tournament.query.get_or_404(t_id)

    # HTML Form madhun select keli Category (A ki B) ghetli
    selected_category = request.form.get('category', 'A') 

    # Category nusar tournament setting madhun base price uchela
    price = 0
    if reg.role == 'Batter': 
        price = tournament.batter_price
    elif reg.role == 'Bowler': 
        price = tournament.bowler_price
    elif reg.role == 'All-Rounder': 
        price = tournament.allrounder_price

    # Main Player Table madhe data transfer kara
    new_player = Player(
        name=reg.full_name,
        role=reg.role,
        batting_style=reg.batting_style,
        bowling_style=reg.bowling_style,
        base_price=price,
        current_price=price, # Current price pan base price set kara
        image=reg.photo,
        tournament_id=t_id,
        category=selected_category, # <--- NAVIN COLUMN ADD KELA
        status="pending",            # <--- 'pending' kara mhanje 1st round la yeil
        round=1                      # <--- Round 1 set kara
    )
    
    # Registration record 'approved' kara
    reg.status = "approved" 
    
    db.session.add(new_player)
    db.session.commit()
    
    return redirect(f"/admin/pending/{t_id}")
#==============REJECT LOGIC=================================
# 3. Reject logic (Jar payment screenshot chuki cha asel tar)
@app.route("/reject/<int:reg_id>")
@login_required
def reject_player(reg_id):
    reg = Registration.query.get_or_404(reg_id)
    t_id = reg.tournament_id
    db.session.delete(reg)
    db.session.commit()
    return redirect(f"/admin/pending/{t_id}")

#=======================================================
# IMPORT PLAYER FROM EXCEL
#===================================================
import pandas as pd # हे फाईलच्या वरती इम्पोर्ट कर

@app.route("/import-players-excel/<int:t_id>", methods=["POST"])
@login_required
def import_players_excel(t_id):
    t = Tournament.query.get_or_404(t_id)
    file = request.files.get("excel_file")
    
    if not file or file.filename == '':
        return "No file selected", 400

    try:
        # एक्सेल फाईल वाचणे
        df = pd.read_excel(file)
        
        # रिकाम्या व्हॅल्यूज (NaN) ला रिकाम्या स्ट्रिंगने बदलणे जेणेकरून एरर येणार नाही
        df = df.fillna('')

        for index, row in df.iterrows():
            new_reg = Registration(
                full_name=str(row.get('full_name', '')),
                address=str(row.get('address', '')),
                contact=str(row.get('contact', '')),
                role=str(row.get('role', '')),
                batting_style=str(row.get('bat_style', '')),
                bowling_style=str(row.get('bowl_style', '')),
                ts_name=str(row.get('ts_name', '')),
                ts_no=str(row.get('ts_no', '')),
                ts_size=str(row.get('ts_size', '')),
                transaction_id=str(row.get('tx_id', 'BULK_IMPORT')), # Bulk साठी डिफॉल्ट आयडी
                payment_ss="bulk_upload.jpg", # डमी पेमेंट स्क्रीनशॉट नाव
                photo=str(row.get('photo', '')), # तू मॅन्युअली टाकलेल्या फोटोचे नाव (उदा. vicky.jpg)
                tournament_id=t_id,
                status="pending"
            )
            db.session.add(new_reg)
        
        db.session.commit()
        return redirect(f"/admin/pending/{t_id}")

    except Exception as e:
        return f"Error: {str(e)}"
#====================================================
# DISPLAY
#====================================================
from sqlalchemy import func

@app.route("/display/<int:t_id>")
def display_page(t_id):
    return render_template("display.html", t_id=t_id)

@app.route("/display_data/<int:t_id>")
def display_data(t_id):
    # १. टूर्नामेंट माहिती (ID नुसार)
    tourney = Tournament.query.get_or_404(t_id)
    
    # २. सध्याचा प्लेयर (Bidding चालू असलेला)
    player = Player.query.filter_by(tournament_id=t_id, status='Bidding').first()
    
    # ३. टॉप प्लेयर (Most Expensive)
    top_player = Player.query.filter(
        Player.tournament_id ==t_id,
        func.lower(Player.status) == 'sold'
        ).order_by(Player.current_price.desc()).first()
    
    # ४. शेवटचा विकला गेलेला प्लेयर
    last_sold = Player.query.filter(
        Player.tournament_id == t_id,
        func.lower(Player.status) == 'sold'
        ).order_by(Player.updated_at.desc()).first()
    
    # ५. सर्व टीम्सची लिस्ट
    teams_list = []
    all_teams = Team.query.filter_by(tournament_id=t_id).all()
    for t in all_teams:
        sold_count = Player.query.filter(Player.tournament_id == t_id,
        Player.sold_to == t.id,func.lower(Player.status) == 'sold').count()
        teams_list.append({'id': t.id,
            'name': t.short_name if t.short_name else t.name,
            'players_count': sold_count,
            'remaining_points': t.purse
        })

    # ६. बिडरचे नाव
    bidder_name = "NO BID"
    if player and player.last_bid_team:
        bidder = Team.query.get(player.last_bid_team)
        bidder_name = bidder.name if bidder else "NO BID"
        
    # --- नवीन टिकर लॉजिक (SOLD + UNSOLD) ---
    recent_updates = Player.query.filter(
        Player.tournament_id == t_id, 
        Player.status.in_(['sold', 'unsold'])
    ).order_by(Player.updated_at.desc()).all()

    ticker_entries = []
    for p in recent_updates:
        if p.status == 'sold':
            team = Team.query.get(p.sold_to)
            t_name = team.short_name if team and team.short_name else "Team"
            ticker_entries.append(f"🔥 {p.name} - SOLD ({t_name} - ₹{p.current_price})")
        else:
            ticker_entries.append(f"❄️ {p.name} - UNSOLD")

    ticker_string = "  |  ".join(ticker_entries)

    return jsonify({
        'tournament_name': tourney.name,
        'tournament_logo': tourney.logo,
        'player': {
            'name': player.name if player else "WAITING...",
            'image': player.image if player else "default.jpg",
            'role': player.role if player else "-",
            'base_price': player.base_price if player else 0,
            'current_price': player.current_price if (player and player.current_price) else 0,
            'status': player.status.lower() if player else "idle",
            'round': player.round if player else 1
        },
        'bidder_name': bidder_name,
        'top_player': {
            'name': top_player.name if top_player else "None",
            'price': top_player.current_price if top_player else 0,
            'team': Team.query.get(top_player.sold_to).name if (top_player and top_player.sold_to) else "-"
        },
        'last_sold': {
            'name': last_sold.name if last_sold else "None",
            'price': last_sold.current_price if last_sold else 0,
            'team': Team.query.get(last_sold.sold_to).name if (last_sold and last_sold.sold_to) else "-"
        },
        'teams': teams_list,
        'ticker_data': ticker_string if ticker_string else "AUCTION STARTED! GET READY..."
    })
#====================================================
# auto setting page 
#====================================================
@app.route("/admin/settings", methods=["GET", "POST"])
@login_required
def admin_settings():
    
    t_id = session.get("tournament")
    settings = AuctionSettings.query.first()
    
    
    
    # Jar table madhe ekhi entry nasel tar default create kara
    if not settings:
        settings = AuctionSettings()
        db.session.add(settings)
        db.session.commit()

    if request.method == "POST":
        settings.limit1 = int(request.form.get("limit1"))
        settings.limit2 = int(request.form.get("limit2"))
        settings.limit3 = int(request.form.get("limit3"))
        settings.limit4 = int(request.form.get("limit4"))
        
        settings.val1 = int(request.form.get("val1"))
        settings.val2 = int(request.form.get("val2"))
        settings.val3 = int(request.form.get("val3"))
        settings.val4 = int(request.form.get("val4"))
        
        db.session.commit()
        return redirect("/admin/settings?success=true")

    return render_template("settings.html", settings=settings,t_id=t_id)
# =================================================
# DELETE PLAYER (PLAYER PAGE)
# =================================================
@app.route("/delete-player/<int:p_id>")
def delete_player(p_id):
    player = Player.query.get_or_404(p_id)
    t_id = player.tournament_id # Redirect sathi ID ghetla
    
    try:
        db.session.delete(player)
        db.session.commit()
        print(f"DEBUG: Player {p_id} deleted successfully")
    except Exception as e:
        db.session.rollback()
        print(f"DEBUG ERROR: {e}")
        
    return redirect(f"/players/{t_id}")
# =================================================
# player list for team page
# =================================================

@app.route("/player-list/<int:id>")
def player_for_team(id):
    tournament = Tournament.query.get_or_404(id)
    # त्या टूर्नामेंटचे सर्व प्लेयर्स मिळवा
    players = Player.query.filter_by(tournament_id=id).all()
    return render_template("player_for_team.html", tournament=tournament, players=players)
# =================================================
# T-SHIRT DETAILS
# =================================================
# HE APP.PY MADHE PAHIJE
@app.route("/tshirt-details/<int:t_id>")
@login_required
def tshirt_details(t_id):
    tournament = Tournament.query.get_or_404(t_id)
    
    # Player.name ani Registration.full_name match karun data ghyaycha
    combined_data = db.session.query(Player, Registration).join(
        Registration, Player.name == Registration.full_name
    ).filter(Player.tournament_id == t_id).all()

    teams = Team.query.filter_by(tournament_id=t_id).all()
    
    return render_template("tshirt_details.html", 
                           combined_data=combined_data, 
                           teams=teams, 
                           tournament=tournament, 
                           t_id=t_id)
    
# =================================================
# squad
# =================================================
@app.route("/all-squads/<int:t_id>")

def all_squads(t_id):
    teams = Team.query.filter_by(tournament_id=t_id).all()
    return render_template("all_teams_list.html", teams=teams, t_id=t_id)

@app.route("/squad/<int:team_id>")
def team_squad(team_id):
    # 1. Pahile ti team kontya tournament chi ahe te kadha
    team = Team.query.get_or_404(team_id)
    t_id = team.tournament_id # Tournament ID itun milto
    
    tournament_data = Tournament.query.get(t_id)
    
    # 2. Registration join madhe mismatch asu shakto, mhanun sopyat players gheu
    # Fakt 'sold_to' check kara mhanje players distil
    players = Player.query.filter_by(sold_to=team_id).all()

    # 3. Template la data pathva (teams chi list pathvnyachi garaj nahi jar ekach team baghaychi asel tar)
    return render_template("squad.html", 
                           players=players, 
                           team=team, 
                           tournament=tournament_data,
                           t_id=t_id)
    
#===============================================
# PRINT ALL SQUAD
#===============================================
@app.route("/print-all-squads/<int:t_id>")
@login_required
def print_all_squads(t_id):
    # Sagle teams ghyachya
    all_teams = Team.query.filter_by(tournament_id=t_id).all()
    
    # Pratyek team che players sobat ek list banvaychi
    full_data = []
    for team in all_teams:
        players = Player.query.filter_by(sold_to=team.id, tournament_id=t_id).all()
        full_data.append({
            'team': team,
            'players': players
        })
    
    return render_template("print_all.html", full_data=full_data, t_id=t_id)

#=================================================
# welcome
#====================================================
@app.route("/welcome/<int:t_id>")
@login_required
def welcome_page(t_id):
    tourney = Tournament.query.get_or_404(t_id)
    teams = Team.query.filter_by(tournament_id=t_id).all()
    return render_template("welcome.html", tourney=tourney, teams=teams)
# ========================================================
# Teams for bidding page
# ========================================================
@app.route("/team-squad/<int:team_id>/<int:t_id>")
def team_squad_bid(team_id, t_id):
    # १. टीम शोधा
    team = Team.query.get_or_404(team_id)
    
    # २. टूर्नामेंट डेटा मिळवा (हा ID URL मधून येतोय)
    tournament_data = Tournament.query.get(t_id)
    
    # ३. या टीमचे विकत घेतलेले प्लेयर्स (sold_to आणि tournament_id दोन्ही चेक करणे चांगले)
    players = Player.query.filter_by(
        sold_to=team_id, 
        tournament_id=t_id, 
        status='sold'
    ).all()

    return render_template("team_for_bid.html", 
                           players=players, 
                           team=team, 
                           tournament=tournament_data,
                           t_id=t_id)
   
# ========================================================
# ADMIN BID (With Security & Max Bid Logic)
# ========================================================

@app.route("/admin-place-bid/<int:p_id>/<int:t_id>", methods=["POST"])
def admin_place_bid(p_id, t_id):
    # १. डेटाबेस फ्रेश करा
    db.session.expire_all()
    
    player = Player.query.get_or_404(p_id)
    team = Team.query.get_or_404(t_id)
    
    # २. लिमिट चेक (१५ प्लेयर)
    current_players_count = Player.query.filter_by(sold_to=team.id, tournament_id=player.tournament_id).count()
    if current_players_count >= 15:
        return "Team Full", 400

    # ३. बॅक-टू-बॅक बिड चेक (त्याच टीमने पुन्हा बिड करू नये)
    if player.last_bid_team and int(player.last_bid_team) == t_id:
        return "Same Team", 400

    # ४. प्राईस कॅल्क्युलेशन (तुझं मूळ लॉजिक)
    settings = AuctionSettings.query.first()
    current_val = player.current_price or 0
    
    if not player.last_bid_team:
        next_bid_value = player.base_price
    else:
        if current_val < settings.limit1: inc = settings.val1
        elif current_val < settings.limit2: inc = settings.val2
        elif current_val < settings.limit3: inc = settings.val3
        else: inc = settings.val4
        next_bid_value = current_val + inc

    # ५. पर्स चेक
    required_slots = 15 - current_players_count
    reserve_for_others = (required_slots - 1) * 100 if required_slots > 1 else 0
    max_allowed = team.purse - reserve_for_others

    if next_bid_value <= max_allowed and team.purse >= next_bid_value:
        player.last_bid_team = team.id
        player.last_bid_team_name = team.name
        player.current_price = next_bid_value
        
        try:
            db.session.commit()
            return "Success", 200
        except Exception as e:
            db.session.rollback()
            return str(e), 500

    return "Insufficient Purse", 400
# =================================================
# RUN
# =================================================
if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
    
    

    
    