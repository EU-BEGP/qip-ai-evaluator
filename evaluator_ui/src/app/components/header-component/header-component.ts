// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

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
  email!: string;

  constructor (
    private router: Router,
    public notificationService: NotificationService
  ) {
    this.email = localStorage.getItem('accountEmail')!
  }

  toggleAuth(): void {
    if (this.email) {
      this.logout();
    } else {
      this.goToLogin();
    }
  }

  goToLogin(): void {
    this.router.navigateByUrl('login');
  }

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
