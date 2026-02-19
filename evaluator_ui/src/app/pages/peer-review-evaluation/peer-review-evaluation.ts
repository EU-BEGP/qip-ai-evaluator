// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { CommonModule } from '@angular/common';
import { Component, OnInit } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTabsModule } from '@angular/material/tabs';
import { SearchComponent } from '../../components/search-component/search-component';
import { ModuleInformationComponent } from '../../components/module-information-component/module-information-component';
import { PeerReviewService } from '../../services/peer-review-service';
import { ActivatedRoute, Router } from '@angular/router';

@Component({
  selector: 'app-peer-review-evaluation',
  imports: [
    CommonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTabsModule,
    SearchComponent,
    ModuleInformationComponent
  ],
  templateUrl: './peer-review-evaluation.html',
  styleUrl: './peer-review-evaluation.css',
})
export class PeerReviewEvaluation implements OnInit {
  review: any = null;
  selectedIndex?: number;
  evaluationId?: string;
  reviewId?: string;
  scansList: any[] = [];

  constructor(private peerReviewService: PeerReviewService,
              private route: ActivatedRoute,
              private router: Router,
  ) {}

  ngOnInit(): void {
    this.evaluationId = this.route.snapshot.paramMap.get('id') || undefined;
    this.reviewId = this.route.snapshot.paramMap.get('reviewId') || undefined;

    this.peerReviewService.getScansInfo(this.reviewId!).subscribe({
      next: (response) => {
        this.review = response;
        this.scansList = response.content;
      },
      error: (error) => {
        console.error(error);
      }
    });
  }

  getNameShort(value: string): string {
    if (!value) return "";

    const parts = value.trim().split(" ");

    if (parts.length <= 1) return value;

    parts.pop();
    return parts.join(" ");
  }

  onTabChange(index: number): void {
    const scanName = this.scansList[index].name;

    this.router.navigate([], {
      relativeTo: this.route,
      queryParams: { scan: scanName },
      queryParamsHandling: 'merge'
    });
  }
}
