from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from utils.config import get_database_url

Base = declarative_base()

class Club(Base):
    __tablename__ = 'club'

    # do not touch, primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String, nullable=False)
    guild_id = Column(String, nullable=False)
    spreadsheet_id = Column(String, nullable=True)

    # Relationships
    players = relationship("Player", back_populates="club")
    channel_configs = relationship("ChannelConfig", back_populates="club")

class Player(Base):
    __tablename__ = 'player'

    # do not touch, primary key
    id = Column(Integer, primary_key=True, autoincrement=True)

    name = Column(String, nullable=False)
    aliases = Column(Text)

    club_id = Column(Integer, ForeignKey('club.id'), nullable=False)
    discord_id = Column(String)

    # Relationships
    club = relationship("Club", back_populates="players")

class ChannelConfig(Base):
    __tablename__ = 'channel_config'

    # do not touch, primary key
    channel_id = Column(String, primary_key=True)
    purpose = Column(String, primary_key=True)

    club_id = Column(Integer, ForeignKey('club.id'))
    created_at = Column(DateTime, default=func.now(), nullable=False)
    created_by = Column(String, nullable=False)

    # Relationships
    club = relationship("Club", back_populates="channel_configs")

# Database setup
engine = create_engine(get_database_url(), pool_pre_ping=True, pool_recycle=300)
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database and create all tables."""
    try:
        Base.metadata.create_all(bind=engine)
        print("Database: Tables created successfully")
    except Exception as e:
        print(f"Database: Failed to create tables - {e}")
        raise