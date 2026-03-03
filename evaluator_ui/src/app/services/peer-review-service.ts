import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { LoaderService } from './loader-service';
import { Observable } from 'rxjs/internal/Observable';
import config from '../config.json';
import { throwError } from 'rxjs/internal/observable/throwError';
import { catchError } from 'rxjs/internal/operators/catchError';
import { finalize } from 'rxjs/internal/operators/finalize';

@Injectable({
  providedIn: 'root',
})
export class PeerReviewService {
  private httpOptions = <any>{};

  constructor(
    private http: HttpClient,
    private loaderService: LoaderService,
  ) {
    this.httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      }),
      observe: 'response' as 'response',
    };
  }

  getPeerReviews(id: string): Observable<any> {
    let URL = `${config.api.baseUrl}${config.api.peerReview.reviews}`;
    URL = URL.replace('{id}', id);

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }

  getScansInfo(reviewId: string): Observable<any> {
    let URL = `${config.api.baseUrl}${config.api.peerReview.scansInfo}`;
    URL = URL.replace('{id}', reviewId);

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }

  getReviewDetailScan(reviewId: string, scanId: string): Observable<any> {
    let URL = `${config.api.baseUrl}${config.api.peerReview.reviewDetail}`;
    URL = URL.replace('{reviewerId}', reviewId);
    URL = URL.replace('{scanId}', scanId);

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }

  getModuleName(token: string): Observable<any> {
    const headers = new HttpHeaders().set('X-Review-Token', `${token}`);
    let URL = `${config.api.baseUrl}reviews/details/`;

    this.loaderService.show();

    return this.http.get<any>(URL, { headers }).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }

  requestPeerReview(evaluationId: string, emails: string[]): Observable<any> {
    const url = `${config.api.baseUrl}reviews/request_peer_reviews/`;
    return this.http.post<{
      result: string;
    }>(url, { evaluationId, emails });
  }

  updatePeerCriterion(
    token: string,
    criterionId: string,
    value: number,
    note: string,
  ): Observable<void> {
    const url = `${config.api.baseUrl}reviews/criterion/${criterionId}/`;
    const headers = new HttpHeaders().set('X-Review-Token', `${token}`);
    return this.http.put<void>(url, { value, note }, { headers });
  }

  endPeerReview(token: string): Observable<void> {
    const headers = new HttpHeaders().set('X-Review-Token', `${token}`);
    const url = `${config.api.baseUrl}reviews/submit/`;
    return this.http.post<void>(url, {}, { headers });
  }

  getPeerReviewCompletionStatus(
    token: string,
  ): Observable<{ scanComplete: { name: string; isComplete: boolean }[] }> {
    const headers = new HttpHeaders().set('X-Review-Token', `${token}`);
    const url = `${config.api.baseUrl}reviews/completion_status`;
    return this.http.get<{
      scanComplete: { name: string; isComplete: boolean }[];
    }>(url, { headers });
  }
}
