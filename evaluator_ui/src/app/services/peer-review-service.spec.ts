import { TestBed } from '@angular/core/testing';

import { PeerReviewService } from './peer-review-service';

describe('PeerReviewService', () => {
  let service: PeerReviewService;

  beforeEach(() => {
    TestBed.configureTestingModule({});
    service = TestBed.inject(PeerReviewService);
  });

  it('should be created', () => {
    expect(service).toBeTruthy();
  });
});
