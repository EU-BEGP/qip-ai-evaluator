// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { CriterionCardComponent } from './criterion-card-component';

describe('CriterionCardComponent', () => {
  let component: CriterionCardComponent;
  let fixture: ComponentFixture<CriterionCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [CriterionCardComponent],
    }).compileComponents();

    fixture = TestBed.createComponent(CriterionCardComponent);
    component = fixture.componentInstance;
    component.question = 'Test question';
    component.description = 'A short description';
    component.buttons = [
      { label: 'One' },
      { label: 'Two' },
      { label: 'Three' },
    ];
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
