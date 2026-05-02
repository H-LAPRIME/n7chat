from app import create_app, db
from app.models.user import User

app = create_app()
with app.app_context():
    user = User.query.filter_by(email='mouadhida2005@gmail.com').first()
    if not user:
        print("USER_MISSING: Creating test user...")
        new_user = User(email='mouadhida2005@gmail.com')
        new_user.set_password('Test123456!')
        db.session.add(new_user)
        db.session.commit()
        print("USER_CREATED: Success")
    else:
        print("USER_EXISTS: Ready for test")
