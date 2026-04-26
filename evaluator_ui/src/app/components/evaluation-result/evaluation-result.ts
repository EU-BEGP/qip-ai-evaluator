// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { EvaluationResult } from '../../interfaces/evaluation-result';
import { EEDAClassification } from '../../interfaces/eeda-classification';

@Component({
  selector: 'app-evaluation-result-component',
  imports: [
    CommonModule
  ],
  templateUrl: './evaluation-result.html',
  styleUrl: './evaluation-result.css',
})
export class EvaluationResultComponent {
  @Input() data!: EvaluationResult;

  getScoreClassification(score: number): EEDAClassification {
    if (score == 5.0) {
      return { label: 'No Issues', class: 'classification-no-issues' };
    } else if (score >= 4.5) {
      return { label: 'Minor Shortcoming', class: 'classification-minor-shortcoming' };
    } else if (score >= 4.0) {
      return { label: 'Shortcoming', class: 'classification-shortcoming' };
    } else if (score >= 3.0) {
      return { label: 'Minor Weakness', class: 'classification-minor-weakness' };
    } else {
      return { label: 'Weakness', class: 'classification-weakness' };
    }
  }

  getEEDAClassifications() {
    return [
      { label: 'No Issues', range: '5.0', description: 'Meets all requirements perfectly', class: 'classification-no-issues' },
      { label: 'Minor Shortcoming', range: '4.5 - 4.9', description: 'Small improvements needed', class: 'classification-minor-shortcoming' },
      { label: 'Shortcoming', range: '4.0 - 4.4', description: 'Notable improvements needed', class: 'classification-shortcoming' },
      { label: 'Minor Weakness', range: '3.0 - 3.9', description: 'Significant improvements needed', class: 'classification-minor-weakness' },
      { label: 'Weakness', range: '< 3.0', description: 'Major improvements required', class: 'classification-weakness' }
    ];
  }
}
