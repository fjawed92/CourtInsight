import db
from models import User

# Fetch the user by username
username_to_check = 'fahad'
password_to_check = 'your_password'

user = User.query.filter_by(username=username_to_check).first()

if user:
    if user.check_password(password_to_check):
        print("Password is correct!")
    else:
        print("Password is incorrect!")
else:
    print("User not found!")
