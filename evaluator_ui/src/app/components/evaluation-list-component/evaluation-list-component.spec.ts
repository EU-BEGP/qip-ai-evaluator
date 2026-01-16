// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvaluationListComponent } from './evaluation-list-component';

describe('EvaluationListComponent', () => {
  let component: EvaluationListComponent;
  let fixture: ComponentFixture<EvaluationListComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvaluationListComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EvaluationListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
