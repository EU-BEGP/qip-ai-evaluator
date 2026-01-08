import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-evaluation-result-component',
  imports: [
    CommonModule
  ],
  templateUrl: './evaluation-result.html',
  styleUrl: './evaluation-result.css',
})
export class EvaluationResultComponent {
  @Input() data!: any;
}
