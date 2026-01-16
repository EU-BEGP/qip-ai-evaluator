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
    EvaluationListComponent
  ],
  templateUrl: './modules.html',
  styleUrl: './modules.css',
})
export class Modules implements OnInit {
  newEvalForm!: FormGroup;
  modules: any[] = [];
  email: string = '';
  openCardIndex: number | null = null;
  evaluationListByIndex: any = {};
  disableCourseLink = false;
  showNewEvalModal = false;
  scans: string[] = ['All Scans', 'Academic Metadata Scan', 'Learning Content Scan', 'Assessment Scan', 'Multimedia Scan', 'Certificate Scan', 'Summary Scan'];

  constructor(
    private evaluationService: EvaluationService,
    private router: Router,
    private fb: FormBuilder
  ) {}

  ngOnInit(): void {
    this.email = localStorage.getItem('accountEmail') || '';

    this.newEvalForm = this.fb.group({
      courseLink: [{ value: '', disabled: false }, Validators.required],
      scanName: ['', Validators.required]
    });

    this.evaluationService.getModules(this.email).subscribe({
      next: (response) => {
        this.modules = response;
      }
    });
  }

  get courseLinkControl() {
    return this.newEvalForm.controls['courseLink'];
  }

  get scanNameControl() {
    return this.newEvalForm.controls['scanName'];
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

  onClickEvaluateUpdated(link: string) {
    this.openNewEvalModal(link);
  }

  openNewEvalModal(courseLink: string = '', scan: string = '') {
    this.disableCourseLink = !!courseLink;
    this.showNewEvalModal = true;

    const courseControl = this.newEvalForm.get('courseLink');
    const scanControl = this.newEvalForm.get('scanName');

    courseControl!.setValue(courseLink || '');
    if (courseLink) {
      courseControl!.disable();
    }  
    else {
      courseControl!.enable();
    }
  
    scanControl!.setValue(scan || '');
  }

  closeNewEvalModal() {
    this.showNewEvalModal = false;
    const courseControl = this.newEvalForm.get('courseLink');
    courseControl!.enable();
    this.newEvalForm.reset();
  }

  evaluateNew() {
    if (this.newEvalForm.valid) {
      this.evaluate();
      this.closeNewEvalModal();
    }
  }

  onSelectEvaluation(item: any) {
    if (!item) return;
    this.openCardIndex = null;
    this.router.navigate(['/evaluation', item.id], {
      queryParams: { scan: 'All Scans' }
    });
  }

  evaluate(): void {
    const courseLink = this.newEvalForm.get('courseLink')?.value;
    const scanName = this.newEvalForm.get('scanName')?.value;

    const scanRequest: ScanRequest = { 
      course_link: courseLink,
      email: this.email,
      scan_name: scanName
    }

    this.evaluationService.evaluate(scanRequest).subscribe({
      next: (response) => {
        this.router.navigate(['/evaluation', response.body.evaluation_id], {
          queryParams: { scan: scanRequest.scan_name }
        });
      },
      error: (error) => {
        console.error('Evaluation error:', error);
      }
    });
  }
}
