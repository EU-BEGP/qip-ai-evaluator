// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ModuleInformationComponent } from '../module-information-component/module-information-component';

describe('ModuleInformationComponent', () => {
  let component: ModuleInformationComponent;
  let fixture: ComponentFixture<ModuleInformationComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ModuleInformationComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(ModuleInformationComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
