from app import app,db,Users
import os
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
load_dotenv()

admin_password=os.getenv("admin_password")
admin_email=os.getenv("admin_email")

with app.app_context():
    db.create_all()
    existing=Users.query.filter_by(email=admin_email).first()
    if not existing:
       admin=Users(
         name="admin",
         email=admin_email,
         password=generate_password_hash(admin_password),
         role="admin"
        )
       db.session.add(admin)
       db.session.commit()

       