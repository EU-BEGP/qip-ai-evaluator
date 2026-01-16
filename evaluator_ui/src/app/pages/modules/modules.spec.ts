// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { Modules } from './modules';

describe('Modules', () => {
  let component: Modules;
  let fixture: ComponentFixture<Modules>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [Modules]
    })
    .compileComponents();

    fixture = TestBed.createComponent(Modules);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
