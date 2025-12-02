import { Component, EventEmitter, Input, Output, OnInit, DoCheck } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EvaluationService } from '../../services/evaluation-service';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { ScanRequest } from '../../interfaces/scan-request';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { ScanItem } from '../../interfaces/scan-item';

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
    MatTabsModule,
    EvaluationCircleComponent,
    MatProgressBarModule
  ],
  templateUrl: './search-component.html',
  styleUrl: './search-component.css',
})
export class SearchComponent implements OnInit, DoCheck {
  @Input() disableEvaluateButton!: boolean;
  @Input() linkModule!: string;
  @Input() scanInformation!: any;
  @Output() startPolling = new EventEmitter<{ scan: ScanItem, refresh: boolean }>();
  @Output() downloadEvent = new EventEmitter<void>();

  private lastUpdatedData: any;

  tab: string = '';
  data: any = null;
  isLoading = false;
  codeControl = new FormControl('', Validators.required);
  evaluationList: any[] = [];
  selectedTabIndex = 0;
  download: boolean = false;
  isEvaluating: boolean = false;
  isFinished: boolean = false;

  constructor (
    private evaluationService: EvaluationService
  ) {}

  ngOnInit(): void {
    this.tab = this.scanInformation.name;
    if (this.scanInformation.id !== undefined && this.scanInformation.id !== null) {
      this.loadData();
    }

    this.isEvaluating = (this.scanInformation.status === 'Creating' || this.scanInformation.status === 'In Progress') && this.scanInformation.evaluable === false;
    this.isFinished = this.scanInformation.status === 'Completed';
    this.download = this.scanInformation.status === 'Completed' && this.scanInformation.name === 'All Scans';
  }

  ngDoCheck(): void {
    if (this.scanInformation?.updated_data && this.lastUpdatedData !== this.scanInformation.updated_data) {
      this.data = this.scanInformation.updated_data;
      this.lastUpdatedData = this.scanInformation.updated_data;
    }
  }

  evaluate(): void {
    const scanRequest: ScanRequest = { 
      course_link: this.linkModule,
      email: localStorage.getItem('accountEmail')!,
      scan_name: this.tab
    }

    this.evaluationService.evaluate(scanRequest).subscribe({
      next: (response) => {
        this.startPolling.emit({ scan: { "scan_id": response.body.scan_id, "scan_name": scanRequest.scan_name }, refresh: true });
        this.scanInformation.evaluable = false;
        this.isEvaluating = true;
      },
      error: (error) => {
        console.error('Evaluation error:', error);
      }
    });
  }

  loadData(): void {
    this.isLoading = true;

    const request$ = this.tab === 'All Scans'
      ? this.evaluationService.getEvaluationDetailModule(this.scanInformation.id, true)
      : this.evaluationService.getEvaluationDetailScan(this.scanInformation.id, true);

    request$.subscribe({
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

  downloadPDF(): void {
    this.downloadEvent.emit();
  }
}