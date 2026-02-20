from flask import Flask
from flask_login import LoginManager
import config
from tools import db
from tools.auth import User


def create_app():
    app = Flask(__name__)
    app.secret_key = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_FILE_SIZE

    # Flask-Login
    login_manager = LoginManager()
    login_manager.login_view = "auth.login"
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.get_by_id(user_id)

    # Init database
    db.init_db()

    # Register blueprints
    from routes import register_blueprints
    register_blueprints(app)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
