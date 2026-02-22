// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, OnInit } from '@angular/core';
import { PageTitleComponent } from '../../components/page-title-component/page-title-component';
import { MatButtonModule } from '@angular/material/button';
import { SelfEvaluationService } from '../../services/self-evaluation-service';
import { ActivatedRoute, Router } from '@angular/router';
import { ResultCardComponent } from '../../components/result-card-component/result-card-component';

@Component({
  selector: 'app-results',
  imports: [
    PageTitleComponent,
    MatButtonModule,
    ResultCardComponent
  ],
  templateUrl: './results.html',
  styleUrl: './results.css',
})
export class Results implements OnInit {
  evaluationId?: string;
  allScans: any = null;
  scans: any[] = [];

  constructor (
    private selfEvaluationService: SelfEvaluationService,
    private route: ActivatedRoute,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.evaluationId = this.route.snapshot.paramMap.get('id') || undefined;

    this.selfEvaluationService.getResults(this.evaluationId!).subscribe({
      next: (response: any[]) => {
        this.allScans = response.find(scan => scan.name === 'All Scans') || null;
        this.scans = response.filter(scan => scan.name !== 'All Scans');
      },
      error: (error) => {
        console.error('Error fetching results:', error);
      }
    })
  }

  goBack(): void {
    this.router.navigate(['/self-assessment', this.evaluationId]);
  }
}
