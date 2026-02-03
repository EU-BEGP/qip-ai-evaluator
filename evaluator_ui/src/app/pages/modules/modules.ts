// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { ModuleCardComponent } from '../../components/module-card-component/module-card-component';
import { EvaluationService } from '../../services/evaluation-service';
import { CommonModule } from '@angular/common';
import { ScanRequest } from '../../interfaces/scan-request';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormBuilder, FormGroup, Validators, FormsModule, ReactiveFormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { StorageService } from '../../services/storage-service';
import { MatIconModule } from '@angular/material/icon';
import { EvaluationListComponent } from '../../components/evaluation-list-component/evaluation-list-component';
import { ToastrService } from 'ngx-toastr';
import { MetadataStatusComponent } from '../../components/metadata-status-component/metadata-status-component';
import { MetadataItem } from '../../interfaces/metadata-item';
import { NewEvaluationModalComponent } from '../../components/new-evaluation-modal-component/new-evaluation-modal-component';

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
    NewEvaluationModalComponent
  ],
  templateUrl: './modules.html',
  styleUrl: './modules.css',
})
export class Modules implements OnInit {
  modules: any[] = [];
  email: string = '';
  openCardIndex: number | null = null;
  evaluationListByIndex: any = {};
  disableCourseLink = false;
  showNewEvalModal = false;
  scans: string[] = ['All Scans', 'Academic Metadata Scan', 'Learning Content Scan', 'Assessment Scan', 'Multimedia Scan', 'Certificate Scan', 'Summary Scan'];

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

  onClickCard(link: string, index: number) {
    const scanRequest: ScanRequest = { 
      course_link: link,
      email: this.email,
      scan_name: 'All Scans'
    }
    
    if (this.openCardIndex === index) {
      this.openCardIndex = null;
      return;
    }

    this.openCardIndex = index;
    this.evaluationService.getEvaluationList(scanRequest).subscribe({
      next: (response) => {
        let list: any[] = [];
        list = response.body;

        if (index >= 0) this.evaluationListByIndex[index] = list;
      }
    });
  }

  ////
  onClickEvaluateUpdated(link: string) {
    this.openNewEvalModal(link);
  }

  ////
  openNewEvalModal(courseLink: string = '') {
    //this.disableCourseLink = !!courseLink;
    this.showNewEvalModal = true;

    /*const courseControl = this.newEvalForm.get('courseLink');

    courseControl!.setValue(courseLink || '');
    if (courseLink) {
      courseControl!.disable();
    }  
    else {
      courseControl!.enable();
    }*/
  }

  closeNewEvalModal() {
    this.showNewEvalModal = false;
  }

  onSelectEvaluation(item: any) {
    if (!item) return;
    this.openCardIndex = null;
    this.router.navigate(['/evaluation', item.id], {
      queryParams: { scan: 'All Scans' }
    });
  }
}
