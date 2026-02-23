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
        this.criterions.map((c) => {
          c.buttons = [
            {
              label: '0',
              value: 0,
              state: c.user_selection === '0',
            },
            {
              label: '0.5',
              value: 0.5,
              state: c.user_selection === '0.5',
            },
            {
              label: '1',
              value: 1,
              state: c.user_selection === '1',
            },
            {
              label: '1.5',
              value: 1.5,
              state: c.user_selection === '1.5',
            },
            {
              label: '2',
              value: 2,
              state: c.user_selection === '2',
            },
            {
              label: '3.5',
              value: 3.5,
              state: c.user_selection === '3.5',
            },
            {
              label: '4',
              value: 4,
              state: c.user_selection === '4',
            },
            {
              label: '4.5',
              value: 4.5,
              state: c.user_selection === '4.5',
            },
            {
              label: '5',
              value: 5,
              state: c.user_selection === '5',
            },
          ];
        });
      },
      error: (err) => console.error('Failed loading criterions', err),
    });
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
      },
      error: (err) => console.error('Failed updating criterion', err),
    });
  }
}
