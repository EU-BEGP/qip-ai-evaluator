// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { CriterionCardComponent } from '../../components/criterion-card-component/criterion-card-component';
import { SelfEvaluationService } from '../../services/self-evaluation-service';

// check why the ai suggestion appears duplicated, once in the third column and again right besides the card.
// fix it and make it work normally.

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
    user_selected: string;
    suggestion?: {
      result: string;
      badge: string;
    };
  }> = [];
  selectedCriterion: {
    id: number;
    question: string;
    description: string;
    user_selected: string;
    suggestion?: {
      result: string;
      badge: string;
    } | null;
  } | null = null;

  constructor(
    private route: ActivatedRoute,
    private selfEval: SelfEvaluationService,
  ) {}

  ngOnInit(): void {
    const moduleId = this.route.snapshot.paramMap.get('id');
    if (moduleId) {
      this.loadScans(moduleId);
    }
  }

  loadScans(moduleId: string) {
    this.selfEval.getScans(moduleId).subscribe({
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
    user_selected: string;
  }) {
    this.selectedCriterion = c as any;
  }

  onCriterionAction(
    event: { value: any },
    criterion: {
      id: number;
      question: string;
      description: string;
      user_selected: string;
    },
  ) {
    this.selfEval.updateCriterion(String(criterion.id), event.value).subscribe({
      next: () => {
        criterion.user_selected = event.value;
        console.log('Criterion updated successfully');
        // Optionally, refresh criterions or update UI state here
      },
      error: (err) => console.error('Failed updating criterion', err),
    });
  }

  onAiSuggestion(criterion: {
    id: number;
    question: string;
    description: string;
    user_selected: string;
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
