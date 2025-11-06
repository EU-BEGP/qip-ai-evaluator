import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EvaluationService } from '../../services/evaluation-service';

@Component({
  selector: 'app-evaluation',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule
  ],
  templateUrl: './evaluation.html',
  styleUrl: './evaluation.css',
  standalone: true
})
export class EvaluationComponent {
  data: any = null;
  isLoading = false;
  codeControl = new FormControl('', Validators.required);

  constructor (
    private evaluationService: EvaluationService,
  ) {}

  evaluate(): void {
    if (this.codeControl.invalid) {
      this.codeControl.markAsTouched();
      return;
    }

    this.data = null;
    this.isLoading = true;
    const courseKey = this.codeControl.value!;

    this.evaluationService.evaluate(courseKey).subscribe({
      next: (response) => {
        this.data = response.body;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Evaluation error:', error);
        this.isLoading = false;
      }
    });
  }
}
