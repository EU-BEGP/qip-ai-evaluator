// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'app-answer-distribution-component',
  imports: [],
  templateUrl: './answer-distribution-component.html',
  styleUrl: './answer-distribution-component.css',
})
export class AnswerDistributionComponent implements OnInit {
  @Input() answerDistribution!: any;

  yesPercentage: number = 0;
  noPercentage: number = 0;
  notApplicablePercentage: number = 0;
  unansweredPercentage: number = 0;

  ngOnInit(): void {
    this.yesPercentage = this.getPercentage(this.answerDistribution.yes, this.answerDistribution.total);
    this.noPercentage = this.getPercentage(this.answerDistribution.no, this.answerDistribution.total);
    this.notApplicablePercentage = this.getPercentage(this.answerDistribution.not_applicable, this.answerDistribution.total);
    this.unansweredPercentage = this.getPercentage(this.answerDistribution.unanswered, this.answerDistribution.total);
  }

  getPercentage(value: number, total: number): number {
    if (total === 0) {
      return 0;
    }
    const percentage = (value / total * 100);
    return Number(percentage.toFixed(0));
  }
}
