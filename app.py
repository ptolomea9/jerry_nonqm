import os
import sqlite3
from flask import Flask
import config
from models import init_db, close_db


def create_app():
    app = Flask(__name__)
    app.config["SECRET_KEY"] = config.SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    # Initialize database
    init_db()

    # Auto-seed if leads table is empty (first deploy on Railway)
    conn = sqlite3.connect(config.DATABASE)
    count = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    conn.close()
    if count == 0:
        from import_csv import import_csv
        import_csv()

    # Register teardown
    app.teardown_appcontext(close_db)

    # Register blueprints
    from routes.dashboard import bp as dashboard_bp
    from routes.leads import bp as leads_bp
    from routes.lists import bp as lists_bp
    from routes.flyers import bp as flyers_bp
    from routes.outreach import bp as outreach_bp
    from routes.api import bp as api_bp
    from routes.templates import bp as templates_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(leads_bp)
    app.register_blueprint(lists_bp)
    app.register_blueprint(flyers_bp)
    app.register_blueprint(outreach_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(templates_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)
