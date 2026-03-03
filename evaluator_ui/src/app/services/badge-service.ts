import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { catchError, finalize, Observable, throwError } from 'rxjs';
import config from '../config.json';
import { LoaderService } from './loader-service';

@Injectable({
  providedIn: 'root',
})
export class BadgeService {
  constructor(
    private http: HttpClient,
    private loaderService: LoaderService,
  ) {}

  retrieveBadgeData(token: string): Observable<any> {
    let URL = `${config.api.baseUrl}badge`;
    const headers = new HttpHeaders({
      'X-Badge-Token': `${token}`,
    });

    this.loaderService.show();

    return this.http.get<any>(URL, { headers }).pipe(
      catchError((err) => throwError(() => err)),
      finalize(() => {
        this.loaderService.hide();
      }),
    );
  }
}
