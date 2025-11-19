import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { Router } from '@angular/router';
import { NotificationService } from '../../services/notification-service';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-header-component',
  imports: [
    MatButtonModule, 
    MatIconModule,
    MatToolbarModule,
    CommonModule
  ],
  templateUrl: './header-component.html',
  styleUrl: './header-component.css',
})
export class HeaderComponent {
  constructor (
    private router: Router,
    public notificationService: NotificationService
  ) {}

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('accountEmail');
    this.router.navigateByUrl('login');
  }

  navigateToHome(): void {
    this.router.navigateByUrl('modules');
  }

  navigateToNotifications() {
    this.router.navigateByUrl('notifications');
  }
}
