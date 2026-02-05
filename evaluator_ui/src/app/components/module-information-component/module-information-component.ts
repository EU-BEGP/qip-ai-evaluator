// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
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
export class ModuleInformationComponent implements OnInit{
  @Input() evaluationId!: string;
  @Input() scanInformation!: Scan;
  @Input() scanList!: Scan[];
  @Output() downloadEvent = new EventEmitter<void>();
  download: boolean = false;

  ngOnInit(): void {
    this.download = this.scanInformation.status === 'Completed';
  }

  downloadPDF(): void {
    this.downloadEvent.emit();
  }
}
