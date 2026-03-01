import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-peer-review-message-model',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './peer-review-message-model-component.html',
  styleUrls: ['./peer-review-message-model-component.css'],
})
export class PeerReviewMessageModelComponent {
  @Input() message: string = '';
  @Input() visible: boolean = true;
  @Output() close = new EventEmitter<void>();

  closeModal() {
    this.visible = false;
    this.close.emit();
  }
}
