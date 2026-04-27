from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Database setup
Base = declarative_base()
engine = create_engine('sqlite:///flightops.db', echo=False)
Session = sessionmaker(bind=engine)

class Flight(Base):
    __tablename__ = 'flights'
    
    id = Column(Integer, primary_key=True)
    flight_num = Column(String(10), unique=True, nullable=False)
    destination = Column(String(50), nullable=False)
    departure_time = Column(DateTime, nullable=False)
    status = Column(String(20), default='Scheduled')
    gate = Column(String(5))
    
    def to_dict(self):
        return {
            'id': self.id,
            'flight_num': self.flight_num,
            'destination': self.destination,
            'departure_time': self.departure_time,
            'status': self.status,
            'gate': self.gate
        }

# Create tables
Base.metadata.create_all(engine)

print("FlightOps DB ready!")
