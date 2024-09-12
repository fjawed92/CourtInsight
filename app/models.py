from datetime import datetime, date
from app import db, login
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    role = db.Column(db.Enum('admin', 'captain', 'player'), default='player')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password, method='pbkdf2:sha256')

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f'<User {self.username}>'

@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class Team(db.Model):
    __tablename__ = 'teams'
    teamID = db.Column(db.Integer, primary_key=True)
    teamName = db.Column(db.String(100), nullable=False)
    teamDivision = db.Column(db.String(100), nullable=True)
    teamCaptain = db.Column(db.String(100), nullable=True)
    contactnumber = db.Column(db.String(15), nullable=True)
    contactemail = db.Column(db.String(100), nullable=True)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=True)  # Foreign key to League

    # Relationship
    league = db.relationship('League', backref=db.backref('teams', lazy=True))


class Player(db.Model):
    __tablename__ = 'player'
    playerID = db.Column(db.Integer, primary_key=True)
    firstName = db.Column(db.String(100), nullable=False)
    lastName = db.Column(db.String(100), nullable=False)
    jerseyNumber = db.Column(db.Integer, nullable=False)
    age = db.Column(db.Integer, nullable=True)
    phoneNumber = db.Column(db.String(15), nullable=True)
    email = db.Column(db.String(100), nullable=True)
    position = db.Column(db.String(50), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    countryOfOrigin = db.Column(db.String(100), nullable=True)
    teamID = db.Column(db.Integer, db.ForeignKey('teams.teamID'))
    team = db.relationship('Team', backref='player', lazy=True)

class BoxScore(db.Model):
    __tablename__ = 'box_scores'
    box_score_id = db.Column(db.Integer, primary_key=True)
    date_played = db.Column(db.Date, nullable=False)
    game_id = db.Column(db.Integer, nullable=False)
    player_id = db.Column(db.Integer, db.ForeignKey('player.playerID'), nullable=False)
    team_id = db.Column(db.Integer, db.ForeignKey('teams.teamID'), nullable=False)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)  # Foreign key to League
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'), nullable=False)  # Foreign key to Season
    fga = db.Column(db.Integer, nullable=False, default=0)  # Field Goals Attempted
    fgm = db.Column(db.Integer, nullable=False, default=0)  # Field Goals Made
    three_fga = db.Column(db.Integer, nullable=False, default=0)  # Three-point Field Goals Attempted
    three_fgm = db.Column(db.Integer, nullable=False, default=0)  # Three-point Field Goals Made
    fta = db.Column(db.Integer, nullable=False, default=0)  # Free Throws Attempted
    ftm = db.Column(db.Integer, nullable=False, default=0)  # Free Throws Made
    oreb = db.Column(db.Integer, nullable=False, default=0)  # Offensive Rebounds
    dreb = db.Column(db.Integer, nullable=False, default=0)  # Defensive Rebounds
    assists = db.Column(db.Integer, nullable=False, default=0)
    steals = db.Column(db.Integer, nullable=False, default=0)
    blocks = db.Column(db.Integer, nullable=False, default=0)
    turnovers = db.Column(db.Integer, nullable=False, default=0)
    fouls = db.Column(db.Integer, nullable=False, default=0)
    points = db.Column(db.Integer, nullable=False, default=0)

    # Define relationships
    player = db.relationship('Player', backref=db.backref('box_scores', lazy=True))
    team = db.relationship('Team', backref=db.backref('box_scores', lazy=True))

    def __repr__(self):
        return f'<BoxScore {self.box_score_id} - Game {self.game_id} - Player {self.player_id}>'




class Game(db.Model):
    __tablename__ = 'games'
    game_id = db.Column(db.Integer, primary_key=True)
    game_date = db.Column(db.Date, nullable=False)
    team_1_id = db.Column(db.Integer, db.ForeignKey('teams.teamID'), nullable=False)
    team_2_id = db.Column(db.Integer, db.ForeignKey('teams.teamID'), nullable=False)
    team_1_score = db.Column(db.Integer, nullable=False, default=0)
    team_2_score = db.Column(db.Integer, nullable=False, default=0)
    team_won = db.Column(db.Integer, db.ForeignKey('teams.teamID'))
    scheduled_played = db.Column(db.String(10), nullable=False, default='Scheduled')
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'))
    season_id = db.Column(db.Integer, db.ForeignKey('seasons.id'))

    # Define relationships
    team1 = db.relationship('Team', foreign_keys=[team_1_id], backref=db.backref('team_1_games', lazy=True))
    team2 = db.relationship('Team', foreign_keys=[team_2_id], backref=db.backref('team_2_games', lazy=True))
    winning_team = db.relationship('Team', foreign_keys=[team_won], backref=db.backref('won_games', lazy=True))

    def __repr__(self):
        return f'<Game {self.game_id} - {self.team_1_id} vs {self.team_2_id}>'


class GameLog(db.Model):
    __tablename__ = 'gamelog'

    gamelogid = db.Column(db.Integer, primary_key=True, autoincrement=True)
    gameid = db.Column(db.Integer, nullable=False)
    teamid = db.Column(db.Integer)
    playerid = db.Column(db.Integer)
    actiontype = db.Column(db.String(50))
    action = db.Column(db.String(50))
    actiondesc = db.Column(db.Text)
    currenttimer = db.Column(db.Time)
    gamelogdatetime = db.Column(db.DateTime)

    def __repr__(self):
        return f'<GameLog {self.gamelogid}>'


class League(db.Model):
    __tablename__ = 'leagues'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)

    # Relationship with Season
    seasons = db.relationship('Season', backref='league', lazy=True)
    games = db.relationship('Game', backref='league', lazy=True)


class Season(db.Model):
    __tablename__ = 'seasons'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    league_id = db.Column(db.Integer, db.ForeignKey('leagues.id'), nullable=False)

    # Relationship with Game
    games = db.relationship('Game', backref='seasons', lazy=True)

