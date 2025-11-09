import { Component } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatToolbarModule } from '@angular/material/toolbar';
import { Router } from '@angular/router';

@Component({
  selector: 'app-header-component',
  imports: [
    MatButtonModule, 
    MatIconModule,
    MatToolbarModule],
  templateUrl: './header-component.html',
  styleUrl: './header-component.css',
})
export class HeaderComponent {
  constructor (
    private router: Router
  ) {}

  logout(): void {
    localStorage.removeItem('token');
    this.router.navigateByUrl('login');
  }
}
