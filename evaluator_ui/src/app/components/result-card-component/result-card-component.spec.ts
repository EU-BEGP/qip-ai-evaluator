// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ResultCardComponent } from './result-card-component';

describe('ResultCardComponent', () => {
  let component: ResultCardComponent;
  let fixture: ComponentFixture<ResultCardComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ResultCardComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ResultCardComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
