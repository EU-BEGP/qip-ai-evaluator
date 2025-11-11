import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormControl, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EvaluationService } from '../../services/evaluation-service';
import { MatSelectModule, MatSelectChange } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { SearchComponent } from '../../components/search-component/search-component';
import { HeaderComponent } from '../../components/header-component/header-component';
import { Subscription } from 'rxjs';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'app-evaluation',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatCardModule,
    MatFormFieldModule,
    MatInputModule,
    MatIconModule,
    MatButtonModule,
    MatProgressSpinnerModule,
    MatSelectModule,
    MatTabsModule,
    SearchComponent,
    HeaderComponent
  ],
  templateUrl: './evaluation.html',
  styleUrl: './evaluation.css',
  standalone: true
})
export class EvaluationComponent {
  private poolingSub?: Subscription;

  currentTab = '';
  selectedTabIndex = 0;
  tabs = ['All Scans', 'Academic Metadata Scan', 'Learning Content Scan', 'Assessment Scan', 'Multimedia Scan', 'Certificate Scan', 'Summary Scan'];

  constructor (
    private toastr: ToastrService,
    private evaluationService: EvaluationService
  ) {}

  ngOnInit() {
    this.currentTab = this.tabs[this.selectedTabIndex];
    this.startPooling();
  }

  onTabChange(index: number): void {
    this.currentTab = this.tabs[index];
  }

  startPooling(): void {
    const isAll = localStorage.getItem('isAll' + localStorage.getItem('accountEmail'));
    const evaluationId = localStorage.getItem('evaluationId' + localStorage.getItem('accountEmail'));

    if(evaluationId && isAll) {
      if (isAll == 'true') {
        this.poolingSub = this.evaluationService.getStatusModule(evaluationId!)
        .subscribe({
          next: (response) => {
            if (response.status === 'Completed') {
              this.toastr.success('Please go to the tab corresponding to “' + response.scan_name + '” and enter the course key “' + response.course_key +'”.', 'Evaluation completed');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
            }
            else if (response.status === 'Failed') {
              this.toastr.error('Something went wrong during the evaluation. Please try again.', 'Error');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
            }
          },
          error: (err) => {
            console.error('Error checking status:', err);
          }
        });
      }
      else {
        this.poolingSub = this.evaluationService.getStatusScan(evaluationId!)
        .subscribe({
          next: (response) => {
            if (response.status === 'Completed') {
              this.toastr.success('Please go to the tab corresponding to “' + response.scan_name + '” and enter the course key “' + response.course_key +'”.', 'Evaluation completed');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
            }
            else if (response.status === 'Failed') {
              this.toastr.error('Something went wrong during the evaluation. Please try again.', 'Error');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
            }
          },
          error: (err) => {
            console.error('Error checking status:', err);
          }
        });
      }
    }
  }

  ngOnDestroy() {
    if (this.poolingSub) this.poolingSub.unsubscribe();
  }
}
