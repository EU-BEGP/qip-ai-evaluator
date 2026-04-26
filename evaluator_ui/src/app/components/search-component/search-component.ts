// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

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
import { ScanItem } from '../../interfaces/scan-item';
import { AlertComponent } from '../alert-component/alert-component';
import { EvaluationResultComponent } from '../evaluation-result/evaluation-result';
import { EvaluationProgressBarComponent } from '../evaluation-progress-bar-component/evaluation-progress-bar-component';
import { EvaluationProgressDotsComponent } from '../evaluation-progress-dots-component/evaluation-progress-dots-component';
import { Scan } from '../../interfaces/scan';
import { EvaluationResult } from '../../interfaces/evaluation-result';
import { EvaluationListItem } from '../../interfaces/evaluation-list-item';

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
    AlertComponent,
    EvaluationResultComponent,
    EvaluationProgressBarComponent,
    EvaluationProgressDotsComponent
  ],
  templateUrl: './search-component.html',
  styleUrl: './search-component.css',
})
export class SearchComponent implements OnInit, DoCheck {
  @Input() disableEvaluateButton!: boolean;
  @Input() linkModule!: string;
  @Input() scanInformation!: Scan;
  @Output() startPolling = new EventEmitter<{ scan: ScanItem, refresh: boolean }>();
  @Output() downloadEvent = new EventEmitter<void>();

  private lastUpdatedData: EvaluationResult | undefined;

  tab: string = '';
  data: EvaluationResult | null = null;
  isLoading = false;
  codeControl = new FormControl('', Validators.required);
  evaluationList: EvaluationListItem[] = [];
  selectedTabIndex = 0;
  download: boolean = false;
  isEvaluating: boolean = false;
  isFinished: boolean = false;
  message: string = 'This evaluation belongs to a previous module version. Please start a new evaluation to continue.';

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
        const scanId = response.body?.scan_id;
        if (scanId !== undefined) {
          this.startPolling.emit({ scan: { "scan_id": String(scanId), "scan_name": scanRequest.scan_name }, refresh: true });
        }
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
      ? this.evaluationService.getEvaluationDetailModule(this.scanInformation.id!, true)
      : this.evaluationService.getEvaluationDetailScan(this.scanInformation.id!, true);

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