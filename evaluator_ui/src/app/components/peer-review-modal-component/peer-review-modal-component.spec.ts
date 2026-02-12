// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon


import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PeerReviewModalComponent } from './peer-review-modal-component';

describe('PeerReviewModalComponent', () => {
  let component: PeerReviewModalComponent;
  let fixture: ComponentFixture<PeerReviewModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [PeerReviewModalComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(PeerReviewModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
