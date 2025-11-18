import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvaluationCircleComponent } from './evaluation-circle-component';

describe('EvaluationCircleComponent', () => {
  let component: EvaluationCircleComponent;
  let fixture: ComponentFixture<EvaluationCircleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvaluationCircleComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EvaluationCircleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
