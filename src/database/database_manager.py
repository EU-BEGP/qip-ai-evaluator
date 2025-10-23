from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import yaml
from models import Base, Module, Evaluation, create_database_engine, create_session_factory

class DatabaseManager:
    
    def __init__(self, db_path: str = None):
        if db_path is None:
            db_path = self.get_db_path()
        
        db_path_obj = Path(db_path)
        db_path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        self.engine = create_database_engine(str(db_path))
        self.SessionLocal = create_session_factory(self.engine)
        Base.metadata.create_all(bind=self.engine)
    
    def get_db_path(self) -> str:
        config_path = Path(__file__).parents[1] / "config" / "config.yaml"
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f) or {}
            
            db_path = config.get("database", {}).get("path", "db/evaluation_history.db")
            
            if not Path(db_path).is_absolute():
                db_path = Path(__file__).parents[1] / db_path
            
            return str(db_path)
        except Exception:
            return str(Path(__file__).parents[1] / "db" / "evaluation_history.db")
    
    def save_module(self, course_key: str) -> Module:
        with self.SessionLocal() as session:
            module = session.query(Module).filter_by(course_key=course_key).first()
            
            if not module:
                module = Module(course_key=course_key)
                session.add(module)
            else:
                module.updated_at = datetime.utcnow()
            
            session.commit()
            return module
    
    def save_evaluation(self, course_key: str, results: Dict[str, Any]) -> Dict[str, Any]:
        with self.SessionLocal() as session:
            # Ensure module exists
            self.save_module(course_key)
            
            # Delete old evaluations (keep only latest 2, so with new one = 3 total)
            old_evaluations = (session.query(Evaluation)
                              .filter_by(course_key=course_key)
                              .order_by(Evaluation.evaluation_date.desc())
                              .offset(2)
                              .all())
            
            for old_eval in old_evaluations:
                session.delete(old_eval)
            
            # Create new evaluation
            evaluation = Evaluation(course_key=course_key)
            evaluation.set_results_dict(results)
            session.add(evaluation)
            session.commit()
            
            # Return simple dict instead of SQLAlchemy object
            return {
                "id": evaluation.id,
                "course_key": evaluation.course_key,
                "date": evaluation.formatted_date
            }
    
    def get_previous_evaluations(self, course_key: str, limit: int = 3) -> List[Evaluation]:
        with self.SessionLocal() as session:
            return (session.query(Evaluation)
                   .filter_by(course_key=course_key)
                   .order_by(Evaluation.evaluation_date.desc())
                   .limit(min(limit, 3))
                   .all())
    
    def get_criterion_history(self, course_key: str, scan_name: str, criterion_name: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Get historical data for a specific criterion from the last N evaluations.
        
        Args:
            course_key: The course identifier
            scan_name: Name of the scan (e.g., "Academic Metadata Scan")
            criterion_name: Name of the criterion (e.g., "EQF level")
            limit: Number of recent evaluations to check (max 3)
        
        Returns:
            List of criterion data from recent evaluations, each containing:
            - description, score, shortcomings, recommendations, evaluation_date
        """
        limit = min(limit, 3)
        evaluations = self.get_previous_evaluations(course_key, limit)
        
        criterion_history = []
        
        for evaluation in evaluations:
            results = evaluation.get_results_dict()
            content = results.get("content", [])
            
            # Find the specific scan
            for scan in content:
                if scan.get("scan") == scan_name:
                    # Find the specific criterion
                    for criterion in scan.get("criteria", []):
                        if criterion.get("name") == criterion_name:
                            criterion_history.append({
                                "evaluation_date": evaluation.formatted_date,
                                "description": criterion.get("description", ""),
                                "score": criterion.get("score", 0),
                                "shortcomings": criterion.get("shortcomings", []),
                                "recommendations": criterion.get("recommendations", [])
                            })
                            break
                    break
        
        return criterion_history
