// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AnswerDistributionComponent } from './answer-distribution-component';

describe('AnswerDistributionComponent', () => {
  let component: AnswerDistributionComponent;
  let fixture: ComponentFixture<AnswerDistributionComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AnswerDistributionComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(AnswerDistributionComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
