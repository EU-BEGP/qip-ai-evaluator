// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { Injectable } from '@angular/core';
import {
  HttpInterceptor,
  HttpRequest,
  HttpHandler,
  HttpEvent,
  HttpErrorResponse,
  HttpClient,
  HttpBackend,
} from '@angular/common/http';
import { BehaviorSubject, Observable, throwError } from 'rxjs';
import { catchError, filter, switchMap, take, tap } from 'rxjs/operators';
import { Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import config from '../config.json';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {
  private isRefreshing = false;
  private refreshTokenSubject = new BehaviorSubject<string | null>(null);
  private rawHttp: HttpClient;

  constructor(
    private router: Router,
    private toastr: ToastrService,
    handler: HttpBackend
  ) {
    this.rawHttp = new HttpClient(handler);
  }

  intercept(
    req: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    const authReq = this.addToken(req, localStorage.getItem('token'));
    return next.handle(authReq).pipe(
      catchError((err) => {
        if (err instanceof HttpErrorResponse && err.status === 401) {
          return this.handle401(req, next);
        }
        return throwError(() => err);
      })
    );
  }

  private addToken(
    req: HttpRequest<any>,
    token: string | null
  ): HttpRequest<any> {
    if (!token) return req;
    return req.clone({
      setHeaders: { Authorization: `Bearer ${token}` },
    });
  }

  private handle401(
    req: HttpRequest<any>,
    next: HttpHandler
  ): Observable<HttpEvent<any>> {
    const refreshToken = localStorage.getItem('refresh');

    if (!refreshToken) {
      return this.forceLogout();
    }

    if (this.isRefreshing) {
      return this.refreshTokenSubject.pipe(
        filter((token) => token !== null),
        take(1),
        switchMap((token) => next.handle(this.addToken(req, token)))
      );
    }

    this.isRefreshing = true;
    this.refreshTokenSubject.next(null);

    const url = `${config.api.baseUrl}${config.api.users.refresh}`;
    return this.rawHttp.post<{ access: string }>(url, { refresh: refreshToken }).pipe(
      tap((res) => {
        localStorage.setItem('token', res.access);
        this.refreshTokenSubject.next(res.access);
        this.isRefreshing = false;
      }),
      switchMap((res) => next.handle(this.addToken(req, res.access))),
      catchError((err) => {
        this.isRefreshing = false;
        return this.forceLogout();
      })
    );
  }

  private forceLogout(): Observable<never> {
    this.toastr.error(
      'Your session has expired. Please log in again.',
      'Session Expired'
    );
    localStorage.removeItem('token');
    localStorage.removeItem('refresh');
    localStorage.removeItem('accountEmail');
    localStorage.removeItem('qipv2');
    this.router.navigateByUrl('login');
    return throwError(() => new Error('Session expired'));
  }
}
