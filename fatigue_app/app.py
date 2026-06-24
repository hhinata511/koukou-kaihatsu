from flask import Flask
from config import Config
from models import db, User, Setting


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)

    # Register blueprints
    from routes.main import main_bp
    from routes.records import records_bp
    from routes.settings import settings_bp
    from routes.analysis import analysis_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(records_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(analysis_bp)

    return app


def init_db():
    """Initialize the database and create default data if needed."""
    app = create_app()
    with app.app_context():
        db.create_all()
        # Create default user if not exists
        if User.query.count() == 0:
            user = User(name='Default User', average_sleep=7.5)
            db.session.add(user)
            db.session.commit()

            setting = Setting(
                user_id=user.id,
                weekly_safe_threshold=49.0,
                weekly_warning_threshold=50.0,
                weekly_danger_threshold=80.0
            )
            db.session.add(setting)
            db.session.commit()

    return app


if __name__ == '__main__':
    from sys import argv

    if len(argv) > 1 and argv[1] == 'init_db':
        app = init_db()
        print('Database initialized successfully.')
    else:
        app = init_db()
        app.run(debug=True)