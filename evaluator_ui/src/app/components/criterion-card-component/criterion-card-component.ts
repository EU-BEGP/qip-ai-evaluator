// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon
import { Component, EventEmitter, Input, Output, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { trigger, transition, style, animate } from '@angular/animations';

@Component({
  selector: 'app-criterion-card-component',
  imports: [MatCardModule, CommonModule, MatButtonModule],
  templateUrl: './criterion-card-component.html',
  styleUrls: ['./criterion-card-component.css'],
  animations: [
    trigger('clickAnimation', [
      transition('* => *', [
        style({ transform: 'scale(0.95)' }),
        animate('100ms ease-out', style({ transform: 'scale(1)' })),
      ]),
    ]),
  ],
})
export class CriterionCardComponent implements OnInit {
  @Input() question: string = '';
  @Input() description: string = '';
  @Input() buttons: Array<{
    label: string;
    value?: any;
    state?: boolean;
  }> = [];

  @Output() buttonClick = new EventEmitter<{ value: any }>();
  @Output() aiClick = new EventEmitter<void>();

  constructor() {}

  ngOnInit(): void {}

  onButtonClick(
    btn: { label: string; value?: any; state?: boolean },
    event: MouseEvent,
  ) {
    event.stopPropagation();
    if (!btn.state) {
      this.buttons.forEach((b) => (b.state = false));
      btn.state = !btn.state;
    }
    this.buttonClick.emit({ value: btn.value ?? btn.label });
  }

  onAiClick(event: MouseEvent) {
    event.stopPropagation();
    this.aiClick.emit();
  }
}
