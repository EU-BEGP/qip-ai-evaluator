// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { CriterionCardComponent } from '../../components/criterion-card-component/criterion-card-component';
import { SelfEvaluationService } from '../../services/self-evaluation-service';
import { PeerReviewService } from '../../services/peer-review-service';
import { Router } from '@angular/router';
import { PageTitleComponent } from '../../components/page-title-component/page-title-component';

@Component({
  selector: 'app-peer-review',
  imports: [CommonModule, CriterionCardComponent, PageTitleComponent],
  templateUrl: './peer-review.html',
  styleUrls: ['./peer-review.css'],
  standalone: true,
})
export class PeerReview implements OnInit {
  scans: Array<{ id: number; name: string }> = [];
  currentScan: { id: number; name: string } | null = null;
  criterions: Array<{
    id: number;
    question: string;
    description: string;
    peer_selection?: string;
    peer_note?: string;
    buttons?: Array<{
      label: string;
      value?: any;
      state?: boolean;
    }>;
  }> = [];
  selectedCriterion: {
    id: number;
    question: string;
    description: string;
    peer_selection?: string;
    peer_note?: string;
    buttons?: Array<{
      label: string;
      value?: any;
      state?: boolean;
    }>;
  } | null = null;
  evaluationId: string | null = null;
  evaluatorId: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private selfEval: SelfEvaluationService,
    private peerRev: PeerReviewService,
  ) {}

  ngOnInit(): void {
    const peerToken = this.route.snapshot.paramMap.get('id');
    if (peerToken) {
      this.peerRev.getEvaluationData(peerToken).subscribe({
        next: (res) => {
          if (res && res.evaluation_id && res.evaluatorId) {
            this.evaluationId = res.evaluation_id;
            this.evaluatorId = res.evaluatorId;
            this.loadScans(res.evaluation_id);
          }
        },
        error: (err) => console.error('Failed getting evaluation data', err),
      });
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

    this.selfEval
      .getCriterions(String(scan.id), String(this.evaluatorId))
      .subscribe({
        next: (res: any) => {
          this.criterions = res.criterions || [];
          this.criterions.map((c) => {
            c.buttons = [
              {
                label: '0',
                value: 0,
                state: c.peer_selection === '0',
              },
              {
                label: '0.5',
                value: 0.5,
                state: c.peer_selection === '0.5',
              },
              {
                label: '1',
                value: 1,
                state: c.peer_selection === '1',
              },
              {
                label: '1.5',
                value: 1.5,
                state: c.peer_selection === '1.5',
              },
              {
                label: '2',
                value: 2,
                state: c.peer_selection === '2',
              },
              {
                label: '3.5',
                value: 3.5,
                state: c.peer_selection === '3.5',
              },
              {
                label: '4',
                value: 4,
                state: c.peer_selection === '4',
              },
              {
                label: '4.5',
                value: 4.5,
                state: c.peer_selection === '4.5',
              },
              {
                label: '5',
                value: 5,
                state: c.peer_selection === '5',
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
    peer_selection?: string;
    peer_note?: string;
    buttons?: Array<{
      label: string;
      value?: any;
      state?: boolean;
    }>;
  }) {
    this.selectedCriterion = c as any;
  }

  onCriterionAction(
    event: { value: any },
    criterion: {
      id: number;
      question: string;
      description: string;
      peer_selection?: string;
      peer_note?: string;
      buttons?: Array<{
        label: string;
        value?: any;
        state?: boolean;
      }>;
    },
  ) {
    this.peerRev
      .updatePeerCriterion(
        this.evaluationId!,
        String(criterion.id),
        this.evaluatorId!,
        event.value,
        criterion.peer_note || '',
      )
      .subscribe({
        next: () => {
          criterion.peer_selection = event.value;
          criterion.buttons?.map((b) => (b.state = b.value === event.value));
          console.log('Criterion updated successfully');
        },
        error: (err) => console.error('Failed updating criterion', err),
      });
  }

  onCriterionNoteFill(
    event: { note: string },
    criterion: {
      id: number;
      question: string;
      description: string;
      peer_selection?: string;
      peer_note?: string;
      buttons?: Array<{
        label: string;
        value?: any;
        state?: boolean;
      }>;
    },
  ) {
    if (event.note) {
      criterion.peer_note = event.note;
    }

    const buttonValue = criterion.buttons?.find((b) => b.state)?.value;

    if (buttonValue === undefined) {
      console.error('Cannot add note without selecting a value first');
      return;
    }

    this.peerRev
      .updatePeerCriterion(
        this.evaluationId!,
        String(criterion.id),
        this.evaluatorId!,
        buttonValue,
        event.note,
      )
      .subscribe({
        next: () => {
          criterion.peer_note = event.note;
          console.log('Criterion note updated successfully');
        },
        error: (err) => console.error('Failed updating criterion note', err),
      });
  }
}
