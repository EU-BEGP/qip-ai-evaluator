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
