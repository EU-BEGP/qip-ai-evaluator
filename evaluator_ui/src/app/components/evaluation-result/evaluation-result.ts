// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, Input } from '@angular/core';
import { RouterLink } from "@angular/router";

@Component({
  selector: 'app-evaluation-result-component',
  imports: [
    CommonModule
],
  templateUrl: './evaluation-result.html',
  styleUrl: './evaluation-result.css',
})
export class EvaluationResultComponent {
  @Input() data!: any;
}
