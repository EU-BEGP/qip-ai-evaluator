from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import json

Base = declarative_base()

class Module(Base):
    __tablename__ = 'modules'
    
    course_key = Column(String(50), primary_key=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    evaluations = relationship("Evaluation", back_populates="module", cascade="all, delete-orphan")

class Evaluation(Base):
    __tablename__ = 'evaluations'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    course_key = Column(String(50), ForeignKey('modules.course_key'), nullable=False, index=True)
    evaluation_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    results_json = Column(Text, nullable=False)
    
    module = relationship("Module", back_populates="evaluations")
    
    @property
    def formatted_date(self) -> str:
        return self.evaluation_date.strftime("%Y-%m-%d %H:%M:%S")
    
    def get_results_dict(self) -> dict:
        try:
            return json.loads(self.results_json)
        except json.JSONDecodeError:
            return {}
    
    def set_results_dict(self, results: dict):
        self.results_json = json.dumps(results, ensure_ascii=False, indent=2)

def create_database_engine(db_path: str = "evaluation_history.db"):
    engine = create_engine(f"sqlite:///{db_path}", echo=False, pool_pre_ping=True)
    return engine

def create_session_factory(engine):
    return sessionmaker(bind=engine)
