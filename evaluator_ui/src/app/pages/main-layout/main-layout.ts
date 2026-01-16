// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from '../../components/header-component/header-component';
import { interval, Subject, switchMap, takeUntil } from 'rxjs';
import { NotificationService } from '../../services/notification-service';
import { FooterComponent } from '../../components/footer-component/footer-component';
import { ToastrService } from 'ngx-toastr';
import config from '../../config.json'

@Component({
  selector: 'app-main-layout',
  imports: [
    RouterOutlet,
    HeaderComponent,
    FooterComponent
  ],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.css',
})
export class MainLayout {
  private notificationsInterval = config.time.notificationPolling * 1000;
  private destroy$ = new Subject<void>();
  
  unreadCount: number = 0;
  email: string = '';

  constructor (
    private toastr: ToastrService,
    private notificationsService: NotificationService
  ) {}

  ngOnInit(): void {
    this.startNotificationPolling();
    this.email = localStorage.getItem('accountEmail')!
  }

  startNotificationPolling() {
    interval(this.notificationsInterval)
      .pipe(
        takeUntil(this.destroy$),
        switchMap(() =>
          this.notificationsService.getUnreadNotificationsQuantity(this.email)
        )
      )
      .subscribe({
        next: (response) => {
          const newValue = response.quantity;
          const currentValue = this.notificationsService.unreadCount();

          if (newValue !== currentValue) {
            this.notificationsService.setUnreadCount(newValue);

            if (newValue > currentValue) {
              this.toastr.info('New activity detected in your evaluations. Please review your notifications for the latest updates.');
            }
          }
        },
        error: (error) => {
          console.error('Error in polling:', error);
        }
      });
  }

  ngOnDestroy() {
    this.destroy$.next();
    this.destroy$.complete();
  }
}
