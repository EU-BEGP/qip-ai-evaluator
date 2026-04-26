// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { EvaluationListItem } from '../../interfaces/evaluation-list-item';

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
  @Input() evaluationList: EvaluationListItem[] = [];
  @Output() selectEvaluation = new EventEmitter<EvaluationListItem>();

  clickEvaluation(item: EvaluationListItem) {
    this.selectEvaluation.emit(item);
  }
}
