// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Router } from '@angular/router';
import { Notification } from '../../interfaces/notification';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-notification-modal-component',
  imports: [
    MatButtonModule,
    MatIconModule
  ],
  templateUrl: './notification-modal-component.html',
  styleUrl: './notification-modal-component.css',
})
export class NotificationModalComponent {
  @Input() selectedNotification: Notification | null = null;
  @Output() close = new EventEmitter<void>();

  constructor (
    private router: Router
  ) {}

  goToEvaluation(id: number, scanName: string): void {
    this.router.navigate(['/evaluation', id], {
      queryParams: { scan: scanName }
    });
  }

  closeNotificationModal(): void {
    this.close.emit();
  }
}
