import { CommonModule } from '@angular/common';
import { Component } from '@angular/core';
import { MatListModule } from '@angular/material/list';
import { Notification } from '../../interfaces/notification';
import { NotificationService } from '../../services/notification-service';
import { MatButtonModule } from '@angular/material/button';

@Component({
  selector: 'app-notifications',
  imports: [
    MatListModule,
    MatButtonModule,
    CommonModule
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

    this.selectedNotification = notification;
    this.showNotificationModal = true;
  }

  closeNotificationModal(): void {
    this.showNotificationModal = false;
    this.selectedNotification = null;
  }
}
