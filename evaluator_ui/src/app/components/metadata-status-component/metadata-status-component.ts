// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule, NgClass } from '@angular/common';
import { Component, Input } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';

@Component({
  selector: 'app-metadata-status-component',
  imports: [
    NgClass,
    CommonModule,
    MatIconModule
],
  templateUrl: './metadata-status-component.html',
  styleUrl: './metadata-status-component.css',
})
export class MetadataStatusComponent {
  @Input() title!: string;
  @Input() status!: string;
  @Input() description!: string;
  expanded: boolean = false;

  private readonly statusConfig: Record<string, { icon: string; badge: string; alert: string }> = {
    GOOD: {
      icon: 'check_circle',
      badge: 'bg-success',
      alert: 'alert-success',
    },
    CRITICAL: {
      icon: 'error',
      badge: 'bg-danger',
      alert: 'alert-danger',
    },
    MISSING: {
      icon: 'warning',
      badge: 'bg-warning',
      alert: 'alert-warning',
    },
  };

  getStatusIcon(): string {
    return this.statusConfig[this.status]?.icon;
  }

  getBadgeClass(): string {
    return this.statusConfig[this.status]?.badge;
  }

  getAlertClass(): string {
    return this.statusConfig[this.status]?.alert;
  }

  toggleExpand(): void {
    this.expanded = !this.expanded;
  }
}
