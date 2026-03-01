import { Component, Input, Output, EventEmitter } from '@angular/core';

@Component({
  selector: 'peer-review-message-model',
  templateUrl: './peer-review-message-model-component.html',
  styleUrls: ['./peer-review-message-model-component.css'],
})
export class PeerReviewMessageModelComponent {
  @Input() message: string = '';
  @Input() visible: boolean = true;
  @Output() closed = new EventEmitter<void>();

  close() {
    this.visible = false;
    this.closed.emit();
  }
}
