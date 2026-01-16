// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, EventEmitter, Input, Output } from '@angular/core';
import { Notification } from '../../interfaces/notification';

@Component({
  selector: 'app-notification-card-component',
  imports: [],
  templateUrl: './notification-card-component.html',
  styleUrl: './notification-card-component.css',
})
export class NotificationCardComponent {
  @Input() notification!: Notification;
  @Output() read = new EventEmitter<Notification>();

  clickNotification() {
    this.read.emit(this.notification);
  }
}
