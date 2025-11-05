import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';

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
  ],
  templateUrl: './evaluation.html',
  styleUrl: './evaluation.css',
  standalone: true
})
export class EvaluationComponent {
  codeControl = new FormControl('', Validators.required);

  evaluate(): void {
    if (this.codeControl.invalid) {
      console.warn('El campo no puede estar vacío.');
      this.codeControl.markAsTouched();
      return;
    }

    console.log('Learnify Code:', this.codeControl.value);
  }
}
