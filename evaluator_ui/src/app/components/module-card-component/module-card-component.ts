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
  @Output() onClick = new EventEmitter<string>();
  @Output() onClickEvaluateUpdated = new EventEmitter<string>();
  @Input() data!: any;

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
