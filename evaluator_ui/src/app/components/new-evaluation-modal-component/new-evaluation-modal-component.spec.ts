// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NewEvaluationModalComponent } from './new-evaluation-modal-component';

describe('NewEvaluationModalComponent', () => {
  let component: NewEvaluationModalComponent;
  let fixture: ComponentFixture<NewEvaluationModalComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [NewEvaluationModalComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(NewEvaluationModalComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
