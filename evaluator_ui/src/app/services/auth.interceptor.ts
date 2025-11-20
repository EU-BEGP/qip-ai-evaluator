import { Injectable } from '@angular/core';
import { HttpInterceptor, HttpRequest, HttpHandler, HttpEvent, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { Router } from '@angular/router';
import { ToastrService } from 'ngx-toastr';

@Injectable()
export class AuthInterceptor implements HttpInterceptor {

  constructor(
    private router: Router,
    private toastr: ToastrService
  ) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    let authReq = req;

    try {
      const token = localStorage.getItem('token');
      if (token) {
        authReq = req.clone({
          setHeaders: { Authorization: `Bearer ${token}` }
        });
      }
    } catch (e) {
      // Si falla localStorage → simplemente no añade token
    }

    return next.handle(authReq).pipe(
      catchError(err => this.handleAuthError(err))
    );
  }

  private handleAuthError(err: any) {
    if (err instanceof HttpErrorResponse && err.status === 401) {
      this.toastr.error('Your session has expired. Please log in again.', 'Session Expired');
      localStorage.removeItem('token');
      localStorage.removeItem('accountEmail');
      this.router.navigateByUrl('login');
    }

    return throwError(() => err);
  }
}