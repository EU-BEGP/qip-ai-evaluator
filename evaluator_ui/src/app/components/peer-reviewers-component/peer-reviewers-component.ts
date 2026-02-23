// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon
import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { FormsModule } from '@angular/forms';

@Component({
  standalone: true,
  selector: 'peer-reviewers-component',
  imports: [CommonModule, MatButtonModule, MatIconModule, FormsModule],
  templateUrl: './peer-reviewers-component.html',
  styleUrls: ['./peer-reviewers-component.css'],
})
export class PeerReviewersComponent {
  @Output() closeModal = new EventEmitter<void>();

  inviteLink: string = 'http://example.com/invite/abcd1234';
  emails: string[] = [''];

  constructor() {}

  private validateEmail(email: string): boolean {
    return (
      email.split('@').length === 2 &&
      email.split('@')[1].split('.').length >= 2
    );
  }

  addEmail(index?: number) {
    if (index === undefined || index === null) {
      this.emails.push('');
    } else {
      this.emails.splice(index + 1, 0, '');
    }
  }

  deleteEmail(index: number) {
    if (this.emails.length > 1) {
      this.emails.splice(index, 1);
    } else {
      // keep at least one empty row
      this.emails[0] = '';
    }
  }

  copyLink() {
    if (navigator && navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(this.inviteLink).then(() => {
        alert('Invite link copied to clipboard!');
      });
    } else {
      const el = document.createElement('textarea');
      el.value = this.inviteLink;
      document.body.appendChild(el);
      el.select();
      try {
        document.execCommand('copy');
      } finally {
        document.body.removeChild(el);
      }
    }
  }

  closePeerReviewModal() {
    this.closeModal.emit();
    const modal = document.getElementById('peer-review-modal');
    if (modal) {
      modal.style.display = 'none';
    }
  }
}
