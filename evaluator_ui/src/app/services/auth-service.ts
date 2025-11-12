import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { AccountCredentials } from '../interfaces/account-credentials';
import { catchError, Observable, tap } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import config from '../config.json';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
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

  login(account: AccountCredentials): Observable<any> {
    const URL = `${config.api.baseUrl}${config.api.users.login}`;
    return this.http
      .post(URL, account, this.httpOptions)
      .pipe(
        tap((response: any) => {
          const token = response.body.access;
          localStorage.setItem('accountEmail', account.email);
          localStorage.setItem('token', token);
          this.toastr.success(`Welcome ${account.email}`);
        }),
        catchError((err) => { 
          this.toastr.error(
            'Please make sure the credentials are correct.',
            'Wrong credentials'
          );
          throw err; 
        })
      );
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  isAuthenticated(): boolean {
    return !!this.getToken();
  }
}
