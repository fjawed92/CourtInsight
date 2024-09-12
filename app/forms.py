# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, IntegerField, DecimalField, SelectField, DateField
from wtforms.validators import DataRequired, Optional, Email, EqualTo, ValidationError
from app.models import Team, User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')

class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField('Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user is not None:
            raise ValidationError('Please use a different email address.')

class TeamForm(FlaskForm):
    teamName = StringField('Team Name', validators=[DataRequired()])
    teamDivision = StringField('Team Division')
    teamCaptain = StringField('Team Captain')
    contactnumber = StringField('Contact Number')
    contactemail = StringField('Contact Email')
    league_id = SelectField('League', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Add Team')

class AddPlayerForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    jerseyNumber = IntegerField('Jersery Number', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired()])
    phoneNumber = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired()])
    position = StringField('Position', validators=[DataRequired()])
    weight = DecimalField('Weight', places=2, validators=[Optional()])
    height = DecimalField('Height', places=2, validators=[Optional()])
    countryOfOrigin = StringField('Country of Origin', validators=[Optional()])
    teamID = SelectField('Team', choices=[], validators=[Optional()])

class UpdatePlayerForm(FlaskForm):
    firstName = StringField('First Name', validators=[DataRequired()])
    lastName = StringField('Last Name', validators=[DataRequired()])
    age = IntegerField('Age', validators=[DataRequired()])
    phoneNumber = StringField('Phone Number', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    position = StringField('Position', validators=[DataRequired()])
    weight = DecimalField('Weight', places=2, validators=[Optional()])
    height = DecimalField('Height', places=2, validators=[Optional()])
    countryOfOrigin = StringField('Country of Origin', validators=[Optional()])
    teamID = SelectField('Team', choices=[], validators=[Optional()])

class CreateGameForm(FlaskForm):
    league = SelectField('League', validators=[DataRequired()], coerce=int)
    season = SelectField('Season', validators=[DataRequired()], coerce=int)
    gameDate = DateField('Select Date', format='%Y-%m-%d', validators=[DataRequired()])
    team1 = SelectField('Select Team 1', coerce=int, validators=[DataRequired()])
    team2 = SelectField('Select Team 2', coerce=int, validators=[DataRequired()])
    submit = SubmitField('Start Game')

    def __init__(self, *args, **kwargs):
        super(CreateGameForm, self).__init__(*args, **kwargs)
        self.team1.choices = [(team.teamID, team.teamName) for team in Team.query.all()]
        self.team2.choices = [(team.teamID, team.teamName) for team in Team.query.all()]

class CreateTeamForm(FlaskForm):
    teamName = StringField('Team Name', validators=[DataRequired()])
    submit = SubmitField('Upload Team and Players')
