import { Component } from '@angular/core';
import { MatProgressBarModule } from '@angular/material/progress-bar';

@Component({
  selector: 'app-evaluation-progress-bar-component',
  imports: [
    MatProgressBarModule,
  ],
  templateUrl: './evaluation-progress-bar-component.html',
  styleUrl: './evaluation-progress-bar-component.css',
})
export class EvaluationProgressBarComponent {

}
