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
import { ModuleDashboardItem } from '../../interfaces/module-dashboard-item';
import { EvaluationListItem } from '../../interfaces/evaluation-list-item';
import { PageTitleComponent } from '../../components/page-title-component/page-title-component';
import { LoaderService } from '../../services/loader-service';
import { firstValueFrom } from 'rxjs/internal/firstValueFrom';
import { Observable } from 'rxjs';
import { Scan } from '../../interfaces/scan';
import { HttpResponse } from '@angular/common/http';
import { EvaluateResponse } from '../../interfaces/evaluate-response';

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
    PageTitleComponent
  ],
  templateUrl: './modules.html',
  styleUrl: './modules.css',
})
export class Modules implements OnInit {
  newEvalForm!: FormGroup;
  modules: ModuleDashboardItem[] = [];
  email: string = '';
  openCardIndex: number | null = null;
  evaluationListByIndex: Record<number, EvaluationListItem[]> = {};
  disableCourseLink = false;
  showNewEvalModal = false;
  scans: string[] = ['All Scans', 'Academic Metadata Scan', 'Learning Content Scan', 'Assessment Scan', 'Multimedia Scan', 'Certificate Scan', 'Summary Scan'];

  constructor(
    private evaluationService: EvaluationService,
    private router: Router,
    private fb: FormBuilder,
    private loaderService: LoaderService,
    private toastr: ToastrService
  ) {}

  ngOnInit(): void {
    this.email = localStorage.getItem('accountEmail') || '';

    this.newEvalForm = this.fb.group({
      courseLink: [{ value: '', disabled: false }, Validators.required],
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

  onClickCard(link: string, index: number) {
    const scanRequest: ScanRequest = { 
      course_link: link,
      scan_name: 'All Scans'
    }
    
    if (this.openCardIndex === index) {
      this.openCardIndex = null;
      return;
    }

    this.openCardIndex = index;
    this.evaluationService.getEvaluationList(scanRequest).subscribe({
      next: (response) => {
        const list: EvaluationListItem[] = response.body ?? [];

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

    courseControl!.setValue(courseLink || '');
  }

  closeNewEvalModal() {
    this.showNewEvalModal = false;
    this.newEvalForm.reset();
  }

  async evaluateNew() {
    if (this.newEvalForm.valid) {
      this.loaderService.show();
      const evaluationId = await this.initAssessment();
      this.closeNewEvalModal();
      if (evaluationId) {
        await this.router.navigate(['/evaluation', evaluationId], {
          queryParams: { scan: 'All Scans' }
        });
      }
      this.loaderService.hide();
    }
  }

  onSelectEvaluation(item: EvaluationListItem) {
    if (!item) return;
    this.openCardIndex = null;
    this.router.navigate(['/evaluation', item.id], {
      queryParams: { scan: 'All Scans' }
    });
  }

  evaluate(scanName: string, courseLink: string): Observable<HttpResponse<EvaluateResponse>> {
    const scanRequest: ScanRequest = { 
      course_link: courseLink,
      scan_name: scanName
    }

    return this.evaluationService.evaluate(scanRequest, false, false);
  }

  initAssessment(): Promise<number | undefined> {
    const courseLink = this.newEvalForm.get('courseLink')?.value;
    const scansToEvaluate = this.getScans();
    const evaluationRequests = scansToEvaluate.map(scan => 
      firstValueFrom(this.evaluate(scan, courseLink))
    );

    return Promise.allSettled(evaluationRequests).then((results) => {
      const anyFailed = results.some(r => r.status === 'rejected');
      if (anyFailed) {
        results.filter(r => r.status === 'rejected')
          .forEach(r => console.error('Batch evaluation error:', (r as PromiseRejectedResult).reason));
        this.toastr.error('Something went wrong initializing the evaluation.', 'Error');
      } else {
        this.toastr.success('The evaluation was initialized successfully.', 'Success');
      }
      const firstFulfilled = results.find(
        (r): r is PromiseFulfilledResult<HttpResponse<EvaluateResponse>> => r.status === 'fulfilled'
      );
      return firstFulfilled?.value?.body?.evaluation_id ?? undefined;
    });
  }

  private getScans(): string[] {
    return this.scans.slice(1);
  }
}
