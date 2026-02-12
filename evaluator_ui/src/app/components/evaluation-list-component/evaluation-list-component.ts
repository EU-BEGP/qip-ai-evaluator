// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';

@Component({
  selector: 'app-evaluation-list-component',
  imports: [
    CommonModule,
    MatIconModule
  ],
  templateUrl: './evaluation-list-component.html',
  styleUrl: './evaluation-list-component.css',
})
export class EvaluationListComponent {
  @Input() moduleData!: any;
  @Output() peerReviewClick = new EventEmitter<void>();

  constructor(
    private router: Router
  ) {}

  onClickSelfAssessment(): void {
    this.router.navigate(['/self-assessment', this.moduleData.last_evaluation_id]);
  }

  onClickAIEvaluation(): void {
    this.router.navigate(['/evaluation', this.moduleData.last_evaluation_id]);
  }

  onClickPeerReview(): void {
    this.peerReviewClick.emit();
  }
}
