// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon
import { Component, EventEmitter, Output, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { FormsModule } from '@angular/forms';
import { PeerReviewService } from '../../services/peer-review-service';

@Component({
  standalone: true,
  selector: 'peer-reviewers-component',
  imports: [CommonModule, MatButtonModule, MatIconModule, FormsModule],
  templateUrl: './peer-reviewers-component.html',
  styleUrls: ['./peer-reviewers-component.css'],
})
export class PeerReviewersComponent {
  @Input() evaluationId: string = '';
  @Output() closeModal = new EventEmitter<void>();
  // Use objects with stable ids so Angular won't recreate DOM nodes
  emails: { id: string; value: string }[] = [];

  constructor(private peerReviewService: PeerReviewService) {}

  ngOnInit() {
    if (this.emails.length === 0) {
      this.emails.push({ id: this.generateId(), value: '' });
    }
  }

  private generateId() {
    return Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
  }

  trackById(_index: number, item: { id: string; value: string }) {
    return item.id;
  }

  private validateEmail(email: string): boolean {
    if (!email) return false;
    return (
      email.split('@').length === 2 &&
      email.split('@')[1].split('.').length >= 2
    );
  }

  addEmail(index?: number) {
    const item = { id: this.generateId(), value: '' };
    if (index === undefined || index === null) {
      this.emails.push(item);
    } else {
      this.emails.splice(index + 1, 0, item);
    }
  }

  deleteEmail(index: number) {
    if (this.emails.length > 1) {
      this.emails.splice(index, 1);
    } else {
      // keep at least one empty row
      this.emails[0].value = '';
    }
  }

  sendInvites() {
    const validEmails = this.emails
      .map((e) => e.value.trim())
      .filter((email) => this.validateEmail(email));
    if (validEmails.length === 0) {
      alert('Please enter at least one valid email address.');
      return;
    }

    if (!this.evaluationId) {
      alert('Evaluation ID is missing. Cannot send invitations.');
      return;
    }

    this.peerReviewService
      .requestPeerReview(this.evaluationId, validEmails)
      .subscribe({
        next: () => {
          alert('Invitations sent successfully!');
          this.closePeerReviewModal();
        },
        error: (err) => {
          console.error('Failed to send invitations', err);
          alert('Failed to send invitations. Please try again later.');
        },
      });
  }

  closePeerReviewModal() {
    this.closeModal.emit();
    const modal = document.getElementById('peer-review-modal');
    if (modal) {
      modal.style.display = 'none';
    }
  }
}
