// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { ModuleCardComponent } from '../../components/module-card-component/module-card-component';
import { EvaluationService } from '../../services/evaluation-service';
import { CommonModule } from '@angular/common';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { EvaluationListComponent } from '../../components/evaluation-list-component/evaluation-list-component';
import { NewEvaluationModalComponent } from '../../components/new-evaluation-modal-component/new-evaluation-modal-component';
import { PeerReviewModalComponent } from '../../components/peer-review-modal-component/peer-review-modal-component';
import { PageTitleComponent } from '../../components/page-title-component/page-title-component';

@Component({
  selector: 'app-modules',
  imports: [
    ModuleCardComponent,
    CommonModule,
    MatSelectModule,
    MatFormFieldModule,
    ReactiveFormsModule,
    FormsModule,
    MatInputModule,
    MatButtonModule,
    EvaluationListComponent,
    NewEvaluationModalComponent,
    PeerReviewModalComponent,
    PageTitleComponent
  ],
  templateUrl: './modules.html',
  styleUrl: './modules.css',
})
export class Modules implements OnInit {
  modules: any[] = [];
  email: string = '';
  openCardIndex: number | null = null;
  evaluationListByIndex: any = {};
  showNewEvalModal: boolean = false;
  showPeerReviewModal: boolean = false;
  selectedModule: any = null;

  constructor(
    private evaluationService: EvaluationService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.email = localStorage.getItem('accountEmail') || '';

    this.evaluationService.getModules(this.email).subscribe({
      next: (response) => {
        this.modules = response;
      }
    });
  }

  onClickCard(index: number) {
    if (this.openCardIndex === index) {
      this.selectedModule = null;
      this.openCardIndex = null;
      return;
    }

    this.selectedModule = this.modules[index];
    this.openCardIndex = index;
  }

  openNewEvalModal() {
    this.showNewEvalModal = true;
  }

  closeNewEvalModal() {
    this.showNewEvalModal = false;
  }

  openPeerReviewModal() {
    this.showPeerReviewModal = true;
  }

  closePeerReviewModal() {
    this.showPeerReviewModal = false;
  }
}
