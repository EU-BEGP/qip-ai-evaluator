import { Component } from '@angular/core';
import { ModuleCardComponent } from '../../components/module-card-component/module-card-component';
import { HeaderComponent } from '../../components/header-component/header-component';
import { EvaluationService } from '../../services/evaluation-service';
import { CommonModule } from '@angular/common';
import { ScanRequest } from '../../interfaces/scan-request';
import { MatSelectModule } from '@angular/material/select';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { Subscription } from 'rxjs';
import { StorageService } from '../../services/storage-service';

@Component({
  selector: 'app-modules',
  imports: [
    ModuleCardComponent,
    HeaderComponent,
    CommonModule,
    MatSelectModule,
    MatFormFieldModule,
    FormsModule,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './modules.html',
  styleUrl: './modules.css',
})
export class Modules {
  private evaluationIdSub?: Subscription;
  
  modules: any[] = [];
  email: string = '';
  openCardIndex: number | null = null;
  evaluationListByIndex: { [key: number]: any[] } = {};
  disableEvaluateButton = false;
  
  // New Evaluation modal
  showNewEvalModal = false;
  newEvalCourseLink: string = '';
  newEvalScan: string = '';
  scans: string[] = ['All Scans', 'Academic Metadata Scan', 'Learning Content Scan', 'Assessment Scan', 'Multimedia Scan', 'Certificate Scan', 'Summary Scan'];

  constructor(
    private evaluationService: EvaluationService,
    private router: Router,
    private storageService: StorageService,
  ) {}

  ngOnInit(): void {
    this.email = localStorage.getItem('accountEmail') || '';
    
    this.evaluationIdSub = this.storageService.evaluationId$.subscribe((id) => {
      this.disableEvaluateButton = id !== null;
    });

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

  openNewEvalModal() {
    this.showNewEvalModal = true;
    this.newEvalCourseLink = '';
    this.newEvalScan = '';
  }

  closeNewEvalModal() {
    this.showNewEvalModal = false;
  }

  canEvaluate(): boolean {
    return !!this.newEvalCourseLink && !!this.newEvalScan;
  }

  evaluateNew() {
    if (!this.canEvaluate()) return;
    this.evaluate();
    this.closeNewEvalModal();
  }

  onSelectEvaluation(item: any, index: number) {
    if (!item) return;
    this.openCardIndex = null;
    this.router.navigate(['/evaluation', item.id]);
  }

  evaluate(): void {
    const scanRequest: ScanRequest = { 
      course_link: this.newEvalCourseLink,
      email: this.email,
      scan_name: this.newEvalScan
    }

    this.evaluationService.evaluate(scanRequest).subscribe({
      next: (response) => {
        this.router.navigate(['/evaluation', response.body.evaluation_id]);
      },
      error: (error) => {
        console.error('Evaluation error:', error);
      }
    });
  }

  ngOnDestroy() {
    if (this.evaluationIdSub) this.evaluationIdSub.unsubscribe();
  }
}
