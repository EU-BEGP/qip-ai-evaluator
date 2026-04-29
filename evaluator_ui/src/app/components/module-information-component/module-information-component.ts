// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnChanges, OnInit, Output, SimpleChanges } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { Scan } from '../../interfaces/scan';
import { ModuleResultsComponent } from '../module-results-component/module-results-component';
import { ModuleDetailComponent } from '../module-detail-component/module-detail-component';

@Component({
  selector: 'app-module-information-component',
  imports: [
    MatButtonModule,
    CommonModule,
    ModuleResultsComponent,
    ModuleDetailComponent
],
  templateUrl: './module-information-component.html',
  styleUrl: './module-information-component.css',
})
export class ModuleInformationComponent implements OnInit, OnChanges {
  @Input() evaluationId!: string;
  @Input() scanInformation!: Scan;
  @Input() scanList!: Scan[];
  @Input() isAIEvaluation: boolean = true;
  @Output() downloadEvent = new EventEmitter<void>();
  download: boolean = false;

  ngOnInit(): void {
    this.download = this.scanInformation.status === 'Completed' && this.isAIEvaluation;
  }

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['scanInformation'] && !changes['scanInformation'].firstChange) {
      const prev = changes['scanInformation'].previousValue?.status;
      const curr = changes['scanInformation'].currentValue?.status;

      if (prev !== curr) {
        this.download = this.scanInformation.status === 'Completed' && this.isAIEvaluation;
      }
    }
  }  

  downloadPDF(): void {
    this.downloadEvent.emit();
  }
}
