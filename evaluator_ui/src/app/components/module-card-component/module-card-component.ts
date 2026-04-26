// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { EvaluationCircleComponent } from '../evaluation-circle-component/evaluation-circle-component';
import { MatButtonModule } from '@angular/material/button';
import { UtilsService } from '../../services/utils-service';
import { ModuleDashboardItem } from '../../interfaces/module-dashboard-item';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-module-card-component',
  imports: [
    MatCardModule,
    CommonModule,
    EvaluationCircleComponent,
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './module-card-component.html',
  styleUrl: './module-card-component.css',
})
export class ModuleCardComponent implements OnInit {
  @Output() onClick = new EventEmitter<string>();
  @Output() onClickEvaluateUpdated = new EventEmitter<string>();
  @Input() data!: ModuleDashboardItem;

  showEvaluateUpdatedButton: boolean = false;

  constructor(
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    const lastEvaluationDate = this.utilsService.parseDate(this.data.last_evaluation);
    const lastModifyDate = this.utilsService.parseDate(this.data.last_modify);

    if (lastModifyDate > lastEvaluationDate) {
      this.showEvaluateUpdatedButton = true;
    }
  }

  onClickCard(link: string) {
    this.onClick.emit(link);
  }

  onClickEvaluateUpdatedVersion(link: string, event: MouseEvent) { 
    event.stopPropagation();
    this.onClickEvaluateUpdated.emit(link);
  }
}
