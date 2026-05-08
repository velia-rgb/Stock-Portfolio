
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///users.db", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)


def init_db():
    Base.metadata.create_all(engine)


def get_user_by_username(username):
    with SessionLocal() as session:
        return session.query(User).filter(User.username == username).first()


def create_user(username, password):
    hashed_password = generate_password_hash(password)
    user = User(username=username, password_hash=hashed_password)
    with SessionLocal() as session:
        session.add(user)
        session.commit()
        session.refresh(user)
        return user
    