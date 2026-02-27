// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon
import { Component, EventEmitter, Input, Output, OnInit } from '@angular/core';
import { MatCardModule } from '@angular/material/card';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';

@Component({
  standalone: true,
  selector: 'app-criterion-card-component',
  imports: [MatCardModule, CommonModule, MatButtonModule],
  templateUrl: './criterion-card-component.html',
  styleUrls: ['./criterion-card-component.css'],
})
export class CriterionCardComponent implements OnInit {
  @Input() question: string = '';
  @Input() description: string = '';
  @Input() buttons: Array<{
    label: string;
    value?: any;
    state?: boolean;
    disabled?: boolean;
  }> = [];
  @Input() hasAI: boolean = false;
  @Input() hasNote: boolean = false;
  @Input() peerNote: string = '';
  @Input() aiLoading: boolean = false;

  @Output() buttonClick = new EventEmitter<{ value: any }>();
  @Output() aiClick = new EventEmitter<void>();
  @Output() noteFill = new EventEmitter<{ note: string }>();

  constructor() {}

  ngOnInit(): void {}

  onButtonClick(
    btn: { label: string; value?: any; state?: boolean; disabled?: boolean },
    event: MouseEvent,
  ) {
    event.stopPropagation();
    if (!btn.state) {
      this.buttons.forEach((b) => (b.state = false));
      btn.state = !btn.state;
    }
    if (!btn.disabled) {
      this.buttonClick.emit({ value: btn.value ?? btn.label });
    }
  }

  onAiClick(event: MouseEvent) {
    event.stopPropagation();
    this.aiClick.emit();
  }

  onNoteFill(event: Event) {
    event.stopPropagation();
    const target = event.target as HTMLInputElement;
    this.noteFill.emit({ note: target.value });
  }
}
