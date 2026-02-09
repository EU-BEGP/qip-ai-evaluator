import { TestBed } from '@angular/core/testing';
import {
  HttpClientTestingModule,
  HttpTestingController,
} from '@angular/common/http/testing';

import { SelfEvaluationService } from './self-evaluation-service';
import config from '../config.json';

describe('SelfEvaluationService', () => {
  let service: SelfEvaluationService;
  let httpMock: HttpTestingController;
  const base = `${config.api.baseUrl}evaluations`;

  beforeEach(() => {
    TestBed.configureTestingModule({
      imports: [HttpClientTestingModule],
      providers: [SelfEvaluationService],
    });

    service = TestBed.inject(SelfEvaluationService);
    httpMock = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    httpMock.verify();
  });

  it('should request scans for a module (GET)', () => {
    const mock = [{ id: '123', name: 'Scan 123' }];

    service.getScans('moduleX').subscribe((res) => {
      expect(res).toEqual(mock);
    });

    const req = httpMock.expectOne(`${base}/scans?moduleId=moduleX`);
    expect(req.request.method).toBe('GET');
    req.flush(mock);
  });

  it('should request criterions for a scan (GET)', () => {
    const mock = [
      { id: 'c1', question: 'Question 1', description: 'Description 1' },
      { id: 'c2', question: 'Question 2', description: 'Description 2' },
    ];

    service.getCriterions('scan1').subscribe((res) => {
      expect(res).toEqual(mock);
    });

    const req = httpMock.expectOne(`${base}/scans/scan1/criterions`);
    expect(req.request.method).toBe('GET');
    req.flush(mock);
  });

  it('should update a criterion result (PUT)', () => {
    const result = { result: 'yes' };
    const mockResp = { success: true };

    service.updateCriterion('scanA', 'critA', result).subscribe((res) => {
      expect(res).toEqual(mockResp);
    });

    const req = httpMock.expectOne(`${base}/scans/scanA/criterions/critA`);
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ result });
    req.flush(mockResp);
  });

  it('should request ai suggestion for a criterion (POST)', () => {
    const mock = { explanation: 'reason', answer: 'yes' };

    service
      .getAiSuggestion('s1', 'c1', 'Is this ok?', 'Some description')
      .subscribe((res) => {
        expect(res).toEqual(mock);
      });

    const req = httpMock.expectOne(
      `${base}/scans/s1/criterions/c1/ai-suggestion`,
    );
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({
      id: 'c1',
      question: 'Is this ok?',
      description: 'Some description',
    });
    req.flush(mock);
  });
});
