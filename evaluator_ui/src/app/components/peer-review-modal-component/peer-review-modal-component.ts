// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon


import { Component, EventEmitter, Output } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-peer-review-modal-component',
  imports: [
    MatButtonModule,
    MatIconModule,
  ],
  templateUrl: './peer-review-modal-component.html',
  styleUrl: './peer-review-modal-component.css',
})
export class PeerReviewModalComponent {
  @Output() closeModalEvent = new EventEmitter<void>();

  closePeerReviewModal() {
    this.closeModalEvent.emit();
  }
}
