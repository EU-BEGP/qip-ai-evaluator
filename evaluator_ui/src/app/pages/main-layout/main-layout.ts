import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HeaderComponent } from '../../components/header-component/header-component';
import { interval, Subject, switchMap, takeUntil } from 'rxjs';
import { NotificationService } from '../../services/notification-service';

@Component({
  selector: 'app-main-layout',
  imports: [
    RouterOutlet,
    HeaderComponent,
  ],
  templateUrl: './main-layout.html',
  styleUrl: './main-layout.css',
})
export class MainLayout {
  private destroy$ = new Subject<void>();
  unreadCount: number = 0;
  email: string = '';

  constructor (
    private notificationsService: NotificationService
  ) {}

  ngOnInit(): void {
    this.startNotificationPolling();
    this.email = localStorage.getItem('accountEmail')!
  }

  startNotificationPolling() {
    interval(4000)
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
