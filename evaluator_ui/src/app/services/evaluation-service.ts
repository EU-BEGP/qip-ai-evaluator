import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { catchError, Observable, throwError } from 'rxjs';
import config from '../config.json';
import { ToastrService } from 'ngx-toastr';

@Injectable({
  providedIn: 'root',
})
export class EvaluationService {
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

  evaluate(courseKey: string): Observable<any> {
    const URL = `${config.api.baseUrl2}${config.api.evaluation.evaluate}`;
    const body = { course_key: courseKey };

    return this.http.post(URL, body, this.httpOptions).pipe(
      catchError((err) => {
        this.toastr.error('Please try again later.', 'Error');
        return throwError(() => err);
      })
    );
  }
}
