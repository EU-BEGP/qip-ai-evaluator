from django.db import models
from django.utils import timezone
import json

class Module(models.Model):
    course_key = models.CharField(max_length=50, primary_key=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.course_key

class Evaluation(models.Model):
    module = models.ForeignKey(Module, related_name='evaluations', on_delete=models.CASCADE)
    evaluation_date = models.DateTimeField(default=timezone.now)
    results_json = models.TextField()

    @property
    def formatted_date(self):
        return self.evaluation_date.strftime("%Y-%m-%d %H:%M:%S")

    def get_results_dict(self):
        try:
            return json.loads(self.results_json)
        except json.JSONDecodeError:
            return {}

    def set_results_dict(self, results: dict):
        self.results_json = json.dumps(results, ensure_ascii=False, indent=2)

    @classmethod
    def get_criterion_history(cls, course_key, scan_name, criterion_name, limit=1):
        """
        Finds the most recent evaluation data for a specific criterion.
        """
        history = []
        
        # Get all evaluations for the module, most recent first
        evaluations = cls.objects.filter(
            module__course_key=course_key
        ).order_by('-evaluation_date')

        for ev in evaluations:
            if len(history) >= limit:
                break
            results = ev.get_results_dict()
            if not results or 'content' not in results:
                continue

            # Dig into the JSON structure
            for scan_data in results.get('content', []):
                if scan_data.get('scan') == scan_name:
                    
                    for crit_data in scan_data.get('criteria', []):
                        if crit_data.get('name') == criterion_name:
                            
                            # Found the matching criterion, extract its data
                            history.append({
                                "evaluation_date": ev.formatted_date, # Use the property
                                "description": crit_data.get("description", ""),
                                "score": crit_data.get("score", 0.0),
                                "shortcomings": crit_data.get("shortcomings", []),
                                "recommendations": crit_data.get("recommendations", [])
                            })
  
                            break
                    break
        
        return history
