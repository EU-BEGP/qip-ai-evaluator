// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvaluationProgressDotsComponent } from './evaluation-progress-dots-component';

describe('EvaluationProgressDotsComponent', () => {
  let component: EvaluationProgressDotsComponent;
  let fixture: ComponentFixture<EvaluationProgressDotsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvaluationProgressDotsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EvaluationProgressDotsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
