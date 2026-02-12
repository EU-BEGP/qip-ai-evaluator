// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatListModule } from '@angular/material/list';
import { Notification } from '../../interfaces/notification';
import { NotificationService } from '../../services/notification-service';
import { NotificationModalComponent } from '../../components/notification-modal-component/notification-modal-component';
import { NotificationCardComponent } from '../../components/notification-card-component/notification-card-component';

@Component({
  selector: 'app-notifications',
  imports: [
    MatListModule,
    CommonModule,
    NotificationModalComponent,
    NotificationCardComponent
  ],
  templateUrl: './notifications.html',
  styleUrl: './notifications.css',
})
export class Notifications {
  notifications: any[] = [];
  email: string = '';
  showNotificationModal: boolean = false;
  selectedNotification: Notification | null = null;

  constructor (
    private notificationService: NotificationService
  ) {}

  ngOnInit(): void {
    this.email = localStorage.getItem('accountEmail') || '';
    this.notificationService.getNotifications(this.email).subscribe({
      next: (response) => {
        this.notifications = response;
      }
    })
  }

  read(notification: Notification): void {
    const notificationRequest = { email: this.email, message_id: notification.id };

    if (!notification.read) {
      this.notificationService.readMessage(notificationRequest).subscribe({
        next: (response) => {
          notification.read = true;
        }
      })
    }

    this.openNotificationModal(notification);
  }

  openNotificationModal(notification: Notification): void {
    this.selectedNotification = notification;
    this.showNotificationModal = true;
  }

  closeNotificationModal(): void {
    this.showNotificationModal = false;
    this.selectedNotification = null;
  }
}
