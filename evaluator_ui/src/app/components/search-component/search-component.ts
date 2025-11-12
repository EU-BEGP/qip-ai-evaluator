import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EvaluationService } from '../../services/evaluation-service';
import { MatSelectModule, MatSelectChange } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { ScanRequest } from '../../interfaces/scan-request';

@Component({
  selector: 'app-search-component',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTabsModule
  ],
  templateUrl: './search-component.html',
  styleUrl: './search-component.css',
})
export class SearchComponent {
  @Input() tab!: string;
  @Input() disableEvaluateButton!: boolean;
  @Output() startPooling = new EventEmitter<void>();

  data: any = null;
  isLoading = false;
  codeControl = new FormControl('', Validators.required);
  evaluationList: any[] = [];
  isLoadingHistory = false;
  selectedTabIndex = 0;

  constructor (
    private evaluationService: EvaluationService
  ) {}

  evaluate(): void {
    if (this.codeControl.invalid) {
      this.codeControl.markAsTouched();
      return;
    }

    const courseKey = this.codeControl.value!;
    const scanRequest: ScanRequest = { 
      course_key: courseKey,
      email: localStorage.getItem('accountEmail')!,
      scan_name: this.tab == 'All Scans' ? '' : this.tab
    }

    this.evaluationService.evaluate(scanRequest).subscribe({
      next: (response) => {
        this.startPooling.emit();
      },
      error: (error) => {
        console.error('Evaluation error:', error);
      }
    });
  }

  loadHistory(): void {
    if (this.codeControl.invalid) {
      this.codeControl.markAsTouched();
      return;
    }
    
    this.isLoadingHistory = true;
    this.evaluationList = [];
    this.data = null;
    const courseKey = this.codeControl.value!;
    const scanRequest: ScanRequest = { 
      course_key: courseKey,
      email: localStorage.getItem('accountEmail')!,
      scan_name: this.tab == 'All Scans' ? '' : this.tab
    }

    this.evaluationService.getEvaluationList(scanRequest).subscribe({
      next: (list) => {
        this.evaluationList = list.body;
        this.isLoadingHistory = false;
      },
      error: (err) => {
        console.error('Error loading history:', err);
        this.evaluationList = [];
        this.isLoadingHistory = false;
      }
    });
  }

  onHistorySelect(event: MatSelectChange): void {
    const evaluationId = event.value;
    if (!evaluationId) return;

    this.data = null;
    this.isLoading = true;

    if (this.tab === 'All Scans') {
      this.evaluationService.getEvaluationDetailModule(evaluationId).subscribe({
        next: (response) => {
          this.data = response;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading evaluation detail:', error);
          this.isLoading = false;
        }
      });
    }
    else {
      this.evaluationService.getEvaluationDetailScan(evaluationId).subscribe({
        next: (response) => {
          this.data = response;
          this.isLoading = false;
        },
        error: (error) => {
          console.error('Error loading evaluation detail:', error);
          this.isLoading = false;
        }
      });
    }
  }
}
