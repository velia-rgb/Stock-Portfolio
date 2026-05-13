
from pathlib import Path
import requests
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Float, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from datetime import datetime
# import requestsusers.db

DB_PATH = Path(__file__).resolve().parent / "users.db"
engine = create_engine(f"sqlite:///{DB_PATH}", echo=False, future=True)
SessionLocal = sessionmaker(bind=engine, future=True, expire_on_commit=False)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String(80), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)
    portfolios = relationship("Portfolio", back_populates="user", cascade="all, delete-orphan")

class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(100), nullable=False)
    cash = Column(Float, nullable=False, default=0.0)
    holdings = relationship("Holding", back_populates="portfolio", cascade="all, delete-orphan")
    transactions = relationship("Transaction", back_populates="portfolio", cascade="all, delete-orphan")

    user = relationship("User", back_populates="portfolios")

class Holding(Base):
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    shares = Column(Integer, nullable=False, default=0)
    avg_price = Column(Float, nullable=False, default=0.0)

    portfolio = relationship("Portfolio", back_populates="holdings")

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False)
    symbol = Column(String(20), nullable=False)
    shares = Column(Integer, nullable=False)
    price = Column(Float, nullable=False)
    cost_basis = Column(Float, nullable=True)  # For sells, the avg price at time of sell
    type = Column(String(10), nullable=False)
    timestamp = Column(DateTime, nullable=False, default=datetime.utcnow)

    portfolio = relationship("Portfolio", back_populates="transactions")


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


def get_portfolios_for_user(user_id):
    with SessionLocal() as session:
        return session.query(Portfolio).filter(Portfolio.user_id == user_id).all()


def create_portfolio_db(user_id, name, cash=0.0):
    portfolio = Portfolio(user_id=user_id, name=name, cash=cash)
    with SessionLocal() as session:
        session.add(portfolio)
        session.commit()
        session.refresh(portfolio)
        return portfolio


def get_portfolio(portfolio_id):
    with SessionLocal() as session:
        return session.query(Portfolio).filter(Portfolio.id == portfolio_id).first()


def get_holdings_for_portfolio(portfolio_id):
    with SessionLocal() as session:
        return session.query(Holding).filter(Holding.portfolio_id == portfolio_id).all()


def get_transactions_for_portfolio(portfolio_id):
    with SessionLocal() as session:
        return session.query(Transaction).filter(Transaction.portfolio_id == portfolio_id).order_by(Transaction.timestamp.desc()).all()


def get_holding(portfolio_id, symbol):
    with SessionLocal() as session:
        return session.query(Holding).filter(Holding.portfolio_id == portfolio_id, Holding.symbol == symbol.upper()).first()


def upsert_holding(portfolio_id, symbol, shares, price):
    symbol = symbol.upper()
    with SessionLocal() as session:
        holding = session.query(Holding).filter(Holding.portfolio_id == portfolio_id, Holding.symbol == symbol).first()
        if holding:
            total_shares = holding.shares + shares
            if total_shares <= 0:
                session.delete(holding)
            else:
                cost_basis = holding.avg_price * holding.shares + price * shares
                holding.shares = total_shares
                holding.avg_price = cost_basis / total_shares
        else:
            holding = Holding(portfolio_id=portfolio_id, symbol=symbol, shares=shares, avg_price=price)
            session.add(holding)
        session.commit()
        return holding


def sell_holding(portfolio_id, symbol, shares):
    symbol = symbol.upper()
    with SessionLocal() as session:
        holding = session.query(Holding).filter(Holding.portfolio_id == portfolio_id, Holding.symbol == symbol).first()
        if not holding or shares <= 0 or shares > holding.shares:
            return None
        remaining = holding.shares - shares
        if remaining == 0:
            session.delete(holding)
        else:
            holding.shares = remaining
        session.commit()
        return holding


def record_transaction(portfolio_id, symbol, shares, price, type_, cost_basis=None):
    symbol = symbol.upper()
    transaction = Transaction(portfolio_id=portfolio_id, symbol=symbol, shares=shares, price=price, type=type_, cost_basis=cost_basis)
    with SessionLocal() as session:
        session.add(transaction)
        session.commit()
        session.refresh(transaction)
        return transaction


def get_current_price(symbol):
    symbol = symbol.strip().upper()
    if not symbol:
        return None

    # Try Yahoo Finance first
    try:
        url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbol}"
        response = requests.get(url, timeout=5, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response.raise_for_status()
        data = response.json()
        results = data.get("quoteResponse", {}).get("result", [])
        if results:
            price = results[0].get("regularMarketPrice")
            if price is not None:
                return float(price)
    except requests.RequestException:
        pass

    # Fallback to Financial Modeling Prep (free tier)
    try:
        url = f"https://financialmodelingprep.com/api/v3/quote/{symbol}?apikey=demo"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        if data and isinstance(data, list) and len(data) > 0:
            price = data[0].get("price")
            if price is not None:
                return float(price)
    except requests.RequestException:
        pass

    # Last fallback: Mock prices for common stocks (for demo purposes)
    mock_prices = {
        'AAPL': 175.43,
        'GOOGL': 141.80,
        'MSFT': 407.77,
        'AMZN': 178.35,
        'TSLA': 248.42,
        'NVDA': 135.40,
        'META': 484.10,
        'NFLX': 689.45
    }

    return mock_prices.get(symbol)

def delete_portfolio_db(portfolio_id):
    with SessionLocal() as session:
        portfolio = session.query(Portfolio).filter(
            Portfolio.id == portfolio_id
        ).first()

        if portfolio:
            session.delete(portfolio)
            session.commit()
            return True
    return False

def update_portfolio_name(portfolio_id, new_name):
    with SessionLocal() as session:
        portfolio = session.query(Portfolio).filter(
            Portfolio.id == portfolio_id
        ).first()

        if portfolio:
            portfolio.name = new_name
            session.commit()


def update_portfolio_cash(portfolio_id, amount):
    with SessionLocal() as session:
        portfolio = session.query(Portfolio).filter(
            Portfolio.id == portfolio_id
        ).first()

        if portfolio:
            portfolio.cash += amount
            session.commit()
            return portfolio
    return None
