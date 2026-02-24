// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { CriterionCardComponent } from '../../components/criterion-card-component/criterion-card-component';
import { SelfEvaluationService } from '../../services/self-evaluation-service';
import { Router } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { PageTitleComponent } from '../../components/page-title-component/page-title-component';
import { AlertComponent } from '../../components/alert-component/alert-component';

@Component({
  selector: 'app-self-assessment',
  imports: [
    CommonModule,
    CriterionCardComponent,
    MatIconModule,
    PageTitleComponent,
    AlertComponent,
  ],
  templateUrl: './self-assessment.html',
  styleUrls: ['./self-assessment.css'],
  standalone: true,
})
export class SelfAssessment implements OnInit {
  isOutdated = false;
  scans: Array<{ id: number; name: string }> = [];
  currentScan: { id: number; name: string } | null = null;
  currentScanIndex = 0;
  maxUnlockedIndex = 0;
  scanCompletion: { [scanId: number]: boolean } = {};
  doneEnabled = false;
  criterions: Array<{
    id: number;
    question: string;
    description: string;
    user_selection: string;
    buttons?: Array<{
      label: string;
      value?: any;
      state?: boolean;
    }>;
    suggestion?: {
      result: string;
      badge: string;
    };
  }> = [];
  selectedCriterion: {
    id: number;
    question: string;
    description: string;
    user_selection: string;
    buttons?: Array<{
      label: string;
      value?: any;
      state?: boolean;
    }>;
    suggestion?: {
      result: string;
      badge: string;
    } | null;
  } | null = null;
  evaluationId: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private selfEval: SelfEvaluationService,
    private router: Router,
  ) {}

  ngOnInit(): void {
    this.evaluationId = this.route.snapshot.paramMap.get('id');
    if (this.evaluationId) {
      this.loadScans(this.evaluationId);
    }
  }

  loadScans(evaluationId: string) {
    this.selfEval.getScans(evaluationId).subscribe({
      next: (res) => {
        this.scans = res;
        this.isOutdated = res.outdated || false;
        this.maxUnlockedIndex = 0;
        this.scanCompletion = {};
        this.doneEnabled = false;

        this.scans.forEach((s) => (this.scanCompletion[s.id] = false));
        if (res.length > 0) {
          this.selectScan(res[0], 0);
        }
      },
      error: (err) => console.error('Failed loading scans', err),
    });
  }
  selectScan(scan: { id: number; name: string }, index: number) {
    if (index > this.maxUnlockedIndex) return;
    this.currentScan = scan;
    this.currentScanIndex = index;
    this.criterions = [];
    this.selectedCriterion = null;
    if (!scan || !scan.id) return;

    this.selfEval.getCriterions(String(scan.id)).subscribe({
      next: (res: any) => {
        this.criterions = res.criterions || [];
        this.criterions.map((c) => {
          c.buttons = [
            {
              label: 'Yes',
              value: 'yes',
              state: (c.user_selection || '').toLowerCase() === 'yes',
            },
            {
              label: 'No',
              value: 'no',
              state: (c.user_selection || '').toLowerCase() === 'no',
            },
            {
              label: 'Not applicable',
              value: 'not applicable',
              state:
                (c.user_selection || '').toLowerCase() === 'not applicable',
            },
          ];
        });

        this.updateScanCompletion(scan.id);
      },
      error: (err) => console.error('Failed loading criterions', err),
    });
  }

  private updateScanCompletion(scanId: number) {
    const allDone =
      this.criterions && this.criterions.length > 0
        ? this.criterions.every(
            (c) => !!c.buttons && c.buttons.some((b) => b.state),
          )
        : true; // if no criterions, treat as completed

    this.scanCompletion[scanId] = allDone;

    if (allDone && this.currentScanIndex === this.maxUnlockedIndex) {
      if (this.maxUnlockedIndex < this.scans.length - 1) {
        this.maxUnlockedIndex++;
      }
    }

    const lastScan = this.scans.length
      ? this.scans[this.scans.length - 1]
      : null;
    if (lastScan) {
      this.doneEnabled = !!this.scanCompletion[lastScan.id];
    } else {
      this.doneEnabled = false;
    }
  }

  selectCriterion(c: {
    id: number;
    question: string;
    description: string;
    user_selection: string;
    buttons?: Array<{
      label: string;
      value?: any;
      state?: boolean;
    }>;
    suggestion?: {
      result: string;
      badge: string;
    } | null;
  }) {
    this.selectedCriterion = c as any;
  }

  onCriterionAction(
    event: { value: any },
    criterion: {
      id: number;
      question: string;
      description: string;
      user_selection: string;
      buttons?: Array<{
        label: string;
        value?: any;
        state?: boolean;
      }>;
    },
  ) {
    this.selfEval.updateCriterion(String(criterion.id), event.value).subscribe({
      next: () => {
        criterion.user_selection = event.value;
        criterion.buttons?.map((b) => (b.state = b.value === event.value));
        console.log('Criterion updated successfully');

        if (this.currentScan && this.currentScan.id) {
          this.updateScanCompletion(this.currentScan.id);
        }
      },
      error: (err) => console.error('Failed updating criterion', err),
    });
  }

  onAiSuggestion(criterion: {
    id: number;
    question: string;
    description: string;
    user_selection: string;
    suggestion?: {
      result: string;
      badge: string;
    } | null;
  }) {
    if (!this.currentScan || !criterion) return;

    this.selectedCriterion = criterion as any;

    criterion.suggestion = null as any;

    this.selfEval
      .requestAiSuggestion(
        String(criterion.id),
        criterion.question,
        criterion.description,
      )
      .subscribe({
        next: () => {
          const intervalId = setInterval(() => {
            this.selfEval.getAiSuggestion(String(criterion.id)).subscribe({
              next: (res: { result: string }) => {
                criterion.suggestion = {
                  result: res.result,
                  badge: (res.result || '')
                    .split(/[\.\n]/)[0]
                    .trim()
                    .toLowerCase(),
                };
                this.selectedCriterion = criterion as any;
                console.log('AI suggestion updated', res);

                if (res && res.result) {
                  clearInterval(intervalId);
                }
              },
              error: (err) => {
                console.error('Failed to get AI suggestion', err);
                clearInterval(intervalId);
              },
            });
          }, 3000);
        },
        error: (err) => console.error('AI suggestion failed', err),
      });
  }

  onResults() {
    this.router.navigate(['results'], { relativeTo: this.route });
  }
}
