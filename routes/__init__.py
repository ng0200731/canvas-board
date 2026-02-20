def register_blueprints(app):
    from routes.auth_routes import auth_bp
    from routes.board_routes import board_bp
    from routes.api import api_bp
    from routes.share_routes import share_bp
    from routes.email_routes import email_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(board_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(share_bp)
    app.register_blueprint(email_bp)

