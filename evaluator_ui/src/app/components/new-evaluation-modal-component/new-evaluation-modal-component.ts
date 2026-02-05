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

  constructor(
    private evaluationService: EvaluationService,
    private fb: FormBuilder,
    private sanitizer: DomSanitizer
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
    console.log("Redirect to self-assessment page");
  }

  verifyMetadata(): void {
    if (this.newEvalForm.valid) {
      const courseLink = this.newEvalForm.get('courseLink')?.value;
      this.safeCourseLink = null;
      this.evaluationService.verifyMetadata(courseLink, true).subscribe({
        next: (response) => {
          this.safeCourseLink = this.sanitizer.bypassSecurityTrustResourceUrl(courseLink);
          this.metadata = response.body;
          this.checkMetadataStatus(this.metadata);
        },
        error: (error) => {
          this.metadata = [];
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

  /*evaluate(): void {
    const courseLink = this.newEvalForm.get('courseLink')?.value;
    const scanName = this.newEvalForm.get('scanName')?.value;

    const scanRequest: ScanRequest = { 
      course_link: courseLink,
      email: this.email,
      scan_name: scanName
    }

    this.evaluationService.evaluate(scanRequest).subscribe({
      next: (response) => {
        this.router.navigate(['/evaluation', response.body.evaluation_id], {
          queryParams: { scan: scanRequest.scan_name }
        });
      },
      error: (error) => {
        console.error('Evaluation error:', error);
      }
    });
  }*/
}
