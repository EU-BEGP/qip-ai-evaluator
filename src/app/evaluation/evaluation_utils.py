# Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
# MIT License - See LICENSE file in the root directory
# Sebastian Itamari, Santiago Almancy, Alex Villazon

from typing import List, Tuple, Dict
import json

class EvaluationUtils:
    @staticmethod
    def get_eu_classification(score: float) -> str:
        """Classify based on the score."""
        if score == 5.0:
            return "No Issues"
        elif 4.5 <= score < 5.0:
            return "Minor Shortcoming"
        elif 4.0 <= score < 4.5:
            return "Shortcoming"
        elif 3.0 <= score < 4.0:
            return "Minor Weakness"
        elif score < 3.0:
            return "Weakness"
        else:
            return "Out of valid range"

    @staticmethod
    def fill_aditional_data(evaluation_data: List[Dict]) -> None:
        """Fill the EU classifications, total scores and maximum scores for each evaluation unit."""
        total_max_score = 0.0
        total_score = 0.0
        for scan in evaluation_data["content"]:
            criterion_quantity_scan = 0
            max_score_scan = 0.0
            score_scan = 0.0
            for criterion in scan.get("criteria", []):
                criterion_quantity_scan += 1
                score = criterion.get("score")
                if score is not None:
                    criterion["eu_classification"] = EvaluationUtils.get_eu_classification(score)
                    criterion["max_score"] = 5.0
                    max_score_scan += 5.0
                    score_scan += score
            
            scan["max_score_scan"] = max_score_scan
            scan["score_scan"] = score_scan
            scan["criterion_quantity_scan"] = criterion_quantity_scan
            scan["average_score_scan"] = round(score_scan / criterion_quantity_scan, 1) if criterion_quantity_scan > 0 else 0.0
            total_max_score += max_score_scan
            total_score += score_scan

        evaluation_data["total_max_score"] = total_max_score
        evaluation_data["total_score"] = total_score
        
        #with open("output.json", "w", encoding="utf-8") as file:
        #    json.dump(evaluation_data, file, indent=2, ensure_ascii=False)