// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PeerReviewEvaluation } from './peer-review-evaluation';

describe('PeerReviewEvaluation', () => {
  let component: PeerReviewEvaluation;
  let fixture: ComponentFixture<PeerReviewEvaluation>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeerReviewEvaluation]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PeerReviewEvaluation);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
