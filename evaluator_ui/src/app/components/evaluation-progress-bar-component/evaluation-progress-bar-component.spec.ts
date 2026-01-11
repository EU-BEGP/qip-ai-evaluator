import { ComponentFixture, TestBed } from '@angular/core/testing';

import { EvaluationProgressBarComponent } from './evaluation-progress-bar-component';

describe('EvaluationProgressBarComponent', () => {
  let component: EvaluationProgressBarComponent;
  let fixture: ComponentFixture<EvaluationProgressBarComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [EvaluationProgressBarComponent]
    })
    .compileComponents();

    fixture = TestBed.createComponent(EvaluationProgressBarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
