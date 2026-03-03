// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { Router } from '@angular/router';
import { UtilsService } from '../../services/utils-service';
import { ToastrService } from 'ngx-toastr';

@Component({
  selector: 'app-evaluation-list-component',
  imports: [
    CommonModule,
    MatIconModule
  ],
  templateUrl: './evaluation-list-component.html',
  styleUrl: './evaluation-list-component.css',
})
export class EvaluationListComponent {
  @Input() moduleData!: any;
  @Output() peerReviewClick = new EventEmitter<void>();

  constructor(
    private router: Router,
    private utilsService: UtilsService,
    private toastr: ToastrService
  ) {}

  onClickSelfAssessment(): void {
    this.router.navigate(['/self-assessment', this.moduleData.last_evaluation_id]);
  }

  onClickAIEvaluation(): void {
    this.router.navigate(['/evaluation', this.moduleData.last_evaluation_id]);
  }

  onClickPeerReview(): void {
    this.peerReviewClick.emit();
  }

  onClickDownload(): void {
    this.utilsService.downloadBadge(this.moduleData.last_evaluation_id!.toString()).subscribe({
      next: (data: Blob) => {
        const pngUrl = window.URL.createObjectURL(data);
        const link = document.createElement('a');

        link.href = pngUrl;
        link.download = `EEDA_Quality_Badge_${this.moduleData.last_evaluation_id!.toString()}.png`;
        link.click();

        window.URL.revokeObjectURL(pngUrl);
      },
      error: (err) => {
        this.toastr.error('Error downloading Quality Badge.', 'Error');
      }
    });
  }
}
