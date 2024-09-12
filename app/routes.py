from flask import render_template, flash, redirect, url_for, request, jsonify, session
from app import app, db
from app.forms import LoginForm, RegistrationForm, TeamForm, AddPlayerForm, UpdatePlayerForm, CreateGameForm, CreateTeamForm
from app.models import User, Team, Player, Game, GameLog, BoxScore, Season, League
from flask_login import current_user, login_user, logout_user, login_required
from urllib.parse import urlparse
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc
from datetime import datetime, date
from functools import wraps


def league_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'selected_league_id' not in session:
            flash('Please select a league to continue.', 'warning')
            return redirect(url_for('index'))  # Redirect to the homepage to select a league
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
@login_required
def index():
    leagues = League.query.all()  # Fetch all available leagues from the database

    # Check if a league has already been selected in the session
    selected_league_id = session.get('selected_league_id')

    if selected_league_id:
        # If a league is selected in the session, redirect to the league dashboard
        return redirect(url_for('league_dashboard', league_id=selected_league_id))

    # If no league is selected, show the homepage with the league selection
    return render_template('index.html', leagues=leagues)


@app.route('/select_league/<int:league_id>', methods=['GET'])
@login_required
def select_league(league_id):
    # Store the selected league in the session
    session['selected_league_id'] = league_id
    session.modified = True  # Explicitly mark the session as modified

    # Redirect to the league dashboard
    return redirect(url_for('league_dashboard', league_id=league_id))

@app.route('/league_dashboard/<int:league_id>')
def league_dashboard(league_id):
    # Get the league by ID
    league = League.query.get_or_404(league_id)

    # Fetch all seasons associated with the league
    seasons = Season.query.filter_by(league_id=league_id).order_by(Season.start_date.desc()).all()

    # Determine the selected season; if none is provided, select the latest season
    selected_season_id = request.args.get('season_id', None)
    if not selected_season_id and seasons:
        selected_season_id = seasons[0].id  # Default to the latest season if not specified
    else:
        selected_season_id = int(selected_season_id)

    # Fetch games for the selected season and league
    games_query = Game.query.filter_by(season_id=selected_season_id, league_id=league_id).order_by(Game.game_date.desc())

    # Last game played
    last_game = games_query.first()

    mvp = None
    if last_game:
        mvp = db.session.query(
            Player.firstName, Player.lastName, Team.teamName, func.sum(BoxScore.points).label('total_points')
        ).select_from(BoxScore).join(Player, BoxScore.player_id == Player.playerID).join(Team, BoxScore.team_id == Team.teamID).filter(
            BoxScore.game_id == last_game.game_id
        ).group_by(Player.playerID, Team.teamID).order_by(desc('total_points')).first()

    # Calculate team standings
    teams = Team.query.filter_by(league_id=league_id).all()
    team_standings = []
    for team in teams:
        wins = games_query.filter(
            ((Game.team_1_id == team.teamID) & (Game.team_1_score > Game.team_2_score)) |
            ((Game.team_2_id == team.teamID) & (Game.team_2_score > Game.team_1_score))
        ).count()

        losses = games_query.filter(
            ((Game.team_1_id == team.teamID) & (Game.team_1_score < Game.team_2_score)) |
            ((Game.team_2_id == team.teamID) & (Game.team_2_score < Game.team_1_score))
        ).count()

        team_standings.append({
            'teamName': team.teamName,
            'wins': wins,
            'losses': losses
        })

    # Sort team standings by number of wins and assign ranking
    team_standings = sorted(team_standings, key=lambda x: x['wins'], reverse=True)
    for index, team in enumerate(team_standings):
        team['rank'] = index + 1

   # Fetch the top 5 scoring leaders for the selected season and league, including FG%
    top_scorers = db.session.query(
        Player.firstName, Player.lastName, Team.teamName,
        func.sum(BoxScore.points).label('total_points'),
        (func.sum(BoxScore.fgm) / func.sum(BoxScore.fga) * 100).label('fg_percentage')
    ).select_from(BoxScore) \
     .join(Player, BoxScore.player_id == Player.playerID) \
     .join(Team, BoxScore.team_id == Team.teamID) \
     .filter(
        BoxScore.season_id == selected_season_id,
        BoxScore.league_id == league_id,
        BoxScore.fga > 0  # Exclude players with zero field goal attempts
    ).group_by(Player.playerID, Team.teamID) \
     .order_by(desc('total_points')).limit(5).all()
    # Fetch upcoming games for the selected season
    upcoming_games = games_query.filter(Game.game_date >= datetime.now()).all()

    return render_template(
        'league_dashboard.html',
        league=league,
        seasons=seasons,
        selected_season_id=selected_season_id,
        last_game=last_game,
        team_standings=team_standings,
        upcoming_games=upcoming_games,
        top_scorers=top_scorers,
        mvp=mvp
    )

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        print(f"Login attempt for username: {form.username.data}")
        user = User.query.filter_by(username=form.username.data).first()
        print(f"User object fetched from DB: {user}")

        if user is None:
            flash('Invalid username or password')
            return redirect(url_for('login'))

        print(f"Provided password: {form.password.data}")
        print(f"Stored password hash: {user.password_hash}")
        password_check = user.check_password(form.password.data)
        print(f"Password check result: {password_check}")

        if not password_check:
            flash('Invalid username or password')
            return redirect(url_for('login'))

        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or urlparse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        print(f"Registering user: {user.username} with email: {user.email}")
        print(f"Password: {form.password.data}")
        print(f"Password hash: {user.password_hash}")
        db.session.add(user)
        db.session.commit()
        print(f'Registered user: {user.username}, {user.email}')
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Register', form=form)


@app.route('/add_team', methods=['GET', 'POST'])
@login_required
@league_required
def add_team():
    form = TeamForm()

    # Fetch all available leagues
    leagues = League.query.all()

    # Add league choices to the form dynamically
    form.league_id.choices = [(league.id, league.name) for league in leagues]

    if form.validate_on_submit():
        team = Team(
            teamName=form.teamName.data,
            teamDivision=form.teamDivision.data,
            teamCaptain=form.teamCaptain.data,
            contactnumber=form.contactnumber.data,
            contactemail=form.contactemail.data,
            league_id=form.league_id.data  # Save selected league
        )
        db.session.add(team)
        db.session.commit()
        flash('Team added successfully!')
        return redirect(url_for('index'))

    return render_template('add_team.html', title='Add Team', form=form)

@app.route('/teams')
@league_required
def teams():
    # Fetch the current league from the session
    current_league_id = session.get('selected_league_id')
    latest_season = Season.query.filter_by(league_id=current_league_id).order_by(Season.start_date.desc()).first()

    if not latest_season:
        flash("No seasons found for the current league.", "warning")
        return redirect(url_for('index'))

    # Fetch all teams for the current league
    teams = Team.query.filter_by(league_id=current_league_id).all()

    # Query all games for the current league and season
    games_query = Game.query.filter_by(season_id=latest_season.id, league_id=current_league_id)

    # Calculate wins and losses for each team
    team_stats = []
    for team in teams:
        wins = games_query.filter(
            ((Game.team_1_id == team.teamID) & (Game.team_1_score > Game.team_2_score)) |
            ((Game.team_2_id == team.teamID) & (Game.team_2_score > Game.team_1_score))
        ).count()

        losses = games_query.filter(
            ((Game.team_1_id == team.teamID) & (Game.team_1_score < Game.team_2_score)) |
            ((Game.team_2_id == team.teamID) & (Game.team_2_score < Game.team_1_score))
        ).count()

        team_stats.append({
            'team': team,
            'wins': wins,
            'losses': losses
        })

    # Sort the teams by their wins, and then by losses
    team_stats.sort(key=lambda x: (-x['wins'], x['losses']))

    return render_template('teams.html', team_stats=team_stats, latest_season=latest_season)


@app.route('/team_details/<int:team_id>')
def team_details(team_id):
    # Fetch the team by ID
    team = Team.query.get_or_404(team_id)

    # Fetch the current league and latest season
    current_league_id = session.get('selected_league_id')
    latest_season = Season.query.filter_by(league_id=current_league_id).order_by(Season.start_date.desc()).first()

    # Calculate the team's current season record and rank
    total_wins = Game.query.filter_by(season_id=latest_season.id).filter(
        ((Game.team_1_id == team_id) & (Game.team_1_score > Game.team_2_score)) |
        ((Game.team_2_id == team_id) & (Game.team_2_score > Game.team_1_score))
    ).count()

    total_losses = Game.query.filter_by(season_id=latest_season.id).filter(
        ((Game.team_1_id == team_id) & (Game.team_1_score < Game.team_2_score)) |
        ((Game.team_2_id == team_id) & (Game.team_2_score < Game.team_1_score))
    ).count()

    current_record = f"{total_wins} - {total_losses}"

    # Fetch all teams for ranking calculation
    teams_in_league = Team.query.filter_by(league_id=current_league_id).all()
    team_standings = []
    for t in teams_in_league:
        wins = Game.query.filter_by(season_id=latest_season.id).filter(
            ((Game.team_1_id == t.teamID) & (Game.team_1_score > Game.team_2_score)) |
            ((Game.team_2_id == t.teamID) & (Game.team_2_score > Game.team_1_score))
        ).count()
        losses = Game.query.filter_by(season_id=latest_season.id).filter(
            ((Game.team_1_id == t.teamID) & (Game.team_1_score < Game.team_2_score)) |
            ((Game.team_2_id == t.teamID) & (Game.team_2_score < Game.team_1_score))
        ).count()
        team_standings.append({'team': t, 'wins': wins, 'losses': losses})

    # Sort standings by wins (descending) and set rank
    team_standings.sort(key=lambda x: (-x['wins'], x['losses']))
    current_rank = next((index + 1 for index, standing in enumerate(team_standings) if standing['team'].teamID == team_id), None)

    # Fetch the last 3 games played by the team in the current season
    last_3_games = Game.query.filter_by(season_id=latest_season.id).filter(
        (Game.team_1_id == team_id) | (Game.team_2_id == team_id)
    ).order_by(Game.game_date.desc()).limit(3).all()

    # Prepare data for the chart
    game_dates = [game.game_date.strftime('%Y-%m-%d') for game in last_3_games]
    points = []
    fg_percentages = []

    # Calculate total points and FG% for each of the last three games
    for game in last_3_games:
        if game.team_1_id == team_id:
            total_points = game.team_1_score
        else:
            total_points = game.team_2_score

        # Sum the field goals made and attempted for the team in each game
        fgm = db.session.query(func.sum(BoxScore.fgm)).filter_by(game_id=game.game_id, team_id=team_id).scalar() or 0
        fga = db.session.query(func.sum(BoxScore.fga)).filter_by(game_id=game.game_id, team_id=team_id).scalar() or 0

        points.append(total_points)
        fg_percentages.append((fgm / fga) * 100 if fga > 0 else 0)

    # Fetch all box scores for the team in the current season
    box_scores = BoxScore.query.filter_by(team_id=team_id, season_id=latest_season.id).all()

    # Calculate average stats per player for the current season
    players = Player.query.filter_by(teamID=team_id).all()
    player_stats = []
    for player in players:
        # Fetch all box scores for the player
        player_box_scores = BoxScore.query.filter_by(player_id=player.playerID, season_id=latest_season.id).all()
        total_games = len(player_box_scores)
        if total_games > 0:
            avg_points = sum(bs.points for bs in player_box_scores) / total_games
            total_fgm = sum(bs.fgm for bs in player_box_scores)
            total_fga = sum(bs.fga for bs in player_box_scores)
            fg_percentage = (total_fgm / total_fga) * 100 if total_fga > 0 else 0
            player_stats.append({
                'firstName': player.firstName,
                'lastName': player.lastName,
                'jersey_number': player.jerseyNumber,
                'avg_points': avg_points,
                'fg_percentage': fg_percentage
            })

    # Fetch games played by the team in the current season
    games = Game.query.filter_by(season_id=latest_season.id).filter(
        (Game.team_1_id == team_id) | (Game.team_2_id == team_id)
    ).order_by(Game.game_date.desc()).all()

    # Prepare game history data
    games_history = []
    for game in games:
        if game.team_1_id == team_id:
            opponent = game.team2.teamName
            team_score = game.team_1_score
            opponent_score = game.team_2_score
        else:
            opponent = game.team1.teamName
            team_score = game.team_2_score
            opponent_score = game.team_1_score

        result = 'Win' if team_score > opponent_score else 'Loss'
        games_history.append({
            'date_played': game.game_date.strftime('%Y-%m-%d'),
            'opponent': opponent,
            'team_score': team_score,
            'opponent_score': opponent_score,
            'result': result,
            'game_id': game.game_id  # Include the game_id for linking
        })

    return render_template('team_details.html', team=team, box_scores=box_scores, game_dates=game_dates, points=points, fg_percentages=fg_percentages, player_stats=player_stats, latest_season=latest_season, games_history=games_history, current_record=current_record, current_rank=current_rank)


@app.route('/players')
@login_required
@league_required
def players():
    all_players = Player.query.all()  # Fetch all players from the database
    return render_template('players.html', players=all_players)

@app.route('/add_player', methods=['GET', 'POST'])
@login_required
@league_required
def add_player():
    form = AddPlayerForm()

    # Populate the teamID choices dynamically
    form.teamID.choices = [('', 'Select a Team')] + [(team.teamID, team.teamName) for team in Team.query.all()]

    if form.validate_on_submit():
        player = Player(
            firstName=form.firstName.data,
            lastName=form.lastName.data,
            jerseyNumber = form.jerseyNumber.data,
            age=form.age.data,
            phoneNumber=form.phoneNumber.data,
            email=form.email.data,
            position=form.position.data,
            weight=form.weight.data,
            height=form.height.data,
            countryOfOrigin=form.countryOfOrigin.data,
            teamID=int(form.teamID.data) if form.teamID.data else None
        )
        db.session.add(player)
        db.session.commit()
        flash('Player added successfully!', 'success')
        return redirect(url_for('players'))

    return render_template('add_player.html', form=form)

@app.route('/update_player/<int:player_id>', methods=['GET', 'POST'])
@login_required
@league_required
def update_player(player_id):
    player = Player.query.get_or_404(player_id)
    form = UpdatePlayerForm()

    # Populate the teamID choices dynamically
    form.teamID.choices = [('', 'Select a Team')] + [(str(team.teamID), team.teamName) for team in Team.query.all()]

    if form.validate_on_submit():
        try:
            player.firstName = form.firstName.data
            player.lastName = form.lastName.data
            player.age = form.age.data
            player.phoneNumber = form.phoneNumber.data
            player.email = form.email.data
            player.position = form.position.data
            player.weight = form.weight.data
            player.height = form.height.data
            player.countryOfOrigin = form.countryOfOrigin.data
            player.teamID = int(form.teamID.data) if form.teamID.data else None

            print(f"Updating Player: {player.firstName}, {player.lastName}, {player.age}, {player.phoneNumber}, {player.email}, {player.position}, {player.weight}, {player.height}, {player.countryOfOrigin}, {player.teamID}")

            db.session.commit()
            flash('Player updated successfully!', 'success')
            return redirect(url_for('players'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating player: {str(e)}', 'danger')
    elif request.method == 'GET':
        form.firstName.data = player.firstName
        form.lastName.data = player.lastName
        form.age.data = player.age
        form.phoneNumber.data = player.phoneNumber
        form.email.data = player.email
        form.position.data = player.position
        form.weight.data = player.weight
        form.height.data = player.height
        form.countryOfOrigin.data = player.countryOfOrigin
        form.teamID.data = str(player.teamID) if player.teamID else ''

    return render_template('update_players.html', form=form, player=player)

@app.route('/quick_upload', methods=['GET', 'POST'])
@login_required
@league_required
def quick_upload():
    form = CreateTeamForm()  # Instantiate the form

    if request.method == 'POST':
        team_name = form.teamName.data

        # Check if the team name is provided
        if not team_name:
            flash('Please enter a team name.', 'danger')
            return redirect(url_for('quick_upload'))

        # Create and save the new team
        new_team = Team(teamName=team_name)
        db.session.add(new_team)
        db.session.commit()  # Commit to get the team ID

        # Loop through the 10 possible player entries
        for i in range(10):
            first_name = request.form.get(f'firstName{i}')
            last_name = request.form.get(f'lastName{i}')
            jersey_number = request.form.get(f'jerseyNumber{i}')

            if first_name and last_name and jersey_number:
                # Create and save the player
                new_player = Player(
                    firstName=first_name,
                    lastName=last_name,
                    jerseyNumber=int(jersey_number),
                    teamID=new_team.teamID
                )
                db.session.add(new_player)

        # Commit all the players to the database
        db.session.commit()

        flash(f'Team {team_name} and players uploaded successfully!', 'success')
        return redirect(url_for('teams'))  # Replace with the appropriate redirect

    return render_template('quick_upload.html', form=form)  # Pass the form to the template

@app.route('/create_game', methods=['GET', 'POST'])
@login_required
def create_game():
    form = CreateGameForm()

    # Fetch the current league and the latest season
    current_league_id = session.get('selected_league_id')
    current_league = League.query.get_or_404(current_league_id)
    seasons = Season.query.filter_by(league_id=current_league_id).order_by(Season.start_date.desc()).all()
    latest_season_id = seasons[0].id if seasons else None

    # Populate league and season choices in the form
    form.league.choices = [(current_league.id, current_league.name)]
    form.season.choices = [(season.id, season.name) for season in seasons]

    # Fetch teams for the selected league
    teams = Team.query.filter_by(league_id=current_league_id).all()
    form.team1.choices = [(team.teamID, team.teamName) for team in teams]
    form.team2.choices = [(team.teamID, team.teamName) for team in teams]

    # Set default values for league and season
    form.league.default = current_league_id
    form.season.default = latest_season_id

    # Fetch scheduled games for the current league and season
    scheduled_games = Game.query.filter_by(scheduled_played='Scheduled', league_id=current_league_id, season_id=latest_season_id).all()

    if form.validate_on_submit():
        # Check if a scheduled game is selected
        selected_game_id = request.form.get('scheduled_game')

        if selected_game_id:
            # Update the selected scheduled game to "Ongoing"
            game = Game.query.get_or_404(int(selected_game_id))
            game.scheduled_played = 'Ongoing'
            game.game_date = form.gameDate.data  # Update game date if needed
        else:
            # Create a new game manually
            game = Game(
                game_date=form.gameDate.data,
                team_1_id=form.team1.data,
                team_2_id=form.team2.data,
                league_id=current_league_id,
                season_id=form.season.data,
                scheduled_played='Ongoing'  # Mark the game as ongoing
            )
            db.session.add(game)

        db.session.commit()
        flash('Game started successfully!', 'success')
        return redirect(url_for('game_actions', game_id=game.game_id))

    # Set default date to today's date
    if request.method == 'GET':
        form.gameDate.data = date.today()

    return render_template('create_game.html', form=form, scheduled_games=scheduled_games)

@app.route('/schedule_game', methods=['GET', 'POST'])
@login_required
@league_required
def schedule_game():
    # Fetch the current league and the latest season
    current_league_id = session.get('selected_league_id')
    current_league = League.query.get_or_404(current_league_id)
    seasons = Season.query.filter_by(league_id=current_league_id).order_by(Season.start_date.desc()).all()
    latest_season_id = seasons[0].id if seasons else None

    if request.method == 'POST':
        team1_id = request.form['team1']
        team2_id = request.form['team2']
        game_date = request.form['game_date']
        selected_season_id = request.form['season']

        # Create a new Game instance with 'Scheduled' status
        new_game = Game(
            game_date=game_date,
            team_1_id=team1_id,
            team_2_id=team2_id,
            league_id=current_league_id,
            season_id=selected_season_id,
            scheduled_played='Scheduled'  # Defaulting to 'Scheduled' when creating a new game
        )

        # Add the new game to the database and commit
        db.session.add(new_game)
        db.session.commit()

        # Flash a success message and redirect to a summary or another page
        flash('Game successfully scheduled!', 'success')
        return redirect(url_for('game_summary', game_id=new_game.game_id))

    # Get all teams for the current league to populate the dropdowns in the form
    teams = Team.query.filter_by(league_id=current_league_id).all()

    return render_template(
        'schedule_game.html',
        teams=teams,
        current_league=current_league,
        seasons=seasons,
        latest_season_id=latest_season_id
    )


@app.route('/view_games')
@login_required
@league_required
def view_games():
    scheduled_games = Game.query.filter_by(scheduled_played='Scheduled').all()
    ongoing_games = Game.query.filter_by(scheduled_played='Ongoing').all()
    completed_games = Game.query.filter_by(scheduled_played='Played').all()

    return render_template('view_games.html',
                           scheduled_games=scheduled_games,
                           ongoing_games=ongoing_games,
                           completed_games=completed_games)


@app.route('/game_details/<int:game_id>', methods=['GET'])
@login_required
@league_required
def game_details(game_id):
    game = Game.query.get_or_404(game_id)
    team1_players = Player.query.filter_by(teamID=game.team_1_id).all()
    team2_players = Player.query.filter_by(teamID=game.team_2_id).all()

    # Fetch the last 10 entries from the gamelog table
    last_entries = GameLog.query.filter_by(gameid=game_id).order_by(GameLog.gamelogdatetime.desc()).limit(100).all()

    # Fetch box scores for each team
    team1_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_1_id).all()
    team2_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_2_id).all()

    return render_template(
        'game_details.html',
        game=game,
        team1_players=team1_players,
        team2_players=team2_players,
        last_entries=last_entries,
        team1_box_scores=team1_box_scores,
        team2_box_scores=team2_box_scores
    )


# Route for the game actions and timer
@app.route('/game_actions/<int:game_id>', methods=['GET'])
@login_required
@league_required
def game_actions(game_id):
    game = Game.query.get_or_404(game_id)
    team1_players = Player.query.filter_by(teamID=game.team_1_id).all()
    team2_players = Player.query.filter_by(teamID=game.team_2_id).all()

    # Fetch team 1 box score and total points
    team1_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_1_id).all()
    team1_total_points = sum([box.points for box in team1_box_scores])

    # Fetch team 2 box score and total points
    team2_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_2_id).all()
    team2_total_points = sum([box.points for box in team2_box_scores])

    return render_template('game_actions.html',
                           game=game,
                           team1_players=team1_players,
                           team2_players=team2_players,
                           team1_box_scores=team1_box_scores,
                           team2_box_scores=team2_box_scores,
                           team1_total_points=team1_total_points,
                           team2_total_points=team2_total_points)

@app.route('/refresh_box_scores/<int:game_id>', methods=['GET'])
@login_required
@league_required
def refresh_box_scores(game_id):
    game = Game.query.get_or_404(game_id)

    # Fetch team 1 box score and total points
    team1_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_1_id).all()
    team1_total_points = sum([box.points for box in team1_box_scores])

    # Fetch team 2 box score and total points
    team2_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_2_id).all()
    team2_total_points = sum([box.points for box in team2_box_scores])

    # Render the box scores to HTML strings
    team1_html = render_template('partials/team_box_score.html', box_scores=team1_box_scores, total_points=team1_total_points)
    team2_html = render_template('partials/team_box_score.html', box_scores=team2_box_scores, total_points=team2_total_points)

    return jsonify({
        'team1_html': team1_html,
        'team2_html': team2_html,
        'team1_total_points': team1_total_points,
        'team2_total_points': team2_total_points
    })



@app.route('/game_summary/<int:game_id>', methods=['GET'])
@login_required
@league_required
def game_summary(game_id):
    game = Game.query.get_or_404(game_id)

    # Fetch the box scores for both teams
    team1_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_1_id).all()
    team2_box_scores = BoxScore.query.filter_by(game_id=game_id, team_id=game.team_2_id).all()

    # Calculate total points for each team
    team1_total_points = sum(box.points for box in team1_box_scores)
    team2_total_points = sum(box.points for box in team2_box_scores)

    def calculate_percentage(made, attempted):
        if attempted > 0:
            return round((made / attempted) * 100, 1)
        return 0.0

    # Calculate totals and percentages for Team 1
    team1_totals = {
        'fga': sum(box.fga for box in team1_box_scores),
        'fgm': sum(box.fgm for box in team1_box_scores),
        'three_fga': sum(box.three_fga for box in team1_box_scores),
        'three_fgm': sum(box.three_fgm for box in team1_box_scores),
        'fta': sum(box.fta for box in team1_box_scores),
        'ftm': sum(box.ftm for box in team1_box_scores),
        'oreb': sum(box.oreb for box in team1_box_scores),
        'dreb': sum(box.dreb for box in team1_box_scores),
        'reb': sum(box.oreb + box.dreb for box in team1_box_scores),
        'ast': sum(box.assists for box in team1_box_scores),
        'stl': sum(box.steals for box in team1_box_scores),
        'blk': sum(box.blocks for box in team1_box_scores),
        'to': sum(box.turnovers for box in team1_box_scores),
        'pf': sum(box.fouls for box in team1_box_scores),
        'pts': sum(box.points for box in team1_box_scores),
        'fg_percent': calculate_percentage(sum(box.fgm for box in team1_box_scores), sum(box.fga for box in team1_box_scores)),
        'three_fg_percent': calculate_percentage(sum(box.three_fgm for box in team1_box_scores), sum(box.three_fga for box in team1_box_scores)),
    }

    # Calculate totals and percentages for Team 2
    team2_totals = {
        'fga': sum(box.fga for box in team2_box_scores),
        'fgm': sum(box.fgm for box in team2_box_scores),
        'three_fga': sum(box.three_fga for box in team2_box_scores),
        'three_fgm': sum(box.three_fgm for box in team2_box_scores),
        'fta': sum(box.fta for box in team2_box_scores),
        'ftm': sum(box.ftm for box in team2_box_scores),
        'oreb': sum(box.oreb for box in team2_box_scores),
        'dreb': sum(box.dreb for box in team2_box_scores),
        'reb': sum(box.oreb + box.dreb for box in team2_box_scores),
        'ast': sum(box.assists for box in team2_box_scores),
        'stl': sum(box.steals for box in team2_box_scores),
        'blk': sum(box.blocks for box in team2_box_scores),
        'to': sum(box.turnovers for box in team2_box_scores),
        'pf': sum(box.fouls for box in team2_box_scores),
        'pts': sum(box.points for box in team2_box_scores),
        'fg_percent': calculate_percentage(sum(box.fgm for box in team2_box_scores), sum(box.fga for box in team2_box_scores)),
        'three_fg_percent': calculate_percentage(sum(box.three_fgm for box in team2_box_scores), sum(box.three_fga for box in team2_box_scores)),
    }

    # Calculate percentages for individual players
    for box in team1_box_scores + team2_box_scores:
        box.fg_percent = calculate_percentage(box.fgm, box.fga)
        box.three_fg_percent = calculate_percentage(box.three_fgm, box.three_fga)

    # Fetch the last 10 entries from the game log table
    last_entries = GameLog.query.filter_by(gameid=game_id).order_by(GameLog.gamelogdatetime.desc()).limit(100).all()

    return render_template('game_summary.html', game=game,
                           team1_box_scores=team1_box_scores,
                           team2_box_scores=team2_box_scores,
                           last_entries=last_entries,
                           team1_total_points=team1_total_points,
                           team2_total_points=team2_total_points,
                           team1_totals=team1_totals,
                           team2_totals=team2_totals)



@app.route('/log_action', methods=['POST'])
@login_required
@league_required
def log_action():
    data = request.get_json()
    try:
        log_entry = GameLog(
            gameid=data['gameid'],
            teamid=data['teamid'],
            playerid=data['playerid'],
            actiontype=data['actiontype'],
            action=data['action'],
            actiondesc=data['actiondesc'],
            currenttimer=data['currenttimer'],
            gamelogdatetime=datetime.now()
        )
        db.session.add(log_entry)
        db.session.commit()
        return jsonify({'status': 'success'})
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)})

@app.route('/update_boxscore', methods=['POST'])
@login_required
@league_required
def update_boxscore():
    try:
        # Fetch current league from session
        current_league_id = session.get('selected_league_id')
        if not current_league_id:
            return jsonify({'status': 'error', 'message': 'League not found in session.'}), 400

        # Fetch the latest season for the current league
        latest_season = Season.query.filter_by(league_id=current_league_id).order_by(Season.start_date.desc()).first()
        if not latest_season:
            return jsonify({'status': 'error', 'message': 'No season found for the current league.'}), 400

        # Parse JSON data
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': 'Invalid or missing JSON data.'}), 400

        game_id = data.get('game_id')
        team_id = data.get('team_id')
        player_id = data.get('player_id')
        action = data.get('action')

        # Validate required fields
        if not all([game_id, team_id, player_id, action]):
            return jsonify({'status': 'error', 'message': 'Missing required fields.'}), 400

        # Fetch the game to get the game date
        game = Game.query.get_or_404(game_id)
        game_date = game.game_date

        # Fetch or create the BoxScore entry for the game, team, and player
        box_score = BoxScore.query.filter_by(game_id=game_id, team_id=team_id, player_id=player_id).first()
        if not box_score:
            box_score = BoxScore(
                game_id=game_id,
                team_id=team_id,
                player_id=player_id,
                league_id=current_league_id,
                season_id=latest_season.id,
                date_played=game_date,  # Set date_played from game date
                fga=0, fgm=0, three_fga=0, three_fgm=0, fta=0, ftm=0,
                oreb=0, dreb=0, assists=0, steals=0, blocks=0, turnovers=0, fouls=0, points=0
            )
            db.session.add(box_score)

        # Dictionary to map actions to their corresponding updates
        action_map = {
            '2-Point Made': lambda bs: (setattr(bs, 'fga', (bs.fga or 0) + 1), setattr(bs, 'fgm', (bs.fgm or 0) + 1), setattr(bs, 'points', (bs.points or 0) + 2)),
            '2-Point Miss': lambda bs: setattr(bs, 'fga', (bs.fga or 0) + 1),
            '3-Point Made': lambda bs: (setattr(bs, 'fga', (bs.fga or 0) + 1), setattr(bs, 'fgm', (bs.fgm or 0) + 1), setattr(bs, 'three_fga', (bs.three_fga or 0) + 1), setattr(bs, 'three_fgm', (bs.three_fgm or 0) + 1), setattr(bs, 'points', (bs.points or 0) + 3)),
            '3-Point Miss': lambda bs: (setattr(bs, 'fga', (bs.fga or 0) + 1), setattr(bs, 'three_fga', (bs.three_fga or 0) + 1)),
            'FT Made': lambda bs: (setattr(bs, 'fta', (bs.fta or 0) + 1), setattr(bs, 'ftm', (bs.ftm or 0) + 1), setattr(bs, 'points', (bs.points or 0) + 1)),
            'FT Miss': lambda bs: setattr(bs, 'fta', (bs.fta or 0) + 1),
            'Offensive Rebound': lambda bs: setattr(bs, 'oreb', (bs.oreb or 0) + 1),
            'Defensive Rebound': lambda bs: setattr(bs, 'dreb', (bs.dreb or 0) + 1),
            'Assist': lambda bs: setattr(bs, 'assists', (bs.assists or 0) + 1),
            'Steal': lambda bs: setattr(bs, 'steals', (bs.steals or 0) + 1),
            'Block': lambda bs: setattr(bs, 'blocks', (bs.blocks or 0) + 1),
            'Turnover': lambda bs: setattr(bs, 'turnovers', (bs.turnovers or 0) + 1),
            'Foul': lambda bs: setattr(bs, 'fouls', (bs.fouls or 0) + 1)
        }

        # Apply the action if it's in the action map
        if action in action_map:
            action_map[action](box_score)

        # Commit the changes to the database
        db.session.commit()

        return jsonify({'status': 'success', 'message': 'BoxScore updated successfully.'})

    except SQLAlchemyError as e:
        # Log the exception and return a server error response
        app.logger.error(f"SQLAlchemyError in update_boxscore: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'An internal server error occurred.'}), 500

    except Exception as e:
        # Log the exception and return a server error response
        app.logger.error(f"Error in update_boxscore: {str(e)}")
        db.session.rollback()
        return jsonify({'status': 'error', 'message': 'An internal server error occurred.'}), 500


@app.route('/end_game', methods=['POST'])
@login_required
@league_required
def end_game():
    game_id = request.json['game_id']

    # Fetch the game
    game = Game.query.get_or_404(game_id)

    # Update the game status
    game.scheduled_played = 'Played'

    # Calculate the final scores
    team_1_score = db.session.query(db.func.sum(BoxScore.points)).filter_by(game_id=game_id, team_id=game.team_1_id).scalar() or 0
    team_2_score = db.session.query(db.func.sum(BoxScore.points)).filter_by(game_id=game_id, team_id=game.team_2_id).scalar() or 0

    game.team_1_score = team_1_score
    game.team_2_score = team_2_score

    # Determine the winning team
    if team_1_score > team_2_score:
        game.team_won = game.team_1_id
    elif team_2_score > team_1_score:
        game.team_won = game.team_2_id
    else:
        game.team_won = None  # Handle tie if applicable

    # Commit the changes to the database
    db.session.commit()

    return jsonify({'status': 'success', 'message': 'Game ended and scores updated.'})

