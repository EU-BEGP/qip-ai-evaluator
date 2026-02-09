// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';
import { MatButtonModule } from '@angular/material/button';
import { UtilsService } from '../../services/utils-service';

@Component({
  selector: 'app-module-card-component',
  imports: [
    MatCardModule,
    CommonModule,
    EvaluationCircleComponent,
    MatButtonModule
  ],
  templateUrl: './module-card-component.html',
  styleUrl: './module-card-component.css',
})
export class ModuleCardComponent implements OnInit {
  @Output() onClick = new EventEmitter<void>();
  @Input() data!: any;

  private readonly statusConfig: Record<string, { badge: string; text: string }> = {
    "Outdated": {
      badge: 'alert-danger',
      text: 'Outdated'
    },
    "Updated": {
      badge: 'alert-success',
      text: 'Updated'
    },
    "Self assessment": {
      badge: 'alert-primary',
      text: 'Self assessment'
    },
  };

  constructor(
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    const lastEvaluationDate = this.utilsService.parseDate(this.data.last_evaluation);
    const lastModifyDate = this.utilsService.parseDate(this.data.last_modify);
  }

  getClass(): string {
    return this.statusConfig[this.data.status]?.badge;
  }

  getText(): string {
    return this.statusConfig[this.data.status]?.text;
  }

  onClickCard() {
    this.onClick.emit();
  }
}
