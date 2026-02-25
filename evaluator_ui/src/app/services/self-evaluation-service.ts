import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { catchError, finalize, Observable, throwError } from 'rxjs';
import config from '../config.json';
import { LoaderService } from './loader-service';

@Injectable({
  providedIn: 'root',
})
export class SelfEvaluationService {
  private base = `${config.api.baseUrl}evaluations`;

  constructor(
    private http: HttpClient,
    private loaderService: LoaderService,
  ) {}

  getScans(evalId: string, token?: string): Observable<any> {
    let url = `${this.base}/evaluation_ids/${encodeURIComponent(evalId)}`;

    let header = new HttpHeaders();
    if (token) {
      header = header.set('X-Review-Token', `${token}`);
    }
    return this.http.get<any>(url, { headers: header });
  }

  getCriterions(scanId: string, token?: string): Observable<any> {
    let url = `${this.base}/scans/${encodeURIComponent(scanId)}/criterions`;

    let header = new HttpHeaders();
    if (token) {
      header = header.set('X-Review-Token', `${token}`);
    }
    return this.http.get<any>(url, { headers: header });
  }

  updateCriterion(criterionId: string, result: any): Observable<any> {
    const url = `${this.base}/scans/criterions/${encodeURIComponent(criterionId)}/`;
    return this.http.put<any>(url, { result });
  }

  requestAiSuggestion(
    criterionId: string,
    question: string,
    description: string,
  ): Observable<any> {
    const url = `${this.base}/scans/criterions/${encodeURIComponent(criterionId)}/ai-suggestion/`;
    return this.http.post<{
      result: string;
    }>(url, { question, description });
  }

  getAiSuggestion(criterionId: string): Observable<{
    result: string;
  }> {
    const url = `${this.base}/scans/criterions/${encodeURIComponent(criterionId)}/result`;
    return this.http.get<{
      result: string;
    }>(url);
  }

  getResults(evaluationId: number) {
    let URL = `${config.api.baseUrl}${config.api.selfAssessment.results}`;
    URL = URL.replace('{id}', evaluationId.toString());

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }

  getStatus(evaluationId: number) {
    let URL = `${config.api.baseUrl}${config.api.selfAssessment.status}`;
    URL = URL.replace('{id}', evaluationId.toString());

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }

  getSelfAssessmentCompletionStatus(evaluationId: string) {
    let URL = `${config.api.baseUrl}/evaluations/self_assessment/${evaluationId}/completion_status`;

    this.loaderService.show();

    return this.http.get<any>(URL).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }
}
