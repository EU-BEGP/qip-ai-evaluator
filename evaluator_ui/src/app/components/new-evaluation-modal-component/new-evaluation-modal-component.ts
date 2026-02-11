// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Component, EventEmitter, OnInit, Output } from '@angular/core';
import { FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MetadataStatusComponent } from '../metadata-status-component/metadata-status-component';
import { MetadataItem } from '../../interfaces/metadata-item';
import { EvaluationService } from '../../services/evaluation-service';
import { CommonModule } from '@angular/common';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { DomSanitizer, SafeResourceUrl } from '@angular/platform-browser';
import { Router } from '@angular/router';

@Component({
  selector: 'app-new-evaluation-modal-component',
  imports: [
    CommonModule,
    ReactiveFormsModule,
    FormsModule,
    MatFormFieldModule,
    MetadataStatusComponent,
    MatInputModule,
    MatButtonModule
  ],
  templateUrl: './new-evaluation-modal-component.html',
  styleUrl: './new-evaluation-modal-component.css',
})
export class NewEvaluationModalComponent implements OnInit{
  @Output() closeModalEvent = new EventEmitter<void>();
  metadata: MetadataItem[] = [];
  newEvalForm!: FormGroup;
  verified: boolean = false;
  safeCourseLink: SafeResourceUrl | null = null;

    private readonly statusConfig: Record<string, { icon: string; badge: string; alert: string }> = {
    GOOD: {
      icon: 'check_circle',
      badge: 'bg-success',
      alert: 'alert-success',
    },
    CRITICAL: {
      icon: 'error',
      badge: 'bg-danger',
      alert: 'alert-danger',
    },
    MISSING: {
      icon: 'warning',
      badge: 'bg-warning',
      alert: 'alert-warning',
    },
  };

  constructor(
    private evaluationService: EvaluationService,
    private fb: FormBuilder,
    private sanitizer: DomSanitizer,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.newEvalForm = this.fb.group({
      courseLink: [{ value: '', disabled: false }, Validators.required]
    });
  }

  get courseLinkControl() {
    return this.newEvalForm.controls['courseLink'];
  }

  closeNewEvalModal() {
    const courseControl = this.newEvalForm.get('courseLink');
    courseControl!.enable();
    this.newEvalForm.reset();
    this.metadata = [];
    this.safeCourseLink = null;
    this.closeModalEvent.emit();
  }

  evaluateNew(): void {
    const courseLink = this.newEvalForm.get('courseLink')?.value;
    const email = localStorage.getItem('accountEmail')!
    this.evaluationService.createEvaluation(courseLink, email).subscribe({
      next: (response) => {
        this.closeNewEvalModal();
        this.router.navigate(['/self-assessment', response.body.evaluation_id]);
      },
      error: (error) => {
        this.closeNewEvalModal();
      }
    });
  }

  verifyMetadata(): void {
    if (this.newEvalForm.valid) {
      this.metadata = [];
      const courseLink = this.newEvalForm.get('courseLink')?.value;
      this.safeCourseLink = null;
      this.evaluationService.verifyMetadata(courseLink, true).subscribe({
        next: (response) => {
          this.safeCourseLink = this.sanitizer.bypassSecurityTrustResourceUrl(courseLink);
          this.metadata = response.body;
          this.checkMetadataStatus(this.metadata);
        },
        error: (error) => {
          this.verified = false;
          console.error('Evaluation error:', error);
        }
      });
    }
    else {
      this.newEvalForm.markAllAsTouched();
      this.metadata = [];
      this.verified = false;
    }
  }

  checkMetadataStatus(metadata: MetadataItem[]): void {
    if (metadata.length > 0) {
      this.verified = metadata.every(item => item.status === 'GOOD');
    } else {
      this.verified = false;
    }
  }
}
