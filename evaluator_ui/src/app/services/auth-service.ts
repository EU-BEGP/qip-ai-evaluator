// Copyright (c) Universidad Privada Boliviana (UPB) - EU-BEGP
// MIT License - See LICENSE file in the root directory
// Sebastian Itamari, Santiago Almancy, Alex Villazon

import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { AccountCredentials } from '../interfaces/account-credentials';
import { catchError, Observable, tap } from 'rxjs';
import { ToastrService } from 'ngx-toastr';
import config from '../config.json';
import { LoaderService } from './loader-service';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private httpOptions = <any>{};

  constructor(
    private http: HttpClient,
    private toastr: ToastrService,
    private loaderService: LoaderService
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
    this.loaderService.show();
    return this.http
      .post(URL, account, this.httpOptions)
      .pipe(
        tap((response: any) => {
          const token = response.body.access;
          localStorage.setItem('accountEmail', account.email);
          localStorage.setItem('token', token);
          this.toastr.success(`Welcome ${account.email}`);
          this.loaderService.hide();
        }),
        catchError((err) => { 
          this.toastr.error(
            'Please make sure the credentials are correct.',
            'Wrong credentials'
          );
          this.loaderService.hide();
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
