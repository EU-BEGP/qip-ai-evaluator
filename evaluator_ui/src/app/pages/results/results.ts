// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { PageTitleComponent } from '../../components/page-title-component/page-title-component';
import { MatButtonModule } from '@angular/material/button';
import { SelfEvaluationService } from '../../services/self-evaluation-service';
import { ActivatedRoute, Router } from '@angular/router';
import { ResultCardComponent } from '../../components/result-card-component/result-card-component';
import { PeerReviewersComponent } from '../../components/peer-reviewers-component/peer-reviewers-component';
import { EvaluationService } from '../../services/evaluation-service';
import { ScanRequest } from '../../interfaces/scan-request';
import { firstValueFrom } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import { LoaderService } from '../../services/loader-service';
import { AlertComponent } from '../../components/alert-component/alert-component';
import { CommonModule } from '@angular/common';
import { UtilsService } from '../../services/utils-service';

@Component({
  selector: 'app-results',
  imports: [
    PageTitleComponent,
    MatButtonModule,
    ResultCardComponent,
    PeerReviewersComponent,
    AlertComponent,
    CommonModule
],
  templateUrl: './results.html',
  styleUrl: './results.css',
})
export class Results implements OnInit {
  evaluationId?: number;
  allScans: any = null;
  scans: any[] = [];
  showPeerReviewModal = false;
  email: string = '';
  isAssessmentCompleted: boolean = false;
  isOutdated: boolean = false;
  message: string = 'This evaluation belongs to a previous module version. Please start a new evaluation to continue.';
  loaded: boolean = false;

  constructor (
    private selfEvaluationService: SelfEvaluationService,
    private route: ActivatedRoute,
    private router: Router,
    private evaluationService: EvaluationService,
    private toastr: ToastrService,
    private loaderService: LoaderService,
    private utilsService: UtilsService
  ) {}

  ngOnInit(): void {
    this.email = localStorage.getItem('accountEmail')!;
    this.evaluationId = Number(this.route.snapshot.paramMap.get('id')) || undefined;

    this.selfEvaluationService.getResults(this.evaluationId!).subscribe({
      next: (response: any[]) => {
        this.allScans = response.find(scan => scan.name === 'All Scans') || null;
        this.scans = response.filter(scan => scan.name !== 'All Scans');
        this.selfEvaluationService.getStatus(this.evaluationId!).subscribe({
          next: (statusResponse: any) => {
            this.isOutdated = statusResponse.outdated;
            if (statusResponse.status !== 'Self Assessment') {
              this.isAssessmentCompleted = true;
            }
            this.loaded = true;
          }
        });
      },
      error: (error) => {
        console.error('Error fetching results:', error);
      }
    })
  }

  completeAssessment(): void {
    this.loaderService.show();
    const evaluationRequests = this.scans.map(scan => 
      firstValueFrom(this.evaluate(scan.name))
    );

    Promise.all(evaluationRequests).then(() => {
      this.loaderService.hide();
      this.toastr.success('Self assessment completed successfully.', 'Success');
      this.isAssessmentCompleted = true;
    }).catch((error) => {
      this.loaderService.hide();
      this.toastr.error('Something went wrong completing the self assessment.', 'Error');
      console.error('Batch evaluation error:', error);
    });
  }

  inviteReviewers(): void {
    this.showPeerReviewModal = true;
  }

  closePeerReviewModal(): void {
    this.showPeerReviewModal = false;
  }

  goBack(): void {
    this.router.navigate(['/self-assessment', this.evaluationId]);
  }

  evaluate(scanName: string): any {
    const scanRequest: ScanRequest = { 
      evaluation_id: this.evaluationId!,
      email: this.email,
      scan_name: scanName
    }

    return this.evaluationService.evaluate(scanRequest);
  }

  download(): void {
    this.utilsService.downloadBadge(this.evaluationId!.toString()).subscribe({
      next: (data: Blob) => {
        const pngUrl = window.URL.createObjectURL(data);
        const link = document.createElement('a');

        link.href = pngUrl;
        link.download = `EEDA_Quality_Badge_${this.evaluationId!}.png`;
        link.click();

        window.URL.revokeObjectURL(pngUrl);
      },
      error: (err) => {
        this.toastr.error('Error downloading Quality Badge.', 'Error');
      }
    });
  }
}
