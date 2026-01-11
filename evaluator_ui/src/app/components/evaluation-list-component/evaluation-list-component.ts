import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

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
  @Input() evaluationList: any[] = [];
  @Output() selectEvaluation = new EventEmitter<any>();

  clickEvaluation(item: any) {
    this.selectEvaluation.emit(item);
  }
}
