import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or '785b430dd68855c292a2872b2909a08a762af370cd2d83cb'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'mysql+pymysql://courtinsights:Fahnam0310@courtinsights.mysql.pythonanywhere-services.com/courtinsights$league'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    ADMINS = ['mjfahad1012@gmail.com']
