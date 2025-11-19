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
import { MatSelectModule, MatSelectChange } from '@angular/material/select';
import { MatTabsModule } from '@angular/material/tabs';
import { SearchComponent } from '../../components/search-component/search-component';
import { Subscription } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import { StorageService } from '../../services/storage-service';
import { ActivatedRoute } from '@angular/router';

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
    SearchComponent
  ],
  templateUrl: './evaluation.html',
  styleUrl: './evaluation.css',
  standalone: true
})
export class EvaluationComponent {
  private poolingSub?: Subscription;
  private evaluationIdSub?: Subscription;

  linkModule = '';
  disableEvaluateButton = false;
  evaluationId?: string;
  loaded: boolean = false;
  scansList: { name: string; id: number | undefined | null; evaluable: boolean; updatedData?: any, scan_max: number, scan_average: number | null }[] = [];

  constructor (
    private toastr: ToastrService,
    private evaluationService: EvaluationService,
    private storageService: StorageService,
    private route: ActivatedRoute
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

    this.startPooling();
    this.evaluationIdSub = this.storageService.evaluationId$.subscribe((id) => {
      this.disableEvaluateButton = id !== null;
    });
  }

  startPooling(): void {
    const isAll = localStorage.getItem('isAll' + localStorage.getItem('accountEmail'));
    const evaluationId = localStorage.getItem('evaluationId' + localStorage.getItem('accountEmail'));

    if(evaluationId && isAll) {
      this.storageService.setEvaluationId(evaluationId);
      
      if (isAll == 'true') {
        this.poolingSub = this.evaluationService.getStatusModule(evaluationId!)
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
                this.finishEvaluation(index, response.scan_name, evaluationId);
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
        this.poolingSub = this.evaluationService.getStatusScan(evaluationId!)
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
                this.finishEvaluation(index, response.scan_name, evaluationId);
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

  finishEvaluation(index: number, scanName: string, evaluationId: string): void {
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
          this.scansList[index].updatedData = response;
        }
      })
    }
    else {
      this.evaluationService.getEvaluationDetailScan(Number(evaluationId)).subscribe({
        next: (response) => {
          this.scansList[index].updatedData = response;
        }
      })
    }
  }

  getEmoji(id: number | undefined | null, scansList: any, index: number): string {
    if (index === 0) {
      const allValid = scansList.every(
        (scan: any) => scan.id !== null
      );
      return allValid ? ' ✅' : ' ❌';
    }
    
    if (id === null) {
      return ' ❌';
    }
    else {
      return ' ✅';
    }
  }

  getScanIndexByName(name: string): number {
    return this.scansList.findIndex(scan => scan.name === name);
  }

  ngOnDestroy() {
    //if (this.poolingSub) this.poolingSub.unsubscribe();
    if (this.evaluationIdSub) this.evaluationIdSub.unsubscribe();
  }
}
