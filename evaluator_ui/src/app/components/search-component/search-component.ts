// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, EventEmitter, Input, Output, OnInit, DoCheck, OnChanges, SimpleChanges } from '@angular/core';
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
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';
import { ScanItem } from '../../interfaces/scan-item';
import { AlertComponent } from '../alert-component/alert-component';
import { EvaluationResultComponent } from '../evaluation-result/evaluation-result';
import { EvaluationProgressBarComponent } from '../evaluation-progress-bar-component/evaluation-progress-bar-component';
import { EvaluationProgressDotsComponent } from '../evaluation-progress-dots-component/evaluation-progress-dots-component';
import { Scan } from '../../interfaces/scan';
import { PeerReviewService } from '../../services/peer-review-service';

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
export class SearchComponent implements OnInit, DoCheck, OnChanges {
  @Input() reviewId: string = '';
  @Input() linkModule!: string;
  @Input() scanInformation!: Scan;
  @Input() isAIEvaluation: boolean = true;
  @Output() startPolling = new EventEmitter<{ scan: ScanItem, refresh: boolean }>();
  @Output() downloadEvent = new EventEmitter<void>();

  private lastUpdatedData: any;

  tab: string = '';
  data: any = null;
  isLoading = false;
  codeControl = new FormControl('', Validators.required);
  evaluationList: any[] = [];
  selectedTabIndex = 0;
  isEvaluating: boolean = false;
  isFinished: boolean = false;
  message: string = 'This evaluation belongs to a previous module version. Please start a new evaluation to continue.';

  constructor (
    private evaluationService: EvaluationService,
    private peerReviewService: PeerReviewService
  ) {}

  ngOnInit(): void {
    this.tab = this.scanInformation.name;
    
    if (this.scanInformation.evaluable === false || this.isAIEvaluation === false) {
      this.loadData();
    }

    this.isEvaluating = (this.scanInformation.status === 'Creating' || this.scanInformation.status === 'In Progress') && this.scanInformation.evaluable === false;
    this.isFinished = this.scanInformation.status === 'Completed';
  }

  ngDoCheck(): void {
    if (this.scanInformation?.updated_data && this.lastUpdatedData !== this.scanInformation.updated_data) {
      this.data = this.scanInformation.updated_data;
      this.lastUpdatedData = this.scanInformation.updated_data;
    }
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['scanInformation'] && !changes['scanInformation'].firstChange) {
      const prev = changes['scanInformation'].previousValue?.status;
      const curr = changes['scanInformation'].currentValue?.status;

      if (prev !== curr) {
        this.isEvaluating = (this.scanInformation.status === 'Creating' || this.scanInformation.status === 'In Progress') && this.scanInformation.evaluable === false;
        this.isFinished = this.scanInformation.status === 'Completed';
      }
    }
  }

  loadData(): void {
    this.isLoading = true;
    let request$;

    if (this.isAIEvaluation === true) {
      request$ = this.tab === 'All Scans'
        ? this.evaluationService.getEvaluationDetailModule(this.scanInformation.id!, true)
        : this.evaluationService.getEvaluationDetailScan(this.scanInformation.id!, true);
    } else {
      request$ = this.peerReviewService.getReviewDetailScan(this.reviewId , this.scanInformation.id!.toString());
    }
    
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
}