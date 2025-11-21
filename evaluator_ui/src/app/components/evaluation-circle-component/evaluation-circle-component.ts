import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { NgCircleProgressModule } from 'ng-circle-progress';

@Component({
  standalone: true,
  selector: 'app-evaluation-circle-component',
  imports: [CommonModule, NgCircleProgressModule],
  templateUrl: './evaluation-circle-component.html',
  styleUrl: './evaluation-circle-component.css',
})
export class EvaluationCircleComponent {
  @Input() obtained!: number;
  @Input() max!: number;
  @Input() label: string = '';
  @Input() title: boolean = false;
  @Input() small: boolean = false;

  percentage = 0;

  ngOnInit(): void {
    this.percentage = this.calculatePercentage();
  }

  private calculatePercentage(): number {
    if (!this.max || this.max <= 0) return 0;
    const p = (this.obtained / this.max) * 100;
    return Math.max(0, Math.min(100, Math.round(p)));
  }
}
