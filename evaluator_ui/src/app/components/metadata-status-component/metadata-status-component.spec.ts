// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MetadataStatusComponent } from './metadata-status-component';

describe('MetadataStatusComponent', () => {
  let component: MetadataStatusComponent;
  let fixture: ComponentFixture<MetadataStatusComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [MetadataStatusComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(MetadataStatusComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
