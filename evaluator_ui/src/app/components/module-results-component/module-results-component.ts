// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, Input } from '@angular/core';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';
import { Scan } from '../../interfaces/scan';

@Component({
  selector: 'app-module-results-component',
  imports: [
    EvaluationCircleComponent
  ],
  templateUrl: './module-results-component.html',
  styleUrl: './module-results-component.css',
})
export class ModuleResultsComponent {
  @Input() scanList!: Scan[];

  get completedScans(): Scan[] {
    return this.scanList?.filter(
      scan => scan.name !== 'All Scans' && scan.status === 'Completed'
    ) ?? [];
  }

  get shouldRender(): boolean {
    return this.completedScans.length > 1;
  }
}
