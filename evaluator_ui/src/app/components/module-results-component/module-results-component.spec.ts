// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ModuleResultsComponent } from './module-results-component';

describe('ModuleResultsComponent', () => {
  let component: ModuleResultsComponent;
  let fixture: ComponentFixture<ModuleResultsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ModuleResultsComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ModuleResultsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
