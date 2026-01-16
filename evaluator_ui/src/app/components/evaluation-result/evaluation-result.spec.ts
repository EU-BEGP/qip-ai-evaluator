// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvaluationResult } from './evaluation-result';

describe('EvaluationResult', () => {
  let component: EvaluationResult;
  let fixture: ComponentFixture<EvaluationResult>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvaluationResult]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EvaluationResult);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
