// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, Input, OnInit } from '@angular/core';
import { Scan } from '../../interfaces/scan';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';
import { RouterLink } from "@angular/router";
import { EvaluationService } from '../../services/evaluation-service';
import { ModuleInfo } from '../../interfaces/module-info';

@Component({
  selector: 'app-module-detail-component',
  imports: [
    EvaluationCircleComponent
],
  templateUrl: './module-detail-component.html',
  styleUrl: './module-detail-component.css',
})
export class ModuleDetailComponent implements OnInit {
  data: ModuleInfo | null = null;

  @Input() scanInformation!: Scan;
  @Input() evaluationId!: string;

  constructor(
    private evaluationService: EvaluationService,
  ) {}

  ngOnInit(): void {
    this.evaluationService.getBasicInformation(this.evaluationId).subscribe({
      next: (response) => {
        this.data = response;
      },
      error: (error) => {
        console.error('Error fetching basic information:', error);
      }
    })
  }
}
