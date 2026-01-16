// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvaluationProgressBarComponent } from './evaluation-progress-bar-component';

describe('EvaluationProgressBarComponent', () => {
  let component: EvaluationProgressBarComponent;
  let fixture: ComponentFixture<EvaluationProgressBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvaluationProgressBarComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EvaluationProgressBarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
