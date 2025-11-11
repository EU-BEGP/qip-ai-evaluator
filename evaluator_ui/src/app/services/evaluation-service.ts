import { HttpClient, HttpHeaders, HttpParams } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, interval, Observable, switchMap, takeWhile, tap, throwError } from 'rxjs';
import config from '../config.json';
import { ToastrService } from 'ngx-toastr';
import { ScanRequest } from '../interfaces/scan-request';

@Injectable({
  providedIn: 'root',
})
export class EvaluationService {
  private readonly POLL_INTERVAL = 5000;

  private httpOptions = <any>{};

  constructor(
    private http: HttpClient,
    private toastr: ToastrService
  ) { 
    this.httpOptions = {
      headers: new HttpHeaders({
        'Content-Type': 'application/json',
      }),
      observe: 'response' as 'response',
    };
  }

  evaluate(scanRequest: ScanRequest): Observable<any> {
    const URL = `${config.api.baseUrl2}${config.api.evaluation.evaluate}`;
    const body = scanRequest;

    return this.http.post(URL, body, this.httpOptions).pipe(
      tap((response: any) => {
        if (body.scan_name != undefined && body.scan_name != '') {
          localStorage.setItem('isAll' + body.email, 'false');
        }
        else {
          localStorage.setItem('isAll' + body.email, 'true');
        }
        localStorage.setItem('evaluationId' + body.email, response.body.evaluationId);
        this.toastr.success('Evaluation request successfully submitted.', 'Success');
      }),
      catchError((err) => {
        this.toastr.error('Please try again later.', 'Error');
        return throwError(() => err);
      })
    );
  }

  getEvaluationList(scanRequest: ScanRequest): Observable<any[]> {
    const URL = `${config.api.baseUrl2}${config.api.evaluation.list}`;
    let params = new HttpParams()
      .set('course_key', scanRequest.course_key)
      .set('email', scanRequest.email);

    if (scanRequest.scan_name != undefined && scanRequest.scan_name != '') {
      params = params.set('scan_name', scanRequest.scan_name);
    }

    return this.http.get<any[]>(URL, { params }).pipe(
      catchError((err) => {
        this.toastr.error('Could not load history.', 'Error');
        return throwError(() => err);
      })
    );
  }

  getEvaluationDetailModule(id: number): Observable<any> {
    let URL = `${config.api.baseUrl2}${config.api.evaluation.detailModule}`;
    URL = URL.replace('{id}', String(id));

    return this.http.get<any>(URL).pipe(
      catchError((err) => {
        this.toastr.error('Could not load evaluation detail.', 'Error');
        return throwError(() => err);
      })
    );
  }

  getEvaluationDetailScan(id: number): Observable<any> {
    let URL = `${config.api.baseUrl2}${config.api.evaluation.detailScan}`;
    URL = URL.replace('{id}', String(id));

    return this.http.get<any>(URL).pipe(
      catchError((err) => {
        this.toastr.error('Could not load evaluation detail.', 'Error');
        return throwError(() => err);
      })
    );
  }

  getStatusModule(id: string) {
    let URL = `${config.api.baseUrl2}${config.api.evaluation.statusModule}`;
    URL = URL.replace('{id}', String(id));

    return interval(this.POLL_INTERVAL).pipe(
      switchMap(() => this.http.get<any>(URL)),
      takeWhile(res => res.status !== 'Completed' && res.status !== 'Failed', true)
    );
  }

  getStatusScan(id: string) {
    let URL = `${config.api.baseUrl2}${config.api.evaluation.statusScan}`;
    URL = URL.replace('{id}', String(id));

    return interval(this.POLL_INTERVAL).pipe(
      switchMap(() => this.http.get<any>(URL)),
      takeWhile(res => res.status !== 'Completed' && res.status !== 'Failed', true)
    );
  }
}
