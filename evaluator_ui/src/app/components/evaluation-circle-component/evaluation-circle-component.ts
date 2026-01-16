// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, Input, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgxGaugeModule } from 'ngx-gauge';

@Component({
  standalone: true,
  selector: 'app-evaluation-circle-component',
  imports: [CommonModule, NgxGaugeModule],
  templateUrl: './evaluation-circle-component.html',
  styleUrl: './evaluation-circle-component.css',
})
export class EvaluationCircleComponent implements OnChanges {
  @Input() obtained!: number;
  @Input() max!: number;
  @Input() label: string = '';
  @Input() title: boolean = false;
  @Input() small: boolean = false;

  thresholdConfig: Record<string, { color: string }> = { '0': { color: 'red' } };

  ngOnChanges(changes: SimpleChanges): void {
    if ('max' in changes || 'obtained' in changes) {
      this.thresholdConfig = this.generateThresholds(this.max);
    }
  }

  private generateThresholds(max: number) {
    if (!max || max <= 0) {
      return { '0': { color: 'red' } };
    }

    const redStart = 0;
    const orangeStart = max * 0.5;
    const greenStart = max * 0.8;

    return {
      [String(redStart)]: { color: 'red' },
      [String(orangeStart)]: { color: 'orange' },
      [String(greenStart)]: { color: 'green' },
    };
  }
}