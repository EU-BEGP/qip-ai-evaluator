import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ReactiveFormsModule } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatIconModule } from '@angular/material/icon';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { EvaluationService } from '../../services/evaluation-service';
import { MatSelectModule } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { SearchComponent } from '../../components/search-component/search-component';
import { Subscription } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import { StorageService } from '../../services/storage-service';
import { ActivatedRoute } from '@angular/router';
import { Scan } from '../../interfaces/scan';
import { UtilsService } from '../../services/utils-service';

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
  ],
  templateUrl: './evaluation.html',
  styleUrl: './evaluation.css',
  standalone: true
})
export class EvaluationComponent {
  private pollingSub?: Subscription;
  private evaluationIdSub?: Subscription;

  linkModule = '';
  disableEvaluateButton = false;
  evaluationId?: string;
  loaded: boolean = false;
  scansList: Scan[] = [];

  constructor (
    private toastr: ToastrService,
    private evaluationService: EvaluationService,
    private storageService: StorageService,
    private route: ActivatedRoute,
    private utilsService: UtilsService
  ) {}

  ngOnInit() {
    const params = this.route.snapshot.paramMap;
    this.evaluationId = params.get('id') || undefined;

    if (this.evaluationId !== undefined) {
      this.evaluationService.getLinkModule(this.evaluationId).subscribe({
        next: (response) => {
          this.linkModule = response.course_link;
          this.evaluationService.getIdsList(this.evaluationId!).subscribe({
            next: (response) => {
              this.scansList = response;
              this.loaded = true;
            }
          });
        }
      });
    }
    else {
      this.loaded = true;
    }

    this.startPolling();
    this.evaluationIdSub = this.storageService.evaluationId$.subscribe((id) => {
      this.disableEvaluateButton = id !== null;
    });
  }

  startPolling(): void {
    const isAll = localStorage.getItem('isAll' + localStorage.getItem('accountEmail'));
    const evaluationId = localStorage.getItem('evaluationId' + localStorage.getItem('accountEmail'));

    if(evaluationId && isAll) {
      this.storageService.setEvaluationId(evaluationId);
      
      if (isAll == 'true') {
        this.pollingSub = this.evaluationService.getStatusModule(evaluationId!)
        .subscribe({
          next: (response) => {
            if (response.status === 'In Progress') {
              if (response.evaluation_id === this.evaluationId) {
                const index = this.getScanIndexByName(response.scan_name);
                this.updateData(index, response.scan_name, evaluationId);
              }
            }
            else if (response.status === 'Completed') {
              if (response.evaluation_id === this.evaluationId) {
                const index = this.getScanIndexByName(response.scan_name);
                this.finishEvaluation();
              }
              this.toastr.success('The evaluation related to the scan: “' + response.scan_name + '” and the course key: “' + response.course_key +'” was finished.', 'Evaluation completed');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
              this.storageService.clearEvaluationId();
            }
            else if (response.status === 'Failed') {
              this.toastr.error('Something went wrong during the evaluation. Please try again.', 'Error');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
              this.storageService.clearEvaluationId();
            }
          },
          error: (err) => {
            console.error('Error checking status:', err);
          }
        });
      }
      else {
        this.pollingSub = this.evaluationService.getStatusScan(evaluationId!)
        .subscribe({
          next: (response) => {
            if (response.status === 'In Progress') {
              if (response.evaluation_id === this.evaluationId) {
                const index = this.getScanIndexByName(response.scan_name);
                this.updateData(index, response.scan_name, evaluationId);
              }
            }
            else if (response.status === 'Completed') {
              if (response.evaluation_id === this.evaluationId) {
                const index = this.getScanIndexByName(response.scan_name);
                this.finishEvaluation();
              }
              this.toastr.success('The evaluation related to the scan: “' + response.scan_name + '” and the course key: “' + response.course_key +'” was finished.', 'Evaluation completed');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
              this.storageService.clearEvaluationId();
            }
            else if (response.status === 'Failed') {
              this.toastr.error('Something went wrong during the evaluation. Please try again.', 'Error');
              localStorage.removeItem('evaluationId' + localStorage.getItem('accountEmail'));
              localStorage.removeItem('isAll' + localStorage.getItem('accountEmail'));
              this.storageService.clearEvaluationId();
            }
          },
          error: (err) => {
            console.error('Error checking status:', err);
          }
        });
      }
    }
  }

  finishEvaluation(): void {
    this.evaluationService.getIdsList(this.evaluationId!).subscribe({
      next: (response) => {
        this.scansList = response;
      }
    });
  }

  updateData(index: number, scanName: string, evaluationId: string): void {
    this.scansList[index].evaluable = false;
    if (scanName === 'All Scans') {
      this.evaluationService.getEvaluationDetailModule(Number(evaluationId)).subscribe({
        next: (response) => {
          this.scansList[index].updated_data = response;
        }
      })
    }
    else {
      this.evaluationService.getEvaluationDetailScan(Number(evaluationId)).subscribe({
        next: (response) => {
          this.scansList[index].updated_data = response;
        }
      })
    }
  }

  getNameShort(value: string): string {
    if (!value) return "";

    const parts = value.trim().split(" ");

    if (parts.length <= 1) return value;

    parts.pop();
    return parts.join(" ");
  }

  getScanIndexByName(name: string): number {
    return this.scansList.findIndex(scan => scan.name === name);
  }

  download() {
    this.utilsService.downloadPDF(this.evaluationId!).subscribe((data: Blob) => {
      const pdfUrl = window.URL.createObjectURL(data);
      const link = document.createElement('a');

      link.href = pdfUrl;
      link.download = 'report.pdf';
      link.click();

      window.URL.revokeObjectURL(pdfUrl);
    });
  }

  ngOnDestroy() {
    //if (this.pollingSub) this.pollingSub.unsubscribe();
    if (this.evaluationIdSub) this.evaluationIdSub.unsubscribe();
  }
}
