// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

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
import { Subject, takeUntil } from 'rxjs';
import { StorageService } from '../../services/storage-service';
import { ActivatedRoute, Router } from '@angular/router';
import { Scan } from '../../interfaces/scan';
import { UtilsService } from '../../services/utils-service';
import { ScanItem } from '../../interfaces/scan-item';
import { ToastrService } from 'ngx-toastr';
import { ModuleInformationComponent } from '../../components/module-information-component/module-information-component';

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
    ModuleInformationComponent
  ],
  templateUrl: './evaluation.html',
  styleUrl: './evaluation.css',
  standalone: true
})
export class EvaluationComponent {
  private destroy$ = new Subject<void>();

  linkModule = '';
  evaluationId?: string;
  loaded: boolean = false;
  scansList: Scan[] = [];
  selectedIndex?: number;
  scanNameSelected: string = 'All Scans';

  constructor (
    private evaluationService: EvaluationService,
    private storageService: StorageService,
    private route: ActivatedRoute,
    private utilsService: UtilsService,
    private router: Router,
    private toastr: ToastrService
  ) {}

  ngOnInit() {
    this.evaluationId = this.route.snapshot.paramMap.get('id') || undefined;

    this.route.queryParamMap
    .pipe(takeUntil(this.destroy$))
    .subscribe(queryParams => {
      this.scanNameSelected = queryParams.get('scan') || 'All Scans';
      if (this.scansList.length > 0) {
        this.selectedIndex = this.getScanIndexByName(this.scanNameSelected);
      }
    });

    const storageKey = 'evaluationList' + localStorage.getItem('accountEmail');
    const list = JSON.parse(localStorage.getItem(storageKey) || '[]');

    if (this.evaluationId !== undefined) {
      this.evaluationService.getLinkModule(this.evaluationId).subscribe({
        next: (response) => {
          this.linkModule = response.course_link;
          this.evaluationService.getIdsList(this.evaluationId!).subscribe({
            next: (response) => {
              this.scansList = response;
              this.selectedIndex = this.getScanIndexByName(this.scanNameSelected);
              this.loaded = true;

              list.forEach((item: ScanItem) => {
                this.startPolling({ scan: item, refresh: false});
              });
            }
          });
        }
      });
    }
    else {
      this.loaded = true;
    }
  }

  startPolling({ scan, refresh }: { scan: ScanItem; refresh: boolean }): void {
    if (refresh) {
      this.evaluationService.getIdsList(this.evaluationId!).subscribe({
        next: (response) => {
          this.scansList = response;
        }
      });
    }

    const obs = scan.scan_name === 'All Scans'
      ? this.evaluationService.getStatusModule(scan.scan_id)
      : this.evaluationService.getStatusScan(scan.scan_id);

    obs.pipe(takeUntil(this.destroy$)).subscribe({
      next: (response) => {
        if (response.status === 'In Progress') {
          if (response.evaluation_id === this.evaluationId) {
            const index = this.getScanIndexByName(response.scan_name);
            this.updateData(index, response.scan_name, scan.scan_id);
          }
        }
        else if (response.status === 'Completed' || response.status === 'Incompleted' || response.status === 'Failed') {
          if (response.evaluation_id === this.evaluationId) {
            this.finishEvaluation();
          }
          this.storageService.removeEvaluation(scan.scan_id, response.scan_name);
        }
      },
      error: (err) => {
        this.toastr.error('Something went wrong with the streaming.', 'Error');
        this.storageService.removeEvaluation(scan.scan_id, scan.scan_name);
        console.error('Error checking status:', err);
      }
    });
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

  download(): void {
    this.utilsService.downloadPDF(this.evaluationId!).subscribe({
      next: (data: Blob) => {
        const pdfUrl = window.URL.createObjectURL(data);
        const link = document.createElement('a');

        link.href = pdfUrl;
        link.download = 'report.pdf';
        link.click();

        window.URL.revokeObjectURL(pdfUrl);
      },
      error: (err) => {
        this.toastr.error('Error downloading PDF.', 'Error');
      }
    });
  }

  isInProgress(scan: Scan): boolean {
    if ((scan.status === 'Creating' || scan.status === 'In Progress') && scan.evaluable === false) {
      return true;
    }
    else {
      return false;
    }
  }

  onTabChange(index: number): void {
    const scanName = this.scansList[index].name;

    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { scan: scanName },
      queryParamsHandling: 'merge'
    });
  }

  ngOnDestroy(): void {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
