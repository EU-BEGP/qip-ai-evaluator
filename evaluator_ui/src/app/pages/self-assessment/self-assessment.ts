// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { CriterionCardComponent } from '../../components/criterion-card-component/criterion-card-component';
import { SelfEvaluationService } from '../../services/self-evaluation-service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-self-assessment',
  imports: [CommonModule, CriterionCardComponent],
  templateUrl: './self-assessment.html',
  styleUrls: ['./self-assessment.css'],
  standalone: true,
})
export class SelfAssessment implements OnInit {
  scans: Array<{ id: number; name: string }> = [];
  currentScan: { id: number; name: string } | null = null;
  criterions: Array<{
    id: number;
    question: string;
    description: string;
    user_selection: string;
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

  onEvaluate() {
    this.router.navigate(['/evaluation', this.evaluationId]);
  }

  loadScans(evaluationId: string) {
    this.selfEval.getScans(evaluationId).subscribe({
      next: (res) => {
        this.scans = res;
        if (res.length > 0) {
          this.selectScan(res[0]);
        }
      },
      error: (err) => console.error('Failed loading scans', err),
    });
  }

  selectScan(scan: { id: number; name: string }) {
    this.currentScan = scan;
    this.criterions = [];
    this.selectedCriterion = null;
    if (!scan || !scan.id) return;

    this.selfEval.getCriterions(String(scan.id)).subscribe({
      next: (res: any) => {
        this.criterions = res.criterions || [];
      },
      error: (err) => console.error('Failed loading criterions', err),
    });
  }

  selectCriterion(c: {
    id: number;
    question: string;
    description: string;
    user_selection: string;
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
    },
  ) {
    this.selfEval.updateCriterion(String(criterion.id), event.value).subscribe({
      next: () => {
        criterion.user_selection = event.value;
        console.log('Criterion updated successfully');
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
    // auto-select the criterion immediately so the right column updates
    this.selectedCriterion = criterion as any;
    // clear any previous suggestion while we fetch a new one
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
                // map service result into the UI shape
                criterion.suggestion = {
                  result: res.result,
                  badge: (res.result || '')
                    .split(/[\.\n]/)[0]
                    .trim()
                    .toLowerCase(),
                };
                this.selectedCriterion = criterion as any;
                console.log('AI suggestion updated', res);
                // stop interval when suggestion is obtained
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
}
