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
import { ToastrService } from 'ngx-toastr';
import { MatIconModule } from '@angular/material/icon';
import { PeerReviewMessageModelComponent } from '../../components/peer-review-message-model-component/peer-review-message-model-component';

@Component({
  selector: 'app-peer-review',
  imports: [
    CommonModule,
    CriterionCardComponent,
    PageTitleComponent,
    MatIconModule,
    PeerReviewMessageModelComponent,
  ],
  templateUrl: './peer-review.html',
  styleUrls: ['./peer-review.css'],
})
export class PeerReview implements OnInit {
  scans: Array<{ id: number; name: string }> = [];
  currentScan: { id: number; name: string } | null = null;
  currentScanIndex = 0;
  maxUnlockedIndex = 0;
  scanCompletion: { [scanId: number]: boolean } = {};
  doneEnabled = false;
  moduleName: string = '';
  finished = false;
  modalMessage = '';

  highlightedIndex: number | null = null;
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
  token: string | null = null;

  constructor(
    private route: ActivatedRoute,
    private selfEval: SelfEvaluationService,
    private peerRev: PeerReviewService,
    private router: Router,
    private toast: ToastrService,
  ) {}

  ngOnInit(): void {
    const peerToken = this.route.snapshot.paramMap.get('token');
    if (!peerToken) {
      this.router.navigate(['/']);
      return;
    }
    this.token = peerToken;
    this.getModuleName(peerToken)
      .then((ok) => {
        if (!ok) {
          return;
        }
        this.peerRev.getPeerReviewCompletionStatus(this.token!).subscribe({
          next: (res) => {
            if (res.scanComplete.length > 0) {
              this.loadScans(
                '',
                this.token!,
                res.scanComplete.filter((r) => r.isComplete).length,
              );
            }
          },
        });
      })
      .catch((err) => {
        console.error('Failed to get module name', err);
        this.router.navigate(['/']);
      });
  }

  getModuleName(token: string): Promise<boolean> {
    return new Promise((resolve, reject) => {
      this.peerRev.getModuleName(token).subscribe({
        next: (res) => {
          this.moduleName = res.module_name;
          resolve(true);
        },
        error: (err) => {
          if (err.status === 404) {
            this.finished = true;
            this.modalMessage = err.message || err.error?.message;
            resolve(false);
            return;
          }
          reject(err);
        },
      });
    });
  }

  loadScans(evaluationId: string, token: string, countCompleted: number = 0) {
    this.selfEval.getScans(evaluationId, token).subscribe({
      next: (res) => {
        this.scans = res.slice(1);

        this.maxUnlockedIndex = countCompleted;
        this.scanCompletion = {};
        this.doneEnabled = false;
        this.scans.forEach((s) => (this.scanCompletion[s.id] = false));
        if (this.scans.length > 0) {
          this.selectScan(this.scans[0], 0);
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

    if (this.highlightedIndex === index) {
      this.highlightedIndex = null;
    }
    if (!scan || !scan.id) return;

    this.selfEval.getCriterions(String(scan.id), this.token!).subscribe({
      next: (res: any) => {
        this.criterions = res.criterions || [];
        this.criterions.map((c) => {
          c.buttons = [
            { label: '0', value: 0, state: c.peer_selection === '0.0' },
            { label: '0.5', value: 0.5, state: c.peer_selection === '0.5' },
            { label: '1', value: 1, state: c.peer_selection === '1.0' },
            { label: '1.5', value: 1.5, state: c.peer_selection === '1.5' },
            { label: '2', value: 2, state: c.peer_selection === '2.0' },
            { label: '3.5', value: 3.5, state: c.peer_selection === '3.5' },
            { label: '4', value: 4, state: c.peer_selection === '4.0' },
            { label: '4.5', value: 4.5, state: c.peer_selection === '4.5' },
            { label: '5', value: 5, state: c.peer_selection === '5.0' },
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
        : true;

    this.scanCompletion[scanId] = allDone;

    if (allDone && this.currentScanIndex === this.maxUnlockedIndex) {
      const nextIndex = this.maxUnlockedIndex + 1;
      if (nextIndex < this.scans.length) {
        this.maxUnlockedIndex = nextIndex;
        // highlight unlocked scan
        this.highlightedIndex = nextIndex;
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
        this.token!,
        String(criterion.id),
        event.value,
        criterion.peer_note || '',
      )
      .subscribe({
        next: () => {
          criterion.peer_selection = event.value;
          criterion.buttons?.map((b) => (b.state = b.value === event.value));
          console.log('Criterion updated successfully');

          if (this.currentScan && this.currentScan.id) {
            this.updateScanCompletion(this.currentScan.id);
          }
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
        this.token!,
        String(criterion.id),
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

  onDone() {
    this.peerRev.endPeerReview(this.token!).subscribe({
      next: () => {
        this.finished = true;
        this.modalMessage = `Thank you so much for completing the peer review for the ${this.moduleName} module! Your feedback has been submitted.`;
        this.toast.success('Peer review completed successfully!');
      },
      error: (err) => {
        console.error('Failed submitting peer review', err);
        this.toast.error('Failed to submit peer review');
      },
    });
  }

  onCloseModal() {
    this.finished = false;
    this.router.navigate(['/']);
  }
}
