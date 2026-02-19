// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon


import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { PeerReviewService } from '../../services/peer-review-service';
import { Review } from '../../interfaces/review';
import { Router } from '@angular/router';

@Component({
  selector: 'app-peer-review-modal-component',
  imports: [
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './peer-review-modal-component.html',
  styleUrl: './peer-review-modal-component.css',
})
export class PeerReviewModalComponent implements OnInit {
  @Input() evaluationId!: string;
  @Output() closeModalEvent = new EventEmitter<void>();

  reviews: Review[] = [];

  constructor(private peerReviewService: PeerReviewService,
              private router: Router
  ) {}

  ngOnInit(): void {
    this.peerReviewService.getPeerReviews(this.evaluationId).subscribe({
      next: (response) => {
        this.reviews = response;
      },
      error: (error) => {
        console.error(error);
      }
    });
  }

  closePeerReviewModal() {
    this.closeModalEvent.emit();
  }

  goToPeerReview(evaluationId: string, reviewId: number) {
    this.router.navigate(['/peer-review-evaluation', evaluationId, 'review', reviewId]);
  }
}
