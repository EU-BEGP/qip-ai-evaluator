// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, Input, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { MatIconModule } from '@angular/material/icon';
import { AnswerDistributionComponent } from '../answer-distribution-component/answer-distribution-component';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';

@Component({
  selector: 'app-result-card-component',
  imports: [
    CommonModule,
    MatCardModule,
    MatIconModule,
    AnswerDistributionComponent,
    EvaluationCircleComponent
  ],
  templateUrl: './result-card-component.html',
  styleUrl: './result-card-component.css',
})
export class ResultCardComponent implements OnInit {
  @Input() isMain: boolean = false;
  @Input() data!: any;

  totalPercentage: number = 0;
  complianceText: string = '';

  ngOnInit(): void {
    this.complianceText = 'This overall compliance is calculated as the percentage of fulfilled criterions for quality. The not-applicable criterions are excluded from the calculated compliance score.';
    this.totalPercentage = this.getPercentage(this.data.answer_distribution.yes + this.data.answer_distribution.not_applicable, this.data.answer_distribution.total);
  }

  getPercentage(value: number, total: number): number {
    if (total === 0) {
      return 0;
    }
    const percentage = (value / total * 100);
    return Number(percentage.toFixed(0));
  }

  getText(): string {
    return this.data.answer_distribution.unanswered > 0 ? 'Incompleted' : 'Completed';
  }

  getClass(): string {
    return this.data.answer_distribution.unanswered > 0 ? 'alert-danger' : 'alert-success';
  }

  getShortName(value: string): string {
    if (!value) return "";

    const parts = value.trim().split(" ");

    if (parts.length <= 1) return value;

    parts.pop();
    return parts.join(" ");
  }
}
