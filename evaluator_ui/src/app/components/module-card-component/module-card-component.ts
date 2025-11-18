import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';

@Component({
  selector: 'app-module-card-component',
  imports: [
    MatCardModule,
    CommonModule,
    EvaluationCircleComponent
  ],
  templateUrl: './module-card-component.html',
  styleUrl: './module-card-component.css',
})
export class ModuleCardComponent {
  @Output() onClick = new EventEmitter<string>();
  @Input() data!: any;

  onClickCard(link: string) {
    this.onClick.emit(link);
  }
}
