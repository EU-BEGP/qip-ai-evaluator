// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, Input } from '@angular/core';

@Component({
  selector: 'app-alert-component',
  imports: [],
  templateUrl: './alert-component.html',
  styleUrl: './alert-component.css',
})
export class AlertComponent {
  @Input() message!: string;
}
